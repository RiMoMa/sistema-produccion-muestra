"""Nodos del motor que cualquier línea puede usar."""
from __future__ import annotations

import json
import re
from pathlib import Path

from motor import contexto as X
from motor import modelos as M
from motor import revisar as V
from motor import state as S
from motor.runtime import Contexto, Nodo, Resultado

REVISABLES = (".md", ".html", ".htm")


def revision_mecanica(reglas: Path) -> Nodo:
    """Revisa las entradas con las reglas de la instancia. Las fallas cuentan como hallazgos del ciclo."""
    cargadas = V.leer_reglas(str(reglas))

    def funcion(ctx: Contexto) -> Resultado:
        informe = {}
        for ruta in ctx.entradas:
            if ruta.lower().endswith(REVISABLES):
                lineas = V.texto_visible(str(ctx.carpeta / ruta)).splitlines()
                informe[ruta] = V.revisar(lineas, ruta, cargadas)
        fallas = sum(1 for hs in informe.values() for h in hs if h["clase"] == "falla")
        texto = json.dumps(informe, ensure_ascii=False, indent=2, sort_keys=True)
        return Resultado({"informe.json": texto}, hallazgos=fallas)

    return Nodo(funcion, rol="revision-mecanica", origen="script", ejecutor={"script": "revisar"},
                reglas_sha256=S.sha256_archivo(reglas))


CLASES = {"M", "R", "J"}
GRAVEDADES = {"bloquea", "corregir", "mejora"}
VERIFICADOR = Path(__file__).resolve().parents[1] / "plantillas" / "verificador.md"


def leer_informe(texto: str) -> dict:
    """El informe del verificador. Tolera la cerca ```json que algunos modelos agregan."""
    s = texto.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else ""
        s = s.rsplit("```", 1)[0]
    return json.loads(s)


def validar_informe(texto: str) -> list[str]:
    """Errores de forma. Un informe que no se puede leer no cuenta como limpio."""
    try:
        doc = leer_informe(texto)
    except ValueError:
        return ["el informe no es JSON"]
    if not isinstance(doc, dict) or not isinstance(doc.get("hallazgos"), list):
        return ["el informe no trae la lista de hallazgos"]
    errores = []
    for i, h in enumerate(doc["hallazgos"], 1):
        if not isinstance(h, dict):
            errores.append(f"hallazgo {i}: no es un objeto")
            continue
        if h.get("clase") not in CLASES:
            errores.append(f"hallazgo {i}: clase no válida")
        if h.get("gravedad") not in GRAVEDADES:
            errores.append(f"hallazgo {i}: gravedad no válida")
        if not str(h.get("que", "")).strip():
            errores.append(f"hallazgo {i}: no dice qué está mal")
        if h.get("clase") == "R" and not str(h.get("regla", "")).strip():
            errores.append(f"hallazgo {i}: R sin regla")
        if h.get("clase") == "J" and not str(h.get("decidir", "")).strip():
            errores.append(f"hallazgo {i}: J sin qué decidir")
    return errores


def contar_informe(texto: str) -> tuple[int, int]:
    """(hallazgos, juicios). M y R devuelven la pieza; J va a la puerta. El tipo 1 lo marca el motor, no el modelo."""
    hs = leer_informe(texto)["hallazgos"]
    return sum(1 for h in hs if h["clase"] in ("M", "R")), sum(1 for h in hs if h["clase"] == "J")


def _clave(h: dict) -> tuple[str, str, str]:
    return h["clase"], " ".join(str(h.get("regla", "")).lower().split()), " ".join(str(h.get("donde", "")).lower().split())


def repetidos(anterior: str, actual: str) -> list[dict]:
    """Tipo 1: un M o R de esta ronda con la misma clase, regla y lugar que uno de la ronda anterior del trabajo.
    La corrección no lo arregló, así que hay que arreglar el contexto, no la pieza."""
    previos = {_clave(h) for h in leer_informe(anterior)["hallazgos"] if h["clase"] in ("M", "R")}
    return [h for h in leer_informe(actual)["hallazgos"] if _clave(h) in previos]


