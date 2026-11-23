"""Prueba las vías con un servidor y comandos falsos: sin red externa y sin gastar."""
import http.client
import json
import os
import stat
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from motor import modelos as M
from motor import nodos as N
from motor import runtime as R
from motor import state as S

CLAVE = "clave-secreta-de-prueba"


class Servidor(BaseHTTPRequestHandler):
    recibido, respuesta, codigo = [], {}, 200

    def do_POST(self):
        cuerpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Servidor.recibido.append({"ruta": self.path, "auth": self.headers.get("Authorization"), "cuerpo": cuerpo})
        datos = json.dumps(Servidor.respuesta).encode()
        self.send_response(Servidor.codigo)
        self.end_headers()
        self.wfile.write(datos)

    def log_message(self, *a):
        pass


@pytest.fixture
def servidor(monkeypatch):
    s = HTTPServer(("127.0.0.1", 0), Servidor)
    threading.Thread(target=s.serve_forever, args=(0.01,), daemon=True).start()
    Servidor.recibido, Servidor.codigo = [], 200
    Servidor.respuesta = {"model": "deepseek-v4-pro-real", "usage": {
        "prompt_tokens": 1000, "completion_tokens": 100, "prompt_cache_hit_tokens": 400,
        "completion_tokens_details": {"reasoning_tokens": 30}},
        "choices": [{"message": {"content": "respuesta"}}], "message": {"content": "local"},
        "prompt_eval_count": 5, "eval_count": 2}
    url = f"http://127.0.0.1:{s.server_port}"
    monkeypatch.setenv("DEEPSEEK_URL", url)
    monkeypatch.setenv("OLLAMA_URL", url)
    yield url
    s.shutdown()


@pytest.fixture
def claves(tmp_path, monkeypatch):
    d = tmp_path / "claves"
    d.mkdir()
    (d / "borrador").write_text(CLAVE + "\n", encoding="utf-8")
    (d / "borrador").chmod(0o600)
    monkeypatch.setenv("MOTOR_CLAVES", str(d))
    return d


def falso(tmp_path, nombre, codigo):
    f = tmp_path / nombre
    f.write_text(f"#!/usr/bin/env python3\nimport json,os,sys\n{codigo}\n", encoding="utf-8")
    f.chmod(f.stat().st_mode | stat.S_IXUSR)
    return f


@pytest.fixture
def claude_falso(tmp_path, monkeypatch):
    log = tmp_path / "claude.json"
    f = falso(tmp_path, "claude", f"""
json.dump({{"argv": sys.argv, "stdin": sys.stdin.read(), "cwd": os.getcwd(),
           "tiene_clave": "ANTHROPIC_API_KEY" in os.environ}}, open({str(log)!r}, "w"))
print(json.dumps({{"result": "revisado", "session_id": "s", "total_cost_usd": 0.5, "is_error": False,
                  "usage": {{"input_tokens": 10, "output_tokens": 3}}}}))""")
    monkeypatch.setenv("CLAUDE_BIN", str(f))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "no-debe-llegar")
    return log


@pytest.fixture
def opencode_falso(tmp_path, monkeypatch):
    log = tmp_path / "opencode.json"
    f = falso(tmp_path, "opencode", f"""
agente = open(".opencode/agent/worker.md").read()
json.dump({{"argv": sys.argv, "agente": agente, "cwd": os.getcwd()}}, open({str(log)!r}, "w"))
print(json.dumps({{"type": "text", "part": {{"text": "gratis"}}}}))""")
    monkeypatch.setenv("OPENCODE_BIN", str(f))
    return log


def pedido(**k):
    return M.Pedido(**{"rol": "borrador", "modelo": "deepseek-v4-pro", "sistema": "rol", "texto": "hola", **k})


# DeepSeek

def test_deepseek_envia_solo_lo_pedido(servidor, claves):
    r = M.llamar("deepseek", pedido())
    q = Servidor.recibido[0]
    assert r.texto == "respuesta" and q["ruta"] == "/chat/completions" and q["auth"] == f"Bearer {CLAVE}"
    assert q["cuerpo"]["messages"] == [{"role": "system", "content": "rol"}, {"role": "user", "content": "hola"}]
    assert "response_format" not in q["cuerpo"]


