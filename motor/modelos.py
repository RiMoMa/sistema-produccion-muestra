"""Vías hacia los modelos, detrás de una sola interfaz. Agregar una vía es agregar una función.

Ningún modelo recibe herramientas de escritura ni shell: solo ve el texto que se le envía, así que
lo que no se manda no existe para él. Procedencia en PROCEDENCIA.md.

Niveles: `pago` (DeepSeek, Claude), `libre` (modelos gratuitos por opencode) y `local` (Ollama).
"""
from __future__ import annotations

import base64
import http.client
import json
import os
import shutil
import stat
import subprocess
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from motor import saneo
from motor.state import Bloqueado

NIVELES = {"deepseek": "pago", "claude": "pago", "opencode": "libre", "ollama": "local"}
HERRAMIENTAS_CLAUDE = {"WebSearch", "WebFetch"}
LOCALES = {"127.0.0.1", "localhost", "::1"}
# Precio por millón en hora pico (api-docs.deepseek.com, 3 nov 2026): el costo registrado es un techo.
PRECIOS = {"deepseek-v4-pro": {"entrada": 1.32, "salida": 3.96, "cache": 0.044}}


class ErrorModelo(RuntimeError):
    pass


@dataclass(frozen=True)
class Pedido:
    rol: str
    modelo: str
    sistema: str
    texto: str
    json: bool = False
    imagenes: tuple[bytes, ...] = ()
    herramientas: tuple[str, ...] = ()
    timeout_s: int = 900
    max_bytes: int = 400_000


@dataclass
class Respuesta:
    texto: str
    modelo: str
    tokens: dict = field(default_factory=dict)
    costo_usd: float = 0.0


def clave_de_rol(rol: str) -> str:
    base = Path(os.environ.get("MOTOR_CLAVES", Path.home() / ".config/deepseek/claves"))
    ruta = base / rol
    if not ruta.is_file():
        raise ErrorModelo(f"no hay clave para el rol {rol}")
    if stat.S_IMODE(ruta.stat().st_mode) not in (0o600, 0o400):
        raise ErrorModelo(f"la clave del rol {rol} debe tener permisos 600")
    clave = ruta.read_text(encoding="utf-8").strip()
    if not clave:
        raise ErrorModelo(f"la clave del rol {rol} está vacía")
    return clave


def _post(url: str, cuerpo: dict, cabeceras: dict, timeout: int, secreto: str = "", leer=json.load) -> dict:
    q = urllib.request.Request(url, data=json.dumps(cuerpo).encode(), headers={"Content-Type": "application/json", **cabeceras})
    try:
        with urllib.request.urlopen(q, timeout=timeout) as r:
            return leer(r)
    # Una respuesta cortada a mitad (IncompleteRead, conexión reiniciada) es una falla de la vía, no del motor.
    except (urllib.error.URLError, TimeoutError, ValueError, http.client.HTTPException, OSError) as x:
        mensaje = str(x).replace(secreto, "***") if secreto else str(x)
        raise ErrorModelo(f"falló la llamada: {mensaje}"[:300]) from None


def _leer_flujo(r) -> dict:
    """Arma la respuesta completa desde los eventos del streaming. Sin [DONE], la respuesta llegó cortada."""
    partes, modelo, uso, completo = [], None, {}, False
    for crudo in r:
        linea = crudo.decode("utf-8").strip()
        if not linea.startswith("data:"):
            continue  # líneas vacías y comentarios de keep-alive
        dato = linea[5:].strip()
        if dato == "[DONE]":
            completo = True
            break
        e = json.loads(dato)
        modelo = e.get("model") or modelo
        uso = e.get("usage") or uso
        for c in e.get("choices") or []:
            partes.append((c.get("delta") or {}).get("content") or "")
    if not completo:
        raise ErrorModelo("respuesta cortada: el flujo terminó sin [DONE]")
    return {"model": modelo, "usage": uso, "choices": [{"message": {"content": "".join(partes)}}]}


def _leer_respuesta(r) -> dict:
    """Con streaming la conexión sigue viva: sin él, las respuestas largas se cortaban a los 60 s (bloque 3)."""
    if "event-stream" not in (r.headers.get("Content-Type") or ""):
        return json.load(r)
    return _leer_flujo(r)


