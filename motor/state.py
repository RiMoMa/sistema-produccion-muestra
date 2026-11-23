"""Contrato del motor: manifiestos, aprobaciones ligadas a hash y vigencia. Sin red ni medios.

Los archivos mandan. El estado de un trabajo se calcula desde lo que hay en disco, así que un
checkpoint se puede borrar sin perder nada. No importa LangGraph. Procedencia en PROCEDENCIA.md.

Una línea es un dict, en orden de ejecución:

    {"version": "1", "aprobadores": ["Persona"],
     "etapas": {"extraer": {"depende": [], "puerta": "P1"},
                "producir": {"depende": ["extraer"]},
                "renderizar": {"depende": ["producir"], "puerta": "P4", "aprueba": ["producir"]}}}

`aprueba` suma a lo que la puerta aprueba las salidas de otras etapas. Con `condicional`, la puerta
solo se exige si la corrida la pidió (`pide_puerta`). `ciclo` declara que una etapa de revisión
devuelve a otra: {"vuelve_a": "producir", "max_rondas": 2}.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path, PurePosixPath
from typing import TypedDict

ORIGENES = {"modelo", "script"}
DECISIONES = {"aprobada", "devuelta", "rechazada"}
SIGUEN = {"vigente", "aviso"}
CAMPOS_AVISO = ("prompt_sha256", "reglas_sha256", "modelo", "linea_version")
TIPO_STATEMENT = "https://in-toto.io/Statement/v1"
TIPO_PREDICADO = "sistema-produccion/aprobacion/v1"


class Bloqueado(RuntimeError):
    pass


class EstadoGrafo(TypedDict):
    """Lo único que guarda el orquestador: referencias y hashes, nunca texto."""
    trabajo: str
    corrida: str
    linea_version: str
    artefactos: dict[str, str]
    ronda: int
    costo_usd: float
    detenido_por: str | None
    hallazgos: int
    extras: dict[str, list[str]]


# Hashes

def sha256_bytes(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


def sha256_archivo(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def digest_conjunto(sujetos: dict[str, str]) -> str:
    """Un solo hash para varios archivos: sha256 de las líneas ordenadas ruta y digest."""
    return sha256_bytes("".join(f"{r}\0{d}\n" for r, d in sorted(sujetos.items())).encode())


def _sello(doc: dict) -> str:
    resto = {k: v for k, v in doc.items() if k != "sello"}
    return sha256_bytes(json.dumps(resto, sort_keys=True, ensure_ascii=False).encode())


# Disco

def _escribir(ruta: Path, datos: bytes, exclusivo: bool = False) -> None:
    """Escritura atómica. Con `exclusivo`, nunca pisa un archivo que ya exista."""
    fd, tmp = tempfile.mkstemp(dir=ruta.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(datos)
            f.flush()
            os.fsync(f.fileno())
        if exclusivo:
            try:
                os.link(tmp, ruta)
            except FileExistsError:
                raise Bloqueado(f"ya existe {ruta.name}") from None
        else:
            os.replace(tmp, ruta)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    d = os.open(ruta.parent, os.O_RDONLY)
    try:
        os.fsync(d)
    finally:
        os.close(d)


def _json(doc: dict) -> bytes:
    return json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True).encode()


def _ruta(carpeta: Path, relativa: str) -> Path:
    """Toda ruta de un manifiesto es relativa al trabajo y no sale de él."""
    p = PurePosixPath(relativa)
    final = (carpeta / relativa).resolve()
    if p.is_absolute() or ".." in p.parts or not final.is_relative_to(carpeta.resolve()):
        raise Bloqueado(f"ruta fuera del trabajo: {relativa}")
    return carpeta / relativa


def digests(carpeta: Path, rutas: list[str]) -> dict[str, str]:
    """Foto de las entradas. El nodo la toma antes de llamar al modelo."""
    return {r: sha256_archivo(_ruta(carpeta, r)) for r in rutas}


def escribir_artefacto(carpeta: Path, ruta: str, texto: str) -> None:
    destino = _ruta(carpeta, ruta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    _escribir(destino, texto.encode())


def leer(carpeta: Path) -> dict:
    return json.loads((carpeta / "trabajo.json").read_text(encoding="utf-8"))


def guardar(carpeta: Path, trabajo: dict) -> None:
    _escribir(carpeta / "trabajo.json", _json(trabajo))


def nuevo(carpeta: Path, id_: str, linea: dict) -> dict:
    validar_linea(linea)
    for sub in ("artefactos", "corridas", "constancias"):
        (carpeta / sub).mkdir(parents=True, exist_ok=True)
    trabajo = {"id": id_, "linea_version": linea["version"]}
    guardar(carpeta, trabajo)
    return trabajo


# Línea

def validar_linea(linea: dict) -> None:
    vistas: set[str] = set()
    puertas: set[str] = set()
    for etapa, decl in linea["etapas"].items():
        for previa in decl.get("depende", []):
            if previa not in vistas:
                raise Bloqueado(f"{etapa} depende de {previa}, que no va antes")
        for otra in decl.get("aprueba", []):
            if otra not in decl.get("depende", []):
                raise Bloqueado(f"{etapa} aprueba {otra}, que no está entre sus dependencias")
        vuelve = decl.get("ciclo", {}).get("vuelve_a")
        if vuelve and vuelve not in vistas:
            raise Bloqueado(f"{etapa} vuelve a {vuelve}, que no va antes")
        if decl.get("condicional") and not decl.get("puerta"):
            raise Bloqueado(f"{etapa} es condicional y no tiene puerta")
        puerta = decl.get("puerta")
        if puerta in puertas:
            raise Bloqueado(f"puerta repetida: {puerta}")
        if puerta:
            puertas.add(puerta)
        vistas.add(etapa)
    if puertas and not linea.get("aprobadores"):
        raise Bloqueado("una línea con puertas necesita aprobadores")


def _etapa(linea: dict, etapa: str) -> dict:
    if etapa not in linea["etapas"]:
        raise Bloqueado(f"etapa desconocida: {etapa}")
    return linea["etapas"][etapa]


def _etapa_de_puerta(linea: dict, puerta: str) -> str:
    for etapa, decl in linea["etapas"].items():
        if decl.get("puerta") == puerta:
            return etapa
    raise Bloqueado(f"puerta desconocida: {puerta}")


# Manifiestos

def _cargar(carpeta: Path, sub: str) -> list[dict]:
    """Un archivo ilegible no se salta: entra como corrupto para que lo vea la vigencia."""
    docs = []
    for f in sorted((carpeta / sub).glob("*.json")):
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
            if not isinstance(doc, dict) or (sub == "corridas" and not {"secuencia", "etapa"} <= doc.keys()):
                raise ValueError
        except ValueError:
            numero, _, nombre = f.stem.partition("-")
            doc = {"secuencia": int(numero) if numero.isdigit() else 0, "etapa": nombre, "corrupto": True}
        doc["_archivo"] = f.stem
        docs.append(doc)
    return docs


def _sin_archivo(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if k != "_archivo"}


def _rotura(manifiestos: list[dict]) -> int | None:
    """Primera secuencia desde la que la cadena deja de ser confiable."""
    previo = ""
    for esperado, m in enumerate(manifiestos, 1):
        if (m.get("corrupto") or m["secuencia"] != esperado or m.get("previo") != previo
                or m.get("sello") != _sello(_sin_archivo(m))):
            return esperado
        previo = m["sello"]
    return None


def _ultimo(manifiestos: list[dict], etapa: str) -> dict | None:
    return next((m for m in reversed(manifiestos) if m["etapa"] == etapa), None)


def _anexar(carpeta: Path, cuerpo: dict) -> dict:
    todos = _cargar(carpeta, "corridas")
    if _rotura(todos) is not None:
        raise Bloqueado("la cadena de manifiestos está rota")
    m = {**cuerpo, "secuencia": len(todos) + 1, "previo": todos[-1]["sello"] if todos else ""}
    m["sello"] = _sello(m)
    _escribir(carpeta / "corridas" / f"{m['secuencia']:06d}-{m['etapa']}.json", _json(m), exclusivo=True)
    return m


def registrar_corrida(carpeta: Path, linea: dict, etapa: str, *, rol: str, origen: str, ejecutor: dict,
                      entradas: dict[str, str], salidas: list[str], inicio: str, fin: str,
                      prompt_sha256: str = "", reglas_sha256: str = "",
                      tokens: dict | None = None, costo_usd: float = 0.0,
                      resultado: dict | None = None, pide_puerta: bool = False) -> dict:
    """Se llama al final, con las salidas ya escritas. Sin manifiesto no hay producción."""
    _etapa(linea, etapa)
    if origen not in ORIGENES:
        raise Bloqueado(f"origen no válido: {origen}")
    if not salidas:
        raise Bloqueado(f"{etapa} no declara salidas")
    return _anexar(carpeta, {
        "etapa": etapa, "rol": rol, "origen": origen, "ejecutor": ejecutor,
        "linea_version": linea["version"], "prompt_sha256": prompt_sha256,
        "reglas_sha256": reglas_sha256, "entradas": entradas,
        "salidas": digests(carpeta, salidas), "inicio": inicio, "fin": fin,
        "tokens": tokens or {}, "costo_usd": costo_usd, "resultado": resultado or {},
        "pide_puerta": pide_puerta})


def registrar_edicion(carpeta: Path, linea: dict, etapa: str, ruta: str, por: str, fecha: str) -> dict:
    """Una edición humana no es un error, pero queda escrita antes de poder aprobarse."""
    _etapa(linea, etapa)
    _exigir_aprobador(linea, por)
    previo = _ultimo(_cargar(carpeta, "corridas"), etapa)
    if previo is None or ruta not in previo.get("salidas", {}):
        raise Bloqueado(f"{ruta} no es salida de {etapa}")
    nuevo_digest = sha256_archivo(_ruta(carpeta, ruta))
    if nuevo_digest == previo["salidas"][ruta]:
        raise Bloqueado(f"{ruta} no cambió")
    return _anexar(carpeta, {
        **{k: previo[k] for k in ("etapa", "linea_version", "prompt_sha256", "reglas_sha256", "entradas",
                                  "resultado", "pide_puerta")},
        "rol": "edicion", "origen": "humano", "ejecutor": {"por": por},
        "salidas": {**previo["salidas"], ruta: nuevo_digest}, "inicio": fecha, "fin": fecha,
        "tokens": {}, "costo_usd": 0.0,
        "edita": {"ruta": ruta, "anterior": previo["salidas"][ruta], "nuevo": nuevo_digest}})


def ultimo_manifiesto(carpeta: Path, etapa: str) -> dict | None:
    return _ultimo(_cargar(carpeta, "corridas"), etapa)


def rondas(carpeta: Path, etapa: str) -> int:
    """Corridas hechas por un ejecutor. Sale del disco, así sobrevive a un checkpoint borrado."""
    return sum(1 for m in _cargar(carpeta, "corridas") if m["etapa"] == etapa and m.get("origen") != "humano")


def proxima_secuencia(carpeta: Path) -> int:
    return len(_cargar(carpeta, "corridas")) + 1


# Aprobaciones

def _exigir_aprobador(linea: dict, por: str) -> None:
    if por not in linea.get("aprobadores", []):
        raise Bloqueado(f"{por!r} no es aprobador de esta línea")


def _sujetos(linea: dict, etapa: str, manifiestos: list[dict]) -> dict[str, str]:
    sujetos: dict[str, str] = {}
    for e in [*linea["etapas"][etapa].get("aprueba", []), etapa]:
        m = _ultimo(manifiestos, e)
        if m is None or m.get("corrupto"):
            raise Bloqueado(f"{e} no tiene artefacto que aprobar")
        sujetos.update(m["salidas"])
    return sujetos


def _constancias(carpeta: Path, trabajo: str, puerta: str) -> list[dict]:
    """Solo cuentan las íntegras, de este trabajo y de esta puerta."""
    validas = []
    for c in _cargar(carpeta, "constancias"):
        p = c.get("predicate", {})
        if (not c.get("corrupto") and c.get("sello") == _sello(_sin_archivo(c))
                and p.get("trabajo") == trabajo and p.get("puerta") == puerta):
            validas.append(c)
    return validas


def _digest_constancia(c: dict) -> str:
    return digest_conjunto({s["name"]: s["digest"]["sha256"] for s in c["subject"]})


def _decision(carpeta: Path, trabajo: str, puerta: str, sujetos: dict[str, str]) -> str | None:
    """Vale la última decisión sobre estos digests exactos. Revocar es escribir otra."""
    actual = digest_conjunto(sujetos)
    hechas = [c for c in _constancias(carpeta, trabajo, puerta) if _digest_constancia(c) == actual]
    return hechas[-1]["predicate"]["decision"] if hechas else None


def aprobar(carpeta: Path, linea: dict, puerta: str, por: str, fecha: str, decision: str = "aprobada",
            observacion: str = "", visto: dict[str, str] | None = None) -> dict:
    """Escribe la constancia sobre los digests de hoy. `por` no tiene valor por defecto a propósito."""
    etapa = _etapa_de_puerta(linea, puerta)
    _exigir_aprobador(linea, por)
    if decision not in DECISIONES:
        raise Bloqueado(f"decisión no válida: {decision}")
    if decision == "devuelta" and not observacion.strip():
        raise Bloqueado("devolver exige una observación")
    v = vigencia(carpeta, linea)[etapa]
    if v["estado"] in ("pendiente", "vencida"):
        raise Bloqueado(f"{puerta} no se puede decidir: {etapa} está {v['estado']}. " + "; ".join(v["causas"]))
    sujetos = _sujetos(linea, etapa, _cargar(carpeta, "corridas"))
    c = {"_type": TIPO_STATEMENT, "predicateType": TIPO_PREDICADO,
         "subject": [{"name": r, "digest": {"sha256": d}} for r, d in sorted(sujetos.items())],
         "predicate": {"decision": decision, "puerta": puerta, "trabajo": leer(carpeta)["id"], "por": por,
                       "fecha": fecha, "linea_version": linea["version"],
                       "conjunto_sha256": digest_conjunto(sujetos), "observacion": observacion,
                       "visto": [{"name": r, "digest": {"sha256": d}} for r, d in sorted((visto or {}).items())]}}
    c["sello"] = _sello(c)
    numero = len(list((carpeta / "constancias").glob("*.json"))) + 1
    id_ = f"{numero:06d}-{puerta}"
    _escribir(carpeta / "constancias" / f"{id_}.json", _json(c), exclusivo=True)
    return {**c, "id": id_}


def leer_constancia(carpeta: Path, puerta: str, id_: str) -> dict:
    """Devuelve la constancia solo si es íntegra y de este trabajo y esta puerta."""
    if "/" in id_ or "\\" in id_ or ".." in id_:
        raise Bloqueado(f"identificador no válido: {id_}")
    c = next((x for x in _constancias(carpeta, leer(carpeta)["id"], puerta) if x["_archivo"] == id_), None)
    if c is None:
        raise Bloqueado(f"no hay constancia válida {id_} de {puerta} en este trabajo")
    return c


def sujetos(carpeta: Path, linea: dict, puerta: str) -> dict[str, str]:
    return _sujetos(linea, _etapa_de_puerta(linea, puerta), _cargar(carpeta, "corridas"))


def ultima_constancia(carpeta: Path, linea: dict, puerta: str) -> str | None:
    """Identificador de la última decisión sobre los digests de hoy, si la hay."""
    etapa = _etapa_de_puerta(linea, puerta)
    actual = digest_conjunto(_sujetos(linea, etapa, _cargar(carpeta, "corridas")))
    hechas = [c for c in _constancias(carpeta, leer(carpeta)["id"], puerta) if _digest_constancia(c) == actual]
    return hechas[-1]["_archivo"] if hechas else None


# Vigencia

def _causas_archivos(carpeta: Path, m: dict) -> list[str]:
    if m.get("corrupto"):
        return []
    causas = []
    for clase, grupo in (("entrada", m["entradas"]), ("salida", m["salidas"])):
        for ruta, digest in grupo.items():
            f = _ruta(carpeta, ruta)
            if not f.exists():
                causas.append(f"falta la {clase} {ruta}")
            elif sha256_archivo(f) != digest:
                causas.append(f"cambió la {clase} {ruta}")
    return causas


def _avisos(m: dict, actual: dict | None) -> list[str]:
    actual = actual or {}
    registrado = {**m, "modelo": m["ejecutor"].get("modelo", "")}
    return [f"cambió {k}" for k in CAMPOS_AVISO if k in actual and actual[k] != registrado.get(k, "")]


def vigencia(carpeta: Path, linea: dict, actual: dict[str, dict] | None = None) -> dict[str, dict]:
    """Estado de cada etapa con su causa. Detecta y no rehace nada.

    Estados: pendiente, por_aprobar, vigente, aviso, vencida, devuelta, rechazada.
    `actual` trae por etapa la huella de hoy (CAMPOS_AVISO): si difiere da aviso y no vence.
    """
    validar_linea(linea)
    todos = _cargar(carpeta, "corridas")
    rota = _rotura(todos)
    trabajo = leer(carpeta)["id"]
    estados: dict[str, dict] = {}
    for etapa, decl in linea["etapas"].items():
        m = _ultimo(todos, etapa)
        if m is None:
            estados[etapa] = {"estado": "pendiente", "causas": []}
            continue
        causas = _causas_archivos(carpeta, m)
        if rota is not None and m["secuencia"] >= rota:
            causas.insert(0, "manifiesto alterado o borrado")
        for previa in decl.get("depende", []):
            if estados[previa]["estado"] not in SIGUEN:
                causas.append(f"depende de {previa}, que está {estados[previa]['estado']}")
            elif not m.get("corrupto"):
                # Un artefacto viejo sigue intacto en disco: hay que comparar con la última corrida.
                for ruta, digest in _ultimo(todos, previa)["salidas"].items():
                    if m["entradas"].get(ruta) != digest:
                        causas.append(f"{previa} se rehízo: falta {ruta}")
        if causas:
            estados[etapa] = {"estado": "vencida", "causas": causas}
            continue
        puerta = decl.get("puerta")
        if decl.get("condicional") and not m.get("pide_puerta"):
            puerta = None
        decision = _decision(carpeta, trabajo, puerta, _sujetos(linea, etapa, todos)) if puerta else "aprobada"
        if decision is None:
            estados[etapa] = {"estado": "por_aprobar", "causas": [f"falta aprobar {puerta}"]}
        elif decision != "aprobada":
            estados[etapa] = {"estado": decision, "causas": [f"{puerta}: {decision}"]}
        else:
            avisos = _avisos(m, (actual or {}).get(etapa))
            estados[etapa] = {"estado": "aviso" if avisos else "vigente", "causas": avisos}
    return estados


def puede_correr(carpeta: Path, linea: dict, etapa: str) -> None:
    """Lanza Bloqueado si falta una etapa previa o una aprobación previa."""
    decl = _etapa(linea, etapa)
    estados = vigencia(carpeta, linea)
    for nombre, e in estados.items():
        if e["estado"] == "rechazada":
            raise Bloqueado(f"trabajo rechazado en {nombre}")
    for previa in decl.get("depende", []):
        e = estados[previa]
        if e["estado"] not in SIGUEN:
            raise Bloqueado(f"{previa} está {e['estado']}: " + "; ".join(e["causas"]))


def siguiente(carpeta: Path, linea: dict) -> str:
    for etapa, e in vigencia(carpeta, linea).items():
        if e["estado"] in SIGUEN:
            continue
        if e["estado"] == "por_aprobar":
            return f"revisión {linea['etapas'][etapa]['puerta']}"
        return "rechazado" if e["estado"] == "rechazada" else etapa
    return "terminado"