def test_deepseek_registra_modelo_devuelto_tokens_y_costo(servidor, claves):
    r = M.llamar("deepseek", pedido())
    assert r.modelo == "deepseek-v4-pro-real"
    assert r.tokens == {"entrada": 1000, "salida": 100, "cache_leido": 400, "razonamiento": 30}
    assert r.costo_usd == pytest.approx((600 * 1.32 + 400 * 0.044 + 100 * 3.96) / 1e6)


def test_deepseek_pide_json(servidor, claves):
    M.llamar("deepseek", pedido(json=True))
    assert Servidor.recibido[0]["cuerpo"]["response_format"] == {"type": "json_object"}


def test_error_del_servidor_no_filtra_la_clave(servidor, claves):
    Servidor.codigo = 500
    with pytest.raises(M.ErrorModelo) as e:
        M.llamar("deepseek", pedido())
    assert CLAVE not in str(e.value)


def test_clave_dentro_de_un_error_de_red_se_oculta(claves, monkeypatch):
    def caer(*a, **k):
        raise M.urllib.error.URLError(f"fallo con {CLAVE}")
    monkeypatch.setattr(M.urllib.request, "urlopen", caer)
    with pytest.raises(M.ErrorModelo) as e:
        M.llamar("deepseek", pedido())
    assert CLAVE not in str(e.value) and "***" in str(e.value)


def test_clave_con_permisos_abiertos_falla(claves):
    (claves / "borrador").chmod(0o644)
    with pytest.raises(M.ErrorModelo, match="permisos 600"):
        M.clave_de_rol("borrador")


def test_clave_vacia_o_inexistente_falla(claves):
    with pytest.raises(M.ErrorModelo, match="no hay clave"):
        M.clave_de_rol("auditor")
    (claves / "vacia").write_text("\n", encoding="utf-8")
    (claves / "vacia").chmod(0o600)
    with pytest.raises(M.ErrorModelo, match="vacía"):
        M.clave_de_rol("vacia")


# Claude

def test_claude_corre_aislado(claude_falso):
    r = M.llamar("claude", pedido(modelo="sonnet"))
    v = json.loads(claude_falso.read_text(encoding="utf-8"))
    assert r.texto == "revisado" and r.costo_usd == 0 and r.tokens["costo_estimado"] == 0.5
    assert v["stdin"] == "hola" and not v["tiene_clave"] and "motor-claude-" in v["cwd"]
    a = v["argv"]
    assert a[a.index("--tools") + 1] == "" and a[a.index("--setting-sources") + 1] == "local"
    assert "--strict-mcp-config" in a and "--no-session-persistence" in a and a[a.index("--model") + 1] == "sonnet"


def test_claude_recibe_solo_herramientas_web(claude_falso):
    M.llamar("claude", pedido(modelo="sonnet", herramientas=("WebSearch", "WebFetch")))
    a = json.loads(claude_falso.read_text(encoding="utf-8"))["argv"]
    assert a[a.index("--tools") + 1] == "WebSearch,WebFetch"
    assert a[a.index("--allowedTools") + 1] == "WebSearch,WebFetch"


def test_claude_sin_herramientas_no_concede_permisos(claude_falso):
    M.llamar("claude", pedido(modelo="sonnet"))
    a = json.loads(claude_falso.read_text(encoding="utf-8"))["argv"]
    assert "--allowedTools" not in a and a[a.index("--tools") + 1] == ""


@pytest.mark.parametrize("h", ["Bash", "Write", "Edit", "Read"])
def test_claude_niega_lo_demas(claude_falso, h):
    with pytest.raises(S.Bloqueado, match="no permitidas"):
        M.llamar("claude", pedido(modelo="sonnet", herramientas=(h,)))
    assert not claude_falso.exists()


def test_claude_con_error_falla(tmp_path, monkeypatch):
    f = falso(tmp_path, "c", 'sys.stdin.read(); print(json.dumps({"is_error": True, "result": "sin cupo"}))')
    monkeypatch.setenv("CLAUDE_BIN", str(f))
    with pytest.raises(M.ErrorModelo, match="sin cupo"):
        M.llamar("claude", pedido(modelo="sonnet"))


