"""Bloque 1: arma el paquete de reglas de cada rol desde la instancia. No trae reglas: las lee.

La instancia declara en `instancia.toml` dónde están sus archivos, su vocabulario de tipos de pieza y qué
recibe cada rol. El paquete lleva, sin recortar, las entradas de `decisiones.md` de los tipos pedidos y de
`todas`, más las que cada una nombra en sus líneas de remisión de cabecera, en una sola dirección (D95 del
proyecto de origen), y los pendientes abiertos. Después, los archivos y las secciones que el rol declare.

La mecánica del índice es copia de `herramientas/indice-decisiones.py` del proyecto de origen (ver PROCEDENCIA.md).
Lo único que el motor fija del vocabulario son `todas` y `sin-efecto`; el resto lo declara la instancia.
"""
from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from motor import state as S

MECANICOS = {"todas", "sin-efecto"}
ENCABEZADO = re.compile(r"^### ((?:D|C|S|P|H)\d+)\b", re.M)
SECCION = re.compile(r"^#{2,3} ", re.M)  # una entrada termina en el siguiente ## o ###
ID = re.compile(r"\b((?:D|C|S|P|H)\d+)\b")
# Solo las líneas de remisión de cabecera. Las menciones dentro de tablas o del cuerpo no enlazan.
REMISION = re.compile(r"^(?:\*\*)?(?:Precisad[ao]|Enmendad[ao]|Revocad[ao]|Anulad[ao]|Reemplazad[ao]|Sin uso"
                      r"|Enmienda |Precisa |Resuelve )|^\*\d[^*]*\*\s*·")
# La tabla de revisión del corpus es historia, no regla: la entrada se corta ahí.
CORPUS = re.compile(r"^\*\*(?:Tabla de )?[Rr]evisión (?:del corpus|en frío)", re.M)
FILA = re.compile(r"^\|\s*((?:D|C|S|P|H)\d+)\s*\|([^|]*)\|")
MANIFIESTO = "instancia.toml"


@dataclass(frozen=True)
class Rol:
    decisiones: bool = True
    archivos: tuple[str, ...] = ()
    secciones: dict[str, tuple[str, ...]] = field(default_factory=dict)


@dataclass(frozen=True)
class Instancia:
    raiz: Path
    nombre: str
    decisiones: str
    indice: str
    tipos: frozenset[str]
    roles: dict[str, Rol]

    def fuentes(self) -> list[Path]:
        """Todo archivo que puede entrar a un paquete, más el manifiesto. Un cambio en cualquiera da aviso."""
        rutas = [MANIFIESTO, self.decisiones, self.indice]
        for r in self.roles.values():
            rutas += [*r.archivos, *r.secciones]
        return [self.raiz / x for x in dict.fromkeys(rutas)]


def _ruta(raiz: Path, valor, campo: str) -> str:
    if not isinstance(valor, str) or not valor.strip():
        raise S.Bloqueado(f"{MANIFIESTO}: falta {campo}")
    p = Path(valor)
    if p.is_absolute() or ".." in p.parts:
        raise S.Bloqueado(f"{MANIFIESTO}: {campo} debe quedar dentro de la instancia: {valor}")
    if not (raiz / p).is_file():
        raise S.Bloqueado(f"{MANIFIESTO}: {campo} no existe: {valor}")
    return valor