def verificador(rutas: list[tuple[str, str]], reglas: tuple[Path, ...], *, agente: Path = VERIFICADOR,
                terminos: list[str] | None = None) -> Nodo:
    """Revisión en frío: sin herramientas, solo con el paquete de la instancia y lo que la etapa recibe.

    La etapa debe depender de la pieza y de la revisión mecánica, y declarar puerta condicional y ciclo.
    """
    nodo = modelo("verificador", agente, rutas, reglas=reglas, niveles=("pago",), json_salida=True,
                  nombre="hallazgos.json", validar=validar_informe, contar=contar_informe, terminos=terminos)
    llamar = nodo.funcion

    def funcion(ctx: Contexto) -> Resultado:
        if not reglas and not any(Path(r).name == "paquete-verificador.md" for r in ctx.entradas):
            raise S.Bloqueado("el verificador necesita el paquete de reglas: páselo o dependa de la etapa contexto")
        previo = S.ultimo_manifiesto(ctx.carpeta, ctx.etapa)  # antes de registrar esta ronda
        r = llamar(ctx)
        anterior = [x for x in (previo or {}).get("salidas", {}) if x.endswith("/hallazgos.json")]
        if anterior:
            tipo1 = repetidos((ctx.carpeta / anterior[0]).read_text(encoding="utf-8"), r.archivos["hallazgos.json"])
            if tipo1:
                r.hallazgos, r.juicios = 0, r.juicios + len(tipo1)
                r.detalle["tipo1"] = [f"{h['clase']} {h.get('regla', '')} en {h['donde']}".strip() for h in tipo1]
        return r

    nodo.funcion = funcion
    return nodo


# Bloque 3: producción

BORRADOR = Path(__file__).resolve().parents[1] / "plantillas" / "borrador.md"
MARCAS = re.compile(r"\[(?:FUENTE PENDIENTE|FALTA|COMPROBACI[ÓO]N PENDIENTE)\b[^\]]*\]", re.I)


def entrada(ruta: Path) -> Nodo:
    """Trae al trabajo un archivo de la instancia (el brief, por ejemplo), para que una puerta lo apruebe por hash."""

    def funcion(ctx: Contexto) -> Resultado:
        return Resultado({ruta.name: ruta.read_text(encoding="utf-8")})

    return Nodo(funcion, rol="entrada", origen="script", ejecutor={"script": "entrada"},
                reglas_sha256=S.sha256_archivo(ruta))


BLOQUES = re.compile(r"^```.*?^```", re.M | re.S)


def contar_marcas(texto: str) -> tuple[int, int]:
    """Las marcas no son error del escritor: lo que el brief no trajo. Van a la puerta, no al ciclo.
    Dentro de un bloque ``` no cuentan: ahí van los prompts que la pieza enseña, y uno puede pedir marcar lo que
    falta (decisión de Ricardo, 7 nov 2026). Esos bloques los sigue leyendo el verificador en frío."""
    return 0, len(MARCAS.findall(BLOQUES.sub("", texto)))


def borrador(rutas: list[tuple[str, str]], reglas: tuple[Path, ...], *, agente: Path = BORRADOR,
             nombre: str = "pieza.md", terminos: list[str] | None = None) -> Nodo:
    """El único escritor (D90). En una ronda de corrección el runtime le entrega su pieza anterior y el informe."""
    for via, _ in rutas:
        if via != "deepseek":
            raise S.Bloqueado(f"solo DeepSeek escribe (D90); {via} no")
    return modelo("borrador", agente, rutas, reglas=reglas, niveles=("pago",), nombre=nombre,
                  contar=contar_marcas, terminos=terminos)


# Bloque 16: fuentes

VERIFICADOR_FUENTES = Path(__file__).resolve().parents[1] / "plantillas" / "verificador-fuentes.md"
HERRAMIENTAS_WEB = ("WebSearch", "WebFetch")
RECOMENDACIONES = {"cortar", "reemplazar"}
DOI = re.compile(r"\b10\.\d{4,9}/[^\s|)\]>\"']+", re.I)
URL = re.compile(r"https?://[^\s|)\]>\"']+", re.I)
FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def referencias(texto: str) -> set[str]:
    """DOI y URL que aparecen en un texto, en minúsculas y sin la puntuación final."""
    return {x.rstrip(".,;:").lower() for x in DOI.findall(texto) + URL.findall(texto)}