def _costo(modelo: str, u: dict) -> float:
    p = PRECIOS.get(modelo)
    if not p:
        return 0.0
    cache = u.get("cache_leido", 0)
    return ((u.get("entrada", 0) - cache) * p["entrada"] + cache * p["cache"] + u.get("salida", 0) * p["salida"]) / 1e6


def deepseek(p: Pedido) -> Respuesta:
    clave = clave_de_rol(p.rol)
    cuerpo = {"model": p.modelo, "stream": True, "stream_options": {"include_usage": True}, "messages": [
        {"role": "system", "content": p.sistema}, {"role": "user", "content": p.texto}]}
    if p.json:
        cuerpo["response_format"] = {"type": "json_object"}
    base = os.environ.get("DEEPSEEK_URL", "https://api.deepseek.com")
    r = _post(f"{base}/chat/completions", cuerpo, {"Authorization": f"Bearer {clave}"}, p.timeout_s, clave,
              _leer_respuesta)
    try:
        texto = r["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise ErrorModelo("respuesta sin texto") from None
    u = r.get("usage") or {}
    tokens = {"entrada": u.get("prompt_tokens", 0), "salida": u.get("completion_tokens", 0),
              "cache_leido": u.get("prompt_cache_hit_tokens", 0),
              "razonamiento": (u.get("completion_tokens_details") or {}).get("reasoning_tokens", 0)}
    return Respuesta(texto or "", r.get("model", p.modelo), tokens, _costo(p.modelo, tokens))


def _correr(cmd: list[str], p: Pedido, carpeta: str, env: dict, entrada: str | None = None) -> str:
    try:
        r = subprocess.run(cmd, cwd=carpeta, env={**env, "PWD": carpeta}, input=entrada, capture_output=True,
                           text=True, timeout=p.timeout_s, stdin=subprocess.DEVNULL if entrada is None else None)
    except subprocess.TimeoutExpired:
        raise ErrorModelo(f"pasó el tiempo de {p.timeout_s} s") from None
    if r.returncode:
        # opencode deja su error en la salida normal, no en la de error.
        raise ErrorModelo(f"el proceso falló (código {r.returncode}): {(r.stderr or r.stdout)[-300:]}")
    return r.stdout


def claude(p: Pedido) -> Respuesta:
    """Con suscripción, en una carpeta temporal y sin CLAUDE.md. Antes de abrir a terceros se pasa a API key (D92)."""
    extra = set(p.herramientas) - HERRAMIENTAS_CLAUDE
    if extra:
        raise Bloqueado(f"herramientas no permitidas: {sorted(extra)}")
    env = {k: v for k, v in os.environ.items()
           if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN")}
    with tempfile.TemporaryDirectory(prefix="motor-claude-") as d:
        sistema = Path(d) / ".sistema.md"
        sistema.write_text(p.sistema, encoding="utf-8")
        cmd = [os.environ.get("CLAUDE_BIN", "claude"), "-p", "--model", p.modelo, "--system-prompt-file", str(sistema),
               "--tools", ",".join(p.herramientas), "--strict-mcp-config", "--no-session-persistence",
               "--setting-sources", "local", "--output-format", "json"]
        if p.herramientas:  # sin permiso explícito, -p las ofrece y las niega (prueba con cupo del bloque 16)
            cmd += ["--allowedTools", ",".join(p.herramientas)]
        crudo = _correr(cmd, p, d, env, p.texto)
    try:
        r = json.loads(crudo)
    except ValueError:
        raise ErrorModelo("la salida de claude no es JSON") from None
    if r.get("is_error"):
        raise ErrorModelo(f"claude falló: {str(r.get('result'))[:300]}")
    u = r.get("usage") or {}
    tokens = {"entrada": (u.get("input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0),
              "salida": u.get("output_tokens") or 0, "cache_leido": u.get("cache_read_input_tokens") or 0,
              "costo_estimado": r.get("total_cost_usd")}
    return Respuesta(r.get("result") or "", p.modelo, tokens, 0.0)


def opencode(p: Pedido) -> Respuesta:
    """Modelos gratuitos. Un agente con todo negado, en carpeta temporal."""
    if not p.modelo.startswith("opencode/"):
        raise Bloqueado(f"esta vía solo es para modelos opencode/: {p.modelo}")
    with tempfile.TemporaryDirectory(prefix="motor-opencode-") as d:
        agentes = Path(d) / ".opencode/agent"
        agentes.mkdir(parents=True)
        (agentes / "worker.md").write_text(
            "---\ndescription: sin herramientas\nmode: primary\npermission:\n  \"*\": deny\n"
            f"  external_directory: deny\n---\n\n{p.sistema}", encoding="utf-8")
        cmd = [os.environ.get("OPENCODE_BIN", "opencode"), "run", "--standalone", "--format", "json",
               "--model", p.modelo, "--agent", "worker", p.texto]
        crudo = _correr(cmd, p, d, dict(os.environ))
    partes, errores = [], []
    for linea in crudo.splitlines():
        try:
            e = json.loads(linea)
        except ValueError:
            continue
        if e.get("type") == "text":
            partes.append(e.get("part", {}).get("text", ""))
        elif e.get("type") == "error":
            errores.append(str(e.get("error") or e)[:300])
    if errores:
        raise ErrorModelo("; ".join(errores))
    return Respuesta("\n".join(partes), p.modelo)


def ollama(p: Pedido) -> Respuesta:
    """Local de verdad: nunca :cloud, y solo contra esta máquina."""
    base = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
    if ":cloud" in p.modelo:
        raise Bloqueado(f"{p.modelo} no es local")
    if urlparse(base).hostname not in LOCALES:
        raise Bloqueado(f"Ollama no apunta a esta máquina: {base}")
    usuario = {"role": "user", "content": p.texto}
    if p.imagenes:
        usuario["images"] = [base64.b64encode(i).decode() for i in p.imagenes]
    cuerpo = {"model": p.modelo, "stream": False, "think": False,
              "messages": [{"role": "system", "content": p.sistema}, usuario]}
    if p.json:
        cuerpo["format"] = "json"
    r = _post(f"{base}/api/chat", cuerpo, {}, p.timeout_s)
    try:
        texto = r["message"]["content"]
    except (KeyError, TypeError):
        raise ErrorModelo("respuesta sin texto") from None
    return Respuesta(texto, p.modelo, {"entrada": r.get("prompt_eval_count", 0), "salida": r.get("eval_count", 0)})


VIAS = {"deepseek": deepseek, "claude": claude, "opencode": opencode, "ollama": ollama}


def llamar(via: str, p: Pedido, terminos: list[str] | None = None) -> Respuesta:
    """Todo pasa por aquí: el freno de saneo y los límites no dependen de cada vía."""
    if via not in VIAS:
        raise Bloqueado(f"vía desconocida: {via}")
    if NIVELES[via] != "local":
        if p.imagenes:
            raise Bloqueado("una imagen no se puede revisar: solo sale a un modelo local")
        saneo.exigir_limpio({"el sistema": p.sistema, "el encargo": p.texto}, terminos)
    r = VIAS[via](p)
    if not r.texto.strip():
        raise ErrorModelo(f"{via} devolvió una respuesta vacía")
    if len(r.texto.encode()) > p.max_bytes:
        raise ErrorModelo(f"la salida pasa de {p.max_bytes} bytes")
    return r


def con_respaldo(rutas: list[tuple[str, str]], pedido: Pedido, validar=None,
                 terminos: list[str] | None = None) -> tuple[str, Respuesta, list[str]]:
    """Prueba las rutas en orden hasta una respuesta válida. Un Bloqueado no se salta: se detiene."""
    fallos = []
    for via, modelo in rutas:
        try:
            r = llamar(via, Pedido(**{**pedido.__dict__, "modelo": modelo}), terminos)
            errores = validar(r.texto) if validar else []
        except ErrorModelo as x:
            errores = [str(x)]
        if not errores:
            return via, r, fallos
        fallos.append(f"{via}/{modelo}: {'; '.join(errores)}"[:300])
    raise ErrorModelo("ninguna ruta dio un resultado válido: " + " | ".join(fallos))
