#!/usr/bin/env python3
"""Revisión mecánica de un entregable, con las reglas de cada instancia.

Uso:
    revisar.py ruta/al/entregable [--reglas contexto/revisar.reglas]

Solo detecta lo que se puede detectar sin leer. El resto del control es de la
lectura (checklist y verificador). Las reglas no viven en este archivo: viven
en `contexto/revisar.reglas` de cada instancia, porque cambian con el dominio y
el motor no.

Formato de una regla, una por línea, campos separados por " | ":

    tipo | etiqueta | patrón | nota | ámbito | patrón2

- tipo:
    falla        la línea coincide con el patrón: falla.
    aviso        igual, pero solo avisa.
    falla_sin    la línea coincide con el patrón y no con patrón2: falla.
    aviso_sin    la línea coincide con el patrón y ni ella ni sus vecinas
                 coinciden con patrón2: aviso (para lo que exige leer).
    aviso_cerca  la línea coincide con el patrón y ella o una vecina coincide
                 con patrón2: aviso.
    aviso_cifras el documento tiene líneas con el patrón y ninguna con
                 patrón2 (por ejemplo, cifras sin ninguna cita): aviso.
- patrón y patrón2: expresiones regulares de Python, sin distinguir mayúsculas.
- ámbito: expresión regular sobre la ruta; vacío = todos los entregables.

Las líneas que empiezan con # y las vacías se ignoran. Un campo vacío se deja
entre separadores: "falla | x | y | z |  | ".

En un HTML se revisa solo el texto que ve el lector: el del cuerpo y el de las
cadenas del <script>. Las líneas reportadas son las del texto extraído.

Sale con 0 si no hay fallas y con 1 si las hay; los avisos no cambian la salida.

`revisar` devuelve los hallazgos como datos, para que los use un nodo del grafo. Procedencia en
PROCEDENCIA.md.
"""
import argparse
import html
import os
import re
import sys


def texto_visible(ruta):
    t = open(ruta, encoding="utf-8").read()
    if not ruta.lower().endswith((".html", ".htm")):
        return t
    cadenas = []
    for js in re.findall(r"(?is)<script[^>]*>(.*?)</script>", t):
        for c in re.findall(r"`([^`]*)`|\"((?:[^\"\\\n]|\\.)*)\"", js):
            c = c[0] or c[1]
            if len(c.split()) >= 3:  # texto, no claves ni identificadores
                cadenas.append(c.replace('\\"', '"').replace("\\n", "\n"))
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", t)
    t = t + "\n" + "\n".join(cadenas)
    t = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h[1-6]|pre|td|th)>", "\n", t)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    t = "\n".join(re.sub(r"[ \t]+", " ", l).strip() for l in t.splitlines())
    return re.sub(r"\n{3,}", "\n\n", t)


def leer_reglas(ruta):
    reglas = []
    for n, linea in enumerate(open(ruta, encoding="utf-8"), 1):
        linea = linea.rstrip()
        if not linea or linea.lstrip().startswith("#"):
            continue
        # Un espacio al final, por si el editor recortó el del último separador.
        campos = [c.strip() for c in (linea + " ").split(" | ")]
        campos += [""] * (6 - len(campos))
        tipo, etiqueta, patron, nota, ambito, patron2 = campos[:6]
        if tipo not in ("falla", "aviso", "falla_sin", "aviso_sin", "aviso_cerca", "aviso_cifras"):
            sys.exit(f"{ruta}:{n}: tipo desconocido «{tipo}»")
        try:
            r = re.compile(patron, re.I | re.M)
            r2 = re.compile(patron2, re.I | re.M) if patron2 else None
            ra = re.compile(ambito) if ambito else None
        except re.error as e:
            sys.exit(f"{ruta}:{n}: expresión inválida: {e}")
        if tipo in ("falla_sin", "aviso_sin", "aviso_cerca", "aviso_cifras") and r2 is None:
            sys.exit(f"{ruta}:{n}: el tipo {tipo} necesita patrón2")
        reglas.append((tipo, etiqueta, r, nota, ra, r2))
    return reglas


def revisar(lineas, ruta, reglas):
    """Devuelve un hallazgo por regla que saltó, en el orden de las reglas."""
    hallazgos = []
    for tipo, etiqueta, r, nota, ambito, r2 in reglas:
        if ambito and not ambito.search(ruta):
            continue
        hits = []
        if tipo in ("falla", "aviso"):
            hits = [(i, l) for i, l in enumerate(lineas) if r.search(l)]
        elif tipo == "falla_sin":
            hits = [(i, l) for i, l in enumerate(lineas) if r.search(l) and not r2.search(l)]
        elif tipo == "aviso_sin":
            for i, l in enumerate(lineas):
                if r.search(l):
                    vecinas = " ".join(lineas[max(i - 1, 0):i + 2])
                    if not r2.search(vecinas):
                        hits.append((i, l))
        elif tipo == "aviso_cerca":
            for i, l in enumerate(lineas):
                if r.search(l):
                    vecinas = " ".join(lineas[max(i - 1, 0):i + 2])
                    if r2.search(vecinas):
                        hits.append((i, l))
        elif tipo == "aviso_cifras":
            con = [(i, l) for i, l in enumerate(lineas) if r.search(l)]
            if con and not any(r2.search(l) for l in lineas):
                hits = con
        if hits:
            hallazgos.append({"clase": "falla" if tipo.startswith("falla") else "aviso", "etiqueta": etiqueta,
                              "nota": nota, "lineas": [{"n": i + 1, "texto": l} for i, l in hits]})
    return hallazgos


def main():
    ap = argparse.ArgumentParser(description="Revisión mecánica de un entregable.")
    ap.add_argument("archivo")
    ap.add_argument("--reglas", default="contexto/revisar.reglas")
    a = ap.parse_args()
    if not os.path.isfile(a.archivo):
        sys.exit(f"Uso: {sys.argv[0]} ruta/al/archivo [--reglas archivo]")
    if not os.path.isfile(a.reglas):
        sys.exit(f"No encuentro las reglas: {a.reglas}")

    print(f"Revisando: {a.archivo}")
    hallazgos = revisar(texto_visible(a.archivo).splitlines(), a.archivo, leer_reglas(a.reglas))
    for h in hallazgos:
        print(f"\n{h['clase'].upper()} · {h['etiqueta']}")
        if h["nota"]:
            print(f"   {h['nota']}")
        for linea in h["lineas"]:
            print(f"   {linea['n']}:{linea['texto']}")
    fallas = sum(1 for h in hallazgos if h["clase"] == "falla")
    print()
    if fallas == 0:
        print("Sin fallas mecánicas. Falta la revisión a mano.")
        return 0
    print(f"{fallas} tipo(s) de falla. Corregir antes de seguir.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