def filtrar_registro(registro: Path) -> Nodo:
    """Trae del registro solo las filas cuyo DOI o URL cita la pieza. Lo que no se encuentra se abre otra vez."""

    def funcion(ctx: Contexto) -> Resultado:
        citadas = set()
        for ruta in ctx.entradas:
            citadas |= referencias((ctx.carpeta / ruta).read_text(encoding="utf-8"))
        filas = [l for l in registro.read_text(encoding="utf-8").splitlines()
                 if l.startswith("|") and referencias(l) & citadas]
        texto = "\n".join(filas) + "\n" if filas else "Sin filas del registro para esta pieza.\n"
        return Resultado({"registro-filtrado.md": texto})

    return Nodo(funcion, rol="filtrar-registro", origen="script", ejecutor={"script": "filtrar_registro"},
                reglas_sha256=S.sha256_archivo(registro))


def validar_fuentes(texto: str) -> list[str]:
    try:
        doc = leer_informe(texto)
    except ValueError:
        return ["el informe no es JSON"]
    listas = ("confirmadas", "corregidas", "no_verificables")
    if not isinstance(doc, dict) or not all(isinstance(doc.get(k), list) for k in listas):
        return ["el informe no trae las tres listas"]
    errores = []
    for k in listas:
        for i, x in enumerate(doc[k], 1):
            if not isinstance(x, dict):
                errores.append(f"{k} {i}: no es un objeto")
                continue
            if k != "no_verificables" and not URL.fullmatch(str(x.get("url", ""))):
                errores.append(f"{k} {i}: sin la URL que se abrió")
            if k == "confirmadas":
                if not FECHA.match(str(x.get("abierta_el", ""))):
                    errores.append(f"{k} {i}: sin fecha de apertura")
                fila = str(x.get("fila", "")).strip()
                if fila and not (fila.startswith("|") and fila.endswith("|")):
                    errores.append(f"{k} {i}: la fila no es una fila de tabla")
            if k == "corregidas" and not all(str(x.get(c, "")).strip()
                                             for c in ("dice_la_pieza", "dice_la_fuente", "cita_correcta")):
                errores.append(f"{k} {i}: falta qué dice la pieza, la fuente o la cita correcta")
            if k == "no_verificables":
                if not str(x.get("por_que", "")).strip():
                    errores.append(f"{k} {i}: sin por qué")
                if x.get("recomendacion") not in RECOMENDACIONES:
                    errores.append(f"{k} {i}: recomendación no válida")
    return errores


def contar_fuentes(texto: str) -> tuple[int, int]:
    """Corregidas y no verificables devuelven la pieza. No hay juicio: lo no verificable se quita."""
    doc = leer_informe(texto)
    return len(doc["corregidas"]) + len(doc["no_verificables"]), 0


def verificador_fuentes(rutas: list[tuple[str, str]], reglas: tuple[Path, ...] = (), *,
                        agente: Path = VERIFICADOR_FUENTES, terminos: list[str] | None = None) -> Nodo:
    """Abre las fuentes con la web y nada más. Solo Claude navega: sin él, la etapa falla."""
    for via, _ in rutas:
        if via != "claude":
            raise S.Bloqueado(f"el verificador de fuentes necesita la web; {via} no la tiene")
    return modelo("verificador-fuentes", agente, rutas, reglas=reglas, niveles=("pago",), json_salida=True,
                  nombre="fuentes.json", herramientas=HERRAMIENTAS_WEB, validar=validar_fuentes,
                  contar=contar_fuentes, terminos=terminos)


def anexar_registro(registro: Path) -> Nodo:
    """Después de la puerta final: suma al registro las filas confirmadas que aún no están."""

    def funcion(ctx: Contexto) -> Resultado:
        informes = [r for r in ctx.entradas if r.endswith("/fuentes.json")]
        if len(informes) != 1:
            raise S.Bloqueado(f"anexar necesita un informe de fuentes, recibió {len(informes)}")
        doc = leer_informe((ctx.carpeta / informes[0]).read_text(encoding="utf-8"))
        actual = registro.read_text(encoding="utf-8")
        ya = set(actual.splitlines())
        nuevas = []
        for x in doc["confirmadas"]:
            fila = str(x.get("fila", "")).strip()
            if fila and fila not in ya and fila not in nuevas:
                nuevas.append(fila)
        if nuevas:
            S._escribir(registro, (actual.rstrip("\n") + "\n" + "\n".join(nuevas) + "\n").encode())
        return Resultado({"anexadas.md": "\n".join(nuevas) + "\n" if nuevas else "Ninguna fila nueva.\n"})

    return Nodo(funcion, rol="anexar-registro", origen="script", ejecutor={"script": "anexar_registro"})