def test_tiempo_corta_el_proceso(tmp_path, monkeypatch):
    f = falso(tmp_path, "c", "import time; time.sleep(30)")
    monkeypatch.setenv("CLAUDE_BIN", str(f))
    with pytest.raises(M.ErrorModelo, match="pasó el tiempo"):
        M.llamar("claude", pedido(modelo="sonnet", timeout_s=1))


# Modelos gratuitos

def test_opencode_niega_todo_al_agente(opencode_falso):
    r = M.llamar("opencode", pedido(modelo="opencode/mimo-v2.6-flash-free"))
    v = json.loads(opencode_falso.read_text(encoding="utf-8"))
    assert r.texto == "gratis" and '"*": deny' in v["agente"] and "external_directory: deny" in v["agente"]
    assert "motor-opencode-" in v["cwd"] and "worker" in v["argv"]


def test_opencode_solo_acepta_sus_modelos(opencode_falso):
    with pytest.raises(S.Bloqueado, match="solo es para"):
        M.llamar("opencode", pedido(modelo="deepseek/deepseek-v4-pro"))


def test_opencode_reporta_errores(tmp_path, monkeypatch):
    f = falso(tmp_path, "o", 'print(json.dumps({"type": "error", "error": "agotado"}))')
    monkeypatch.setenv("OPENCODE_BIN", str(f))
    with pytest.raises(M.ErrorModelo, match="agotado"):
        M.llamar("opencode", pedido(modelo="opencode/x-free"))


def test_opencode_no_esconde_el_motivo_cuando_sale_con_error(tmp_path, monkeypatch):
    f = falso(tmp_path, "o", 'print(json.dumps({"type": "error", "error": "cupo gratuito agotado"})); sys.exit(1)')
    monkeypatch.setenv("OPENCODE_BIN", str(f))
    with pytest.raises(M.ErrorModelo, match="cupo gratuito agotado"):
        M.llamar("opencode", pedido(modelo="opencode/x-free"))


# Ollama

def test_ollama_local_con_imagen(servidor):
    r = M.llamar("ollama", pedido(modelo="qwen2.5vl:3b", imagenes=(b"png",)))
    assert r.texto == "local" and Servidor.recibido[0]["ruta"] == "/api/chat"
    assert Servidor.recibido[0]["cuerpo"]["messages"][1]["images"] == ["cG5n"]


def test_ollama_rechaza_cloud(servidor):
    with pytest.raises(S.Bloqueado, match="no es local"):
        M.llamar("ollama", pedido(modelo="deepseek-v4-pro:cloud"))
    assert not Servidor.recibido


def test_ollama_rechaza_otra_maquina(monkeypatch):
    monkeypatch.setenv("OLLAMA_URL", "http://ejemplo.invalid:11434")
    with pytest.raises(S.Bloqueado, match="esta máquina"):
        M.llamar("ollama", pedido(modelo="qwen3:8b"))


def test_ollama_no_pasa_por_saneo_porque_no_sale(servidor):
    assert M.llamar("ollama", pedido(modelo="qwen3:8b", texto="de ana@mail.co")).texto == "local"


# Lo común a todas las vías

@pytest.mark.parametrize("via, modelo", [("deepseek", "deepseek-v4-pro"), ("claude", "sonnet"), ("opencode", "opencode/x-free")])
def test_dato_personal_no_sale_por_ninguna_via_externa(servidor, claves, claude_falso, opencode_falso, via, modelo):
    with pytest.raises(S.Bloqueado, match="posible dato personal"):
        M.llamar(via, pedido(modelo=modelo, texto="escriba a ana@mail.co"))
    assert not Servidor.recibido and not claude_falso.exists() and not opencode_falso.exists()


def test_el_sistema_tambien_pasa_por_saneo(servidor, claves):
    with pytest.raises(S.Bloqueado):
        M.llamar("deepseek", pedido(sistema="de ana@mail.co"))


def test_termino_privado_detiene(servidor, claves):
    with pytest.raises(S.Bloqueado, match="término privado"):
        M.llamar("deepseek", pedido(texto="Hospital Secreto"), ["hospital secreto"])


def test_imagen_no_sale_a_una_via_externa(servidor, claves):
    with pytest.raises(S.Bloqueado, match="imagen"):
        M.llamar("deepseek", pedido(imagenes=(b"x",)))