def leer_instancia(raiz: Path) -> Instancia:
    raiz = Path(raiz).resolve()
    archivo = raiz / MANIFIESTO
    if not archivo.is_file():
        raise S.Bloqueado(f"la instancia no tiene {MANIFIESTO}: {raiz}")
    try:
        d = tomllib.loads(archivo.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as x:
        raise S.Bloqueado(f"{MANIFIESTO} no se puede leer: {x}") from None
    tipos = d.get("tipos")
    if not isinstance(tipos, list) or not tipos or not all(isinstance(t, str) and t.strip() for t in tipos):
        raise S.Bloqueado(f"{MANIFIESTO}: tipos debe ser una lista de nombres")
    if set(tipos) & MECANICOS:
        raise S.Bloqueado(f"{MANIFIESTO}: {sorted(set(tipos) & MECANICOS)} los pone el motor; no van en tipos")
    roles = {}
    for nombre, r in (d.get("roles") or {}).items():
        if not isinstance(r, dict):
            raise S.Bloqueado(f"{MANIFIESTO}: roles.{nombre} no es una tabla")
        archivos = tuple(_ruta(raiz, a, f"roles.{nombre}.archivos") for a in r.get("archivos", []))
        secciones = {}
        for a, titulos in (r.get("secciones") or {}).items():
            _ruta(raiz, a, f"roles.{nombre}.secciones")
            if not isinstance(titulos, list) or not titulos:
                raise S.Bloqueado(f"{MANIFIESTO}: roles.{nombre}.secciones de {a} debe ser una lista de títulos")
            secciones[a] = tuple(titulos)
        roles[nombre] = Rol(decisiones=r.get("decisiones", True) is not False, archivos=archivos, secciones=secciones)
    if not roles:
        raise S.Bloqueado(f"{MANIFIESTO}: ningún rol declarado")
    return Instancia(raiz, str(d.get("nombre", raiz.name)), _ruta(raiz, d.get("decisiones"), "decisiones"),
                     _ruta(raiz, d.get("indice"), "indice"), frozenset(tipos) | MECANICOS, roles)


# El índice: copia fiel del script del proyecto de origen, con el vocabulario como parámetro

def entradas(texto: str) -> dict[str, str]:
    """{id: texto completo de la entrada}, en orden, de su encabezado al siguiente ### o ##."""
    marcas = list(ENCABEZADO.finditer(texto))
    cortes = sorted({m.start() for m in marcas} | {m.start() for m in SECCION.finditer(texto)} | {len(texto)})
    res = {}
    for m in marcas:
        fin = next(c for c in cortes if c > m.start())
        cuerpo = texto[m.start():fin]
        c = CORPUS.search(cuerpo)
        res[m.group(1)] = cuerpo[:c.start()] if c else cuerpo
    return res


def pendientes(texto: str) -> str:
    i = texto.find("\n## Pendientes abiertos")
    return texto[i + 1:] if i >= 0 else ""


def enlaces(ents: dict[str, str]) -> dict[str, set[str]]:
    """Cada entrada apunta a las que nombra en sus propias líneas de remisión. Que otra la nombre no la arrastra."""
    g = {k: set() for k in ents}
    for k, t in ents.items():
        for linea in t.splitlines():
            if not REMISION.search(linea):
                continue
            for otro in ID.findall(linea):
                if otro != k and otro in ents:
                    g[k].add(otro)
    return g


def leer_indice(texto: str) -> tuple[dict[str, list], list[int]]:
    filas, sueltas = {}, []
    for n, linea in enumerate(texto.splitlines(), 1):
        s = linea.strip()
        if not s or s.startswith("# "):
            continue
        if s.startswith("|"):
            m = FILA.match(s)
            if m:
                tipos = [t.strip() for t in m.group(2).split(",") if t.strip()]
                filas.setdefault(m.group(1), []).append((n, tipos))
            continue
        sueltas.append(n)
    return filas, sueltas


def comprobar(texto: str, indice: str, vocabulario: set[str] | frozenset[str]) -> tuple[list[str], dict, dict]:
    """(fallas, entradas, filas). Sin fallas, cada entrada tiene una fila con tipos del vocabulario."""
    ents = entradas(texto)
    filas, sueltas = leer_indice(indice)
    fallas = [f"l. {n}: texto fuera de la tabla" for n in sueltas]
    for k in ents:
        if k not in filas:
            fallas.append(f"{k}: sin fila en el índice")
    for k, apar in filas.items():
        if k not in ents:
            fallas.append(f"{k}: fila sin entrada en decisiones")
        if len(apar) > 1:
            fallas.append(f"{k}: {len(apar)} filas")
        for n, tipos in apar:
            if not tipos:
                fallas.append(f"l. {n}: {k} sin tipos")
            for t in tipos:
                if t not in vocabulario:
                    fallas.append(f"l. {n}: {k} con tipo desconocido: {t}")
            if "sin-efecto" in tipos and len(tipos) > 1:
                fallas.append(f"l. {n}: {k} es sin-efecto y lleva otros tipos")
    return fallas, ents, filas


def paquete(ents: dict, filas: dict, texto: str, pedidos: list[str]) -> tuple[list[str], set[str], str]:
    """(orden, base, cuerpo): las entradas de los tipos pedidos y de `todas`, cerradas por remisión."""
    g = enlaces(ents)
    quiere = set(pedidos) | {"todas"}
    base = {k for k, apar in filas.items() if k in ents and any(set(t) & quiere for _, t in apar)}
    vistos, pila = set(base), list(base)
    while pila:
        for otro in g[pila.pop()]:
            tipos_otro = {t for _, ts in filas.get(otro, []) for t in ts}
            # Solo suma lo que comparte tipo con el paquete: cada paquete lleva lo suyo.
            if otro not in vistos and tipos_otro & (quiere | {"sin-efecto"}):
                vistos.add(otro)
                pila.append(otro)
    orden = [k for k in ents if k in vistos]
    cuerpo = "".join(ents[k] for k in orden) + "\n" + pendientes(texto)
    return orden, base, cuerpo


# Lo que suma el bloque 1

def seccion(texto: str, titulo: str) -> str:
    """La sección `## titulo`, con su encabezado, hasta el siguiente `## `. Si no está o está vacía, falla."""
    m = re.search(rf"^## {re.escape(titulo)}[ \t]*$", texto, re.M)
    if not m:
        raise S.Bloqueado(f"no existe la sección «{titulo}»")
    sig = re.search(r"^## ", texto[m.end():], re.M)
    cuerpo = texto[m.start():m.end() + sig.start()] if sig else texto[m.start():]
    if not cuerpo[m.end() - m.start():].strip():
        raise S.Bloqueado(f"la sección «{titulo}» está vacía")
    return cuerpo.rstrip() + "\n"


def validar_tipos(inst: Instancia, tipos: list[str]) -> None:
    if not tipos:
        raise S.Bloqueado("el paquete necesita al menos un tipo de pieza")
    malos = [t for t in tipos if t not in inst.tipos or t in MECANICOS]
    if malos:
        raise S.Bloqueado(f"tipos que la instancia no declara: {malos}")


def armar(inst: Instancia, tipos: list[str]) -> dict[str, str]:
    """{rol: paquete}. Falla si el índice tiene fallas: no se arma un paquete al que le falte una regla."""
    validar_tipos(inst, tipos)
    texto = (inst.raiz / inst.decisiones).read_text(encoding="utf-8")
    fallas, ents, filas = comprobar(texto, (inst.raiz / inst.indice).read_text(encoding="utf-8"), inst.tipos)
    if fallas:
        raise S.Bloqueado(f"el índice tiene {len(fallas)} fallas: " + "; ".join(fallas[:20]))
    decisiones = paquete(ents, filas, texto, tipos)[2]
    res = {}
    for nombre, rol in inst.roles.items():
        partes = []
        if rol.decisiones:
            partes.append((f"{inst.decisiones} · {', '.join(tipos)}", decisiones))
        for a in rol.archivos:
            partes.append((a, (inst.raiz / a).read_text(encoding="utf-8")))
        for a, titulos in rol.secciones.items():
            fuente = (inst.raiz / a).read_text(encoding="utf-8")
            for t in titulos:
                try:
                    partes.append((f"{a} · {t}", seccion(fuente, t)))
                except S.Bloqueado as x:
                    raise S.Bloqueado(f"{a}: {x}") from None
        if not partes:
            raise S.Bloqueado(f"el rol {nombre} no recibe nada: declare decisiones, archivos o secciones")
        res[nombre] = "".join(f"## {n}\n\n{c}\n\n" for n, c in partes)
    return res