# Bloque 1: contexto

PAQUETE = re.compile(r"^paquete-(.+)\.md$")


def contexto(raiz: Path, tipos: list[str]) -> Nodo:
    """Arma un paquete por rol desde la instancia (`instancia.toml`). Sin modelo y sin red.

    Las etapas que lo usan dependen de esta; cada rol recibe solo el suyo. La huella cubre el manifiesto y cada
    archivo que puede entrar: si uno cambia, la etapa da aviso y no se rehace sola."""
    inst = X.leer_instancia(raiz)
    X.validar_tipos(inst, tipos)
    huella = "".join(f"{p.relative_to(inst.raiz)} {S.sha256_archivo(p)}\n" for p in inst.fuentes())

    def funcion(ctx: Contexto) -> Resultado:
        return Resultado({f"paquete-{rol}.md": texto for rol, texto in X.armar(inst, tipos).items()})

    return Nodo(funcion, rol="contexto", origen="script",
                ejecutor={"script": "contexto", "instancia": inst.nombre, "tipos": list(tipos)},
                reglas_sha256=S.sha256_bytes(huella.encode()))


def entradas_del_rol(rol: str, entradas) -> list[str]:
    """El paquete del rol primero, para la caché de prefijo; los paquetes de otros roles no se envían."""
    propio = [r for r in entradas if Path(r).name == f"paquete-{rol}.md"]
    resto = [r for r in entradas if not PAQUETE.match(Path(r).name)]
    return [*propio, *resto]


def cuerpo_agente(ruta: Path) -> str:
    """El rol vive en un archivo .md; su encabezado no se envía."""
    s = ruta.read_text(encoding="utf-8")
    if s.startswith("---\n"):
        fin = s.find("\n---", 4)
        if fin != -1:
            s = s[fin + 4:]
    return s.strip() + "\n"


def modelo(rol: str, agente: Path, rutas: list[tuple[str, str]], *, reglas: tuple[Path, ...] = (),
           niveles: tuple[str, ...] = ("pago", "local"), json_salida: bool = False, nombre: str = "salida.md",
           herramientas: tuple[str, ...] = (), validar=None, contar=None, terminos: list[str] | None = None) -> Nodo:
    """Nodo que llama a un modelo. Solo le llega lo que la etapa recibe por sus dependencias y `reglas`.

    Los modelos gratuitos quedan fuera salvo que la etapa incluya "libre" en `niveles`. `contar` recibe
    el texto y devuelve (hallazgos, juicios), para los nodos que revisan.
    """
    for via, _ in rutas:
        if via not in M.NIVELES:
            raise S.Bloqueado(f"vía desconocida: {via}")
        if M.NIVELES[via] not in niveles:
            raise S.Bloqueado(f"{rol} no admite la vía {via}, de nivel {M.NIVELES[via]}")
    sistema = cuerpo_agente(agente)
    # Lo fijo va primero, para aprovechar la caché de prefijo; lo que cambia, al final.
    fijo = "".join(f"## {r.name}\n\n{r.read_text(encoding='utf-8')}\n\n" for r in reglas)

    def funcion(ctx: Contexto) -> Resultado:
        variable = "".join(f"## {ruta}\n\n{(ctx.carpeta / ruta).read_text(encoding='utf-8')}\n\n"
                           for ruta in entradas_del_rol(rol, ctx.entradas))
        pedido = M.Pedido(rol=rol, modelo=rutas[0][1], sistema=sistema, texto=fijo + variable, json=json_salida,
                          herramientas=herramientas)
        via, r, fallos = M.con_respaldo(rutas, pedido, validar, terminos)
        hallazgos, juicios = contar(r.texto) if contar else (0, 0)
        return Resultado({nombre: r.texto}, tokens=r.tokens, costo_usd=r.costo_usd, hallazgos=hallazgos, juicios=juicios,
                         detalle={"via": via, "modelo_devuelto": r.modelo, "fallos": fallos})

    return Nodo(funcion, rol=rol, origen="modelo", ejecutor={"modelo": rutas[0][1], "rutas": [list(x) for x in rutas]},
                prompt_sha256=S.sha256_bytes(sistema.encode()), reglas_sha256=S.sha256_bytes(fijo.encode()))