def test_respuesta_vacia_falla(servidor, claves):
    Servidor.respuesta["choices"][0]["message"]["content"] = "  "
    with pytest.raises(M.ErrorModelo, match="vacía"):
        M.llamar("deepseek", pedido())


def test_salida_demasiado_grande_falla(servidor, claves):
    with pytest.raises(M.ErrorModelo, match="bytes"):
        M.llamar("deepseek", pedido(max_bytes=3))


def test_via_desconocida(servidor):
    with pytest.raises(S.Bloqueado, match="desconocida"):
        M.llamar("otra", pedido())


# Respaldo en cadena, como en video

def test_respaldo_pasa_al_siguiente_y_anota_el_fallo(servidor, opencode_falso, tmp_path, monkeypatch):
    f = falso(tmp_path, "o", 'sys.exit(3)')
    monkeypatch.setenv("OPENCODE_BIN", str(f))
    via, r, fallos = M.con_respaldo([("opencode", "opencode/a-free"), ("ollama", "qwen3:8b")], pedido())
    assert via == "ollama" and r.texto == "local" and "opencode/a-free" in fallos[0]


def test_respaldo_valida_antes_de_aceptar(servidor, opencode_falso):
    via, r, fallos = M.con_respaldo([("opencode", "opencode/a-free"), ("ollama", "qwen3:8b")], pedido(),
                                    lambda t: ["no sirve"] if t == "gratis" else [])
    assert via == "ollama" and "no sirve" in fallos[0]


def test_sin_ruta_valida_falla(servidor):
    with pytest.raises(M.ErrorModelo, match="ninguna ruta"):
        M.con_respaldo([("ollama", "qwen3:8b")], pedido(), lambda t: ["mal"])


def test_dato_personal_no_cae_a_la_siguiente_ruta(servidor, claves):
    with pytest.raises(S.Bloqueado):
        M.con_respaldo([("deepseek", "deepseek-v4-pro"), ("ollama", "qwen3:8b")], pedido(texto="ana@mail.co"))
    assert not Servidor.recibido


# Como nodo del grafo

LINEA = {"version": "1", "etapas": {"fuente": {}, "escribir": {"depende": ["fuente"]}}}


@pytest.fixture
def t(tmp_path):
    c = tmp_path / "trabajo"
    c.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=c, check=True)
    S.nuevo(c, "t", LINEA)
    (tmp_path / "agente.md").write_text("---\nname: x\n---\n\nEscribes.\n", encoding="utf-8")
    (tmp_path / "reglas.md").write_text("Regla uno.", encoding="utf-8")
    (c / "secreto.md").write_text("NO-DEBE-SALIR", encoding="utf-8")
    return c


def nodo_fuente():
    return R.Nodo(lambda ctx: R.Resultado({"f.md": "texto fuente"}), rol="f")


def test_nodo_envia_solo_reglas_y_entradas_declaradas(t, servidor, claves):
    n = N.modelo("borrador", t.parent / "agente.md", [("deepseek", "deepseek-v4-pro")], reglas=(t.parent / "reglas.md",))
    R.correr(t, LINEA, {"fuente": nodo_fuente(), "escribir": n})
    m = Servidor.recibido[0]["cuerpo"]["messages"]
    assert m[0]["content"] == "Escribes.\n" and "name: x" not in m[0]["content"]
    assert m[1]["content"].index("Regla uno.") < m[1]["content"].index("texto fuente")
    assert "NO-DEBE-SALIR" not in json.dumps(Servidor.recibido)


def test_nodo_deja_constancia_en_el_manifiesto(t, servidor, claves):
    n = N.modelo("borrador", t.parent / "agente.md", [("deepseek", "deepseek-v4-pro")])
    R.correr(t, LINEA, {"fuente": nodo_fuente(), "escribir": n})
    m = S.ultimo_manifiesto(t, "escribir")
    assert m["origen"] == "modelo" and m["ejecutor"]["modelo"] == "deepseek-v4-pro"
    assert m["resultado"]["via"] == "deepseek" and m["resultado"]["modelo_devuelto"] == "deepseek-v4-pro-real"
    assert m["prompt_sha256"] == S.sha256_bytes(b"Escribes.\n") and m["tokens"]["salida"] == 100 and m["costo_usd"] > 0


