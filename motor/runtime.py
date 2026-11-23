"""Conduce una línea con LangGraph. La verdad sigue en los archivos: el checkpoint se puede borrar.

El orden de los pasos está en el programa: ningún modelo elige rutas. Un nodo recibe un Contexto y
devuelve texto; la envoltura escribe, registra el manifiesto y salta lo que ya está vigente.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from motor import state as S

SALTA = S.SIGUEN | {"por_aprobar", "devuelta"}


@dataclass(frozen=True)
class Contexto:
    carpeta: Path
    etapa: str
    entradas: dict[str, str]
    extras: list[str]


@dataclass
class Resultado:
    archivos: dict[str, str]
    tokens: dict = field(default_factory=dict)
    costo_usd: float = 0.0
    hallazgos: int = 0
    juicios: int = 0
    detalle: dict = field(default_factory=dict)


@dataclass
class Nodo:
    funcion: Callable[[Contexto], Resultado]
    rol: str
    origen: str = "script"
    ejecutor: dict = field(default_factory=dict)
    prompt_sha256: str = ""
    reglas_sha256: str = ""


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _anotar_llamada(carpeta: Path, registro: dict) -> None:
    with open(carpeta / "llamadas.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")


def _escribir_salidas(carpeta: Path, etapa: str, archivos: dict[str, str]) -> list[str]:
    """Cada corrida escribe en su carpeta: un artefacto ya hecho no se pisa."""
    if not archivos:
        raise S.Bloqueado(f"{etapa} no devolvió archivos")
    base = f"artefactos/{etapa}/{S.proxima_secuencia(carpeta):06d}"
    rutas = []
    for nombre, texto in archivos.items():
        if "/" in nombre or "\\" in nombre or nombre in ("", ".", ".."):
            raise S.Bloqueado(f"nombre de salida no válido: {nombre}")
        rutas.append(f"{base}/{nombre}")
        S.escribir_artefacto(carpeta, rutas[-1], texto)
    return rutas


def _ejecutar(carpeta: Path, linea: dict, etapa: str, nodo: Nodo, entradas: dict[str, str],
              extras: list[str]) -> dict:
    inicio = _ahora()
    base = {"etapa": etapa, "rol": nodo.rol, "ejecutor": nodo.ejecutor, "inicio": inicio}
    try:
        r = nodo.funcion(Contexto(carpeta, etapa, entradas, extras))
        salidas = _escribir_salidas(carpeta, etapa, r.archivos)
    except Exception as x:
        _anotar_llamada(carpeta, {**base, "estado": f"error: {x}"[:300]})
        raise
    fin = _ahora()
    m = S.registrar_corrida(
        carpeta, linea, etapa, rol=nodo.rol, origen=nodo.origen, ejecutor=nodo.ejecutor, entradas=entradas,
        salidas=salidas, inicio=inicio, fin=fin, prompt_sha256=nodo.prompt_sha256,
        reglas_sha256=nodo.reglas_sha256, tokens=r.tokens, costo_usd=r.costo_usd,
        resultado={"hallazgos": r.hallazgos, "juicios": r.juicios, **r.detalle}, pide_puerta=r.juicios > 0)
    _anotar_llamada(carpeta, {**base, "fin": fin, "estado": "ok", "tokens": r.tokens, "costo_usd": r.costo_usd})
    return m


def huellas(nodos: dict[str, Nodo]) -> dict[str, dict]:
    """La huella de hoy de cada etapa: si difiere de la registrada, la etapa da aviso (no vence ni se rehace)."""
    res = {}
    for etapa, n in nodos.items():
        h = {"prompt_sha256": n.prompt_sha256, "reglas_sha256": n.reglas_sha256}
        if n.ejecutor.get("modelo"):
            h["modelo"] = n.ejecutor["modelo"]
        res[etapa] = h
    return res


def _nodo_etapa(carpeta: Path, linea: dict, etapa: str, nodo: Nodo):
    decl = linea["etapas"][etapa]

    def correr(est: S.EstadoGrafo) -> dict:
        S.puede_correr(carpeta, linea, etapa)
        extras = est["extras"].get(etapa, [])
        costo = 0.0
        if not extras and S.vigencia(carpeta, linea)[etapa]["estado"] in SALTA:
            m = S.ultimo_manifiesto(carpeta, etapa)
        else:
            rutas = [r for previa in decl.get("depende", []) for r in S.ultimo_manifiesto(carpeta, previa)["salidas"]]
            m = _ejecutar(carpeta, linea, etapa, nodo, S.digests(carpeta, [*rutas, *extras]), extras)
            costo = m["costo_usd"]
        pendientes = {k: v for k, v in est["extras"].items() if k != etapa}
        hallazgos = m["resultado"].get("hallazgos", 0)
        ciclo = decl.get("ciclo")
        if ciclo and hallazgos and S.rondas(carpeta, etapa) < ciclo["max_rondas"]:
            # Quien corrige recibe su pieza anterior y el informe que la devolvió (bloque 3).
            anterior = S.ultimo_manifiesto(carpeta, ciclo["vuelve_a"])
            pendientes[ciclo["vuelve_a"]] = [*(anterior["salidas"] if anterior else []), *m["salidas"]]
        return {"extras": pendientes, "hallazgos": hallazgos, "costo_usd": est["costo_usd"] + costo,
                "ronda": S.rondas(carpeta, etapa), "detenido_por": None,
                "artefactos": {**est["artefactos"], etapa: S.digest_conjunto(m["salidas"])}}

    return correr


def _en_git(carpeta: Path, ruta: str) -> bool:
    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=carpeta, capture_output=True, text=True).stdout.strip()
    return bool(git("log", "-1", "--format=%H", "--", ruta)) and not git("status", "--porcelain", "--", ruta)


def _devolver(est: S.EstadoGrafo, etapa: str, ruta: str) -> dict:
    return {"detenido_por": "devuelta", "extras": {**est["extras"], etapa: [ruta]}}


def _exigir_commit(carpeta: Path, id_: str) -> None:
    if not _en_git(carpeta, f"constancias/{id_}.json"):
        raise S.Bloqueado(f"{id_} no tiene commit")


def _nodo_puerta(carpeta: Path, linea: dict, etapa: str, puerta: str):
    def decidir(est: S.EstadoGrafo) -> dict:
        # LangGraph repite este nodo desde aquí al reanudar, así que todo control va antes del
        # interrupt() y solo lee. Decide el disco; lo que traiga la reanudación no prueba nada.
        estado = S.vigencia(carpeta, linea)[etapa]
        if estado["estado"] not in (*S.SIGUEN, "por_aprobar", "devuelta"):
            raise S.Bloqueado(f"{puerta}: {etapa} está {estado['estado']}. " + "; ".join(estado["causas"]))
        id_ = S.ultima_constancia(carpeta, linea, puerta)
        if estado["estado"] in S.SIGUEN:
            if id_:  # una puerta condicional que no se pidió no tiene constancia
                _exigir_commit(carpeta, id_)
            return {"detenido_por": None}
        if estado["estado"] == "devuelta":
            _exigir_commit(carpeta, id_)
            return _devolver(est, etapa, f"constancias/{id_}.json")
        respuesta = interrupt({"puerta": puerta, "etapa": etapa, "sujetos": S.sujetos(carpeta, linea, puerta)})
        S.leer_constancia(carpeta, puerta, respuesta)
        raise S.Bloqueado(f"{respuesta} no decide sobre lo que hay hoy en {puerta}")

    return decidir


def construir(carpeta: Path, linea: dict, nodos: dict[str, Nodo]) -> StateGraph:
    S.validar_linea(linea)
    faltan = set(linea["etapas"]) - set(nodos)
    if faltan:
        raise S.Bloqueado(f"faltan nodos: {sorted(faltan)}")
    grafo = StateGraph(S.EstadoGrafo)
    etapas = list(linea["etapas"])
    grafo.add_edge(START, etapas[0])
    for i, etapa in enumerate(etapas):
        decl = linea["etapas"][etapa]
        puerta, ciclo = decl.get("puerta"), decl.get("ciclo")
        siguiente = etapas[i + 1] if i + 1 < len(etapas) else END
        grafo.add_node(etapa, _nodo_etapa(carpeta, linea, etapa, nodos[etapa]))
        ultimo = etapa
        if puerta:
            grafo.add_node(puerta, _nodo_puerta(carpeta, linea, etapa, puerta))
            grafo.add_edge(etapa, puerta)
            ultimo = puerta
        if not puerta and not ciclo:
            grafo.add_edge(etapa, siguiente)
            continue

        def ruta(est: S.EstadoGrafo, etapa=etapa, ciclo=ciclo, siguiente=siguiente) -> str:
            if est["detenido_por"] == "devuelta":
                return etapa
            if ciclo and est["extras"].get(ciclo["vuelve_a"]):
                return ciclo["vuelve_a"]
            return siguiente

        destinos = {etapa, siguiente, *([ciclo["vuelve_a"]] if ciclo else [])}
        grafo.add_conditional_edges(ultimo, ruta, sorted(destinos))
    return grafo


def dibujar(linea: dict) -> str:
    """Dibujo del grafo en Mermaid, para auditarlo. No corre nada y no usa red."""
    nodos = {e: Nodo(lambda ctx: Resultado({}), rol=e) for e in linea["etapas"]}
    return construir(Path("."), linea, nodos).compile().get_graph().draw_mermaid()


def correr(carpeta: Path, linea: dict, nodos: dict[str, Nodo], reanudar: str | None = None) -> dict:
    """Avanza hasta la próxima puerta o el final. Devuelve lo que quedó pendiente."""
    trabajo = S.leer(carpeta)["id"]
    if S.siguiente(carpeta, linea) == "rechazado":
        return {"estado": "rechazado"}
    (carpeta / ".cache").mkdir(exist_ok=True)
    config = {"configurable": {"thread_id": trabajo}, "recursion_limit": 200}
    inicial: S.EstadoGrafo = {"trabajo": trabajo, "corrida": _ahora(), "linea_version": linea["version"],
                              "artefactos": {}, "ronda": 0, "costo_usd": 0.0, "detenido_por": None,
                              "hallazgos": 0, "extras": {}}
    with SqliteSaver.from_conn_string(str(carpeta / ".cache" / "checkpoints.sqlite")) as memoria:
        app = construir(carpeta, linea, nodos).compile(checkpointer=memoria)
        pendiente = reanudar and app.get_state(config).next
        salida = app.invoke(Command(resume=reanudar) if pendiente else inicial, config, durability="sync")
    # Una etapa con aviso no se rehace sola: se informa para que la persona decida.
    avisos = {e: v["causas"] for e, v in S.vigencia(carpeta, linea, huellas(nodos)).items() if v["estado"] == "aviso"}
    extra = {"avisos": avisos} if avisos else {}
    if salida.get("__interrupt__"):
        return {"estado": "detenido", **salida["__interrupt__"][0].value, **extra}
    return {"estado": "terminado", "costo_usd": salida.get("costo_usd", 0.0), "hallazgos": salida.get("hallazgos", 0),
            **extra}


def decidir(carpeta: Path, linea: dict, puerta: str, por: str, fecha: str, **opciones) -> str:
    """Escribe la constancia y hace su commit. Es la única vía para que una puerta avance."""
    constancia = S.aprobar(carpeta, linea, puerta, por, fecha, **opciones)
    ruta = f"constancias/{constancia['id']}.json"
    for comando in (["add", "--", ruta], ["commit", "-q", "-m", f"{puerta}: {constancia['predicate']['decision']}",
                                          "--", ruta]):
        r = subprocess.run(["git", *comando], cwd=carpeta, capture_output=True, text=True)
        if r.returncode:
            raise S.Bloqueado(f"no se pudo hacer commit de {ruta}: {r.stderr.strip()}")
    return constancia["id"]