def test_modelo_gratuito_apagado_por_defecto(t):
    with pytest.raises(S.Bloqueado, match="nivel libre"):
        N.modelo("borrador", t.parent / "agente.md", [("opencode", "opencode/x-free")])


def test_modelo_gratuito_si_la_etapa_lo_admite(t, opencode_falso):
    n = N.modelo("borrador", t.parent / "agente.md", [("opencode", "opencode/x-free")], niveles=("libre",))
    R.correr(t, LINEA, {"fuente": nodo_fuente(), "escribir": n})
    assert S.ultimo_manifiesto(t, "escribir")["resultado"]["via"] == "opencode"


def test_etapa_solo_local_rechaza_las_externas(t):
    with pytest.raises(S.Bloqueado, match="no admite"):
        N.modelo("r", t.parent / "agente.md", [("deepseek", "deepseek-v4-pro")], niveles=("local",))


def test_una_via_nueva_cabe_sin_tocar_el_grafo(t, monkeypatch):
    monkeypatch.setitem(M.VIAS, "otra", lambda p: M.Respuesta("de otra vía", p.modelo))
    monkeypatch.setitem(M.NIVELES, "otra", "local")
    n = N.modelo("r", t.parent / "agente.md", [("otra", "m")])
    R.correr(t, LINEA, {"fuente": nodo_fuente(), "escribir": n})
    assert S.ultimo_manifiesto(t, "escribir")["resultado"]["via"] == "otra"


def test_contar_alimenta_el_ciclo(t, servidor, claves):
    n = N.modelo("borrador", t.parent / "agente.md", [("deepseek", "deepseek-v4-pro")], contar=lambda x: (2, 1))
    R.correr(t, LINEA, {"fuente": nodo_fuente(), "escribir": n})
    assert S.ultimo_manifiesto(t, "escribir")["resultado"]["hallazgos"] == 2
    assert S.ultimo_manifiesto(t, "escribir")["pide_puerta"] is True


@pytest.mark.parametrize("error", [http.client.IncompleteRead(b""), ConnectionResetError("reset")])
def test_respuesta_cortada_es_falla_de_la_via(claves, monkeypatch, error):
    def cortar(*a, **k):
        raise error
    monkeypatch.setattr(M.urllib.request, "urlopen", cortar)
    with pytest.raises(M.ErrorModelo, match="falló la llamada") as e:
        M.deepseek(pedido())
    assert CLAVE not in str(e.value)


class Flujo(BaseHTTPRequestHandler):
    eventos, recibido = [], []

    def do_POST(self):
        Flujo.recibido.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for e in Flujo.eventos:
            self.wfile.write((e + "\n\n").encode())

    def log_message(self, *a):
        pass


@pytest.fixture
def flujo(monkeypatch):
    s = HTTPServer(("127.0.0.1", 0), Flujo)
    threading.Thread(target=s.serve_forever, args=(0.01,), daemon=True).start()
    Flujo.recibido = []
    monkeypatch.setenv("DEEPSEEK_URL", f"http://127.0.0.1:{s.server_port}")
    yield
    s.shutdown()


def evento(**k):
    return "data: " + json.dumps(k)


def test_deepseek_lee_el_flujo_completo(flujo, claves):
    Flujo.eventos = [": keep-alive", evento(model="deepseek-v4-pro-real", choices=[{"delta": {"reasoning_content": "pienso"}}]),
                     evento(choices=[{"delta": {"content": "Ho"}}]), ": keep-alive",
                     evento(choices=[{"delta": {"content": "la."}}]),
                     evento(choices=[], usage={"prompt_tokens": 1000, "completion_tokens": 100,
                                               "prompt_cache_hit_tokens": 400}), "data: [DONE]"]
    r = M.deepseek(pedido())
    assert r.texto == "Hola." and r.modelo == "deepseek-v4-pro-real"
    assert r.tokens["entrada"] == 1000 and r.tokens["cache_leido"] == 400 and r.costo_usd > 0
    assert Flujo.recibido[0]["stream"] is True and Flujo.recibido[0]["stream_options"] == {"include_usage": True}


def test_deepseek_flujo_sin_fin_es_respuesta_cortada(flujo, claves):
    Flujo.eventos = [evento(choices=[{"delta": {"content": "media pieza"}}])]
    with pytest.raises(M.ErrorModelo, match="cortada"):
        M.deepseek(pedido())
