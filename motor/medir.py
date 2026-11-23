"""Lo que gastó cada trabajo, desde sus archivos. No corre nada y no usa red.

Lo hecho sale de los manifiestos, que están sellados; las caídas, de `llamadas.jsonl`, porque no dejan manifiesto.
Una etapa vigente que se saltó no tiene manifiesto nuevo, así que no suma dos veces. Una edición humana no gasta.
El costo estimado de `claude -p` con suscripción va en "equivalente API" y no suma al costo real (D92).

Uso: python -m motor.medir TRABAJO [TRABAJO...] [--por etapa|rol|modelo|via] [--json]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from motor import state as S

DIMENSIONES = ("etapa", "rol", "modelo", "via")
CAMPOS = ("corridas", "caidas", "entrada", "cache_leido", "salida", "costo_usd", "equivalente_api")


def _modelo(ejecutor: dict) -> str:
    return ejecutor.get("modelo") or ("script" if "script" in ejecutor else "sin declarar")


def _via(ejecutor: dict, resultado: dict | None = None) -> str:
    if resultado and resultado.get("via"):
        return resultado["via"]
    rutas = ejecutor.get("rutas") or []
    return rutas[0][0] if rutas else ("script" if "script" in ejecutor else "sin declarar")


def _clave(por: str, etapa: str, rol: str, ejecutor: dict, resultado: dict | None) -> str:
    return {"etapa": etapa, "rol": rol, "modelo": _modelo(ejecutor), "via": _via(ejecutor, resultado)}[por]


def medir(carpetas: list[Path], por: str = "etapa") -> dict:
    """{"grupos": {clave: campos}, "total": campos, "trabajos": {id: {"cadena_rota": bool, ...}}}."""
    if por not in DIMENSIONES:
        raise S.Bloqueado(f"dimensión desconocida: {por}")
    grupos: dict[str, dict] = defaultdict(lambda: dict.fromkeys(CAMPOS, 0))
    trabajos = {}
    for carpeta in carpetas:
        manifiestos = S._cargar(carpeta, "corridas")
        rota = S._rotura(manifiestos) is not None
        n = 0
        for m in manifiestos:
            if m.get("corrupto") or m.get("origen") == "humano":
                continue
            n += 1
            g = grupos[_clave(por, m["etapa"], m.get("rol", "?"), m.get("ejecutor", {}), m.get("resultado"))]
            t = m.get("tokens") or {}
            g["corridas"] += 1
            for campo in ("entrada", "cache_leido", "salida"):
                g[campo] += t.get(campo) or 0
            g["costo_usd"] += m.get("costo_usd") or 0.0
            g["equivalente_api"] += t.get("costo_estimado") or 0.0
        caidas = 0
        llamadas = carpeta / "llamadas.jsonl"
        if llamadas.exists():
            for linea in llamadas.read_text(encoding="utf-8").splitlines():
                try:
                    r = json.loads(linea)
                except ValueError:
                    continue
                if str(r.get("estado", "")).startswith("error"):
                    caidas += 1
                    grupos[_clave(por, r.get("etapa", "?"), r.get("rol", "?"), r.get("ejecutor", {}), None)]["caidas"] += 1
        trabajos[S.leer(carpeta)["id"]] = {"cadena_rota": rota, "corridas": n, "caidas": caidas}
    total = dict.fromkeys(CAMPOS, 0)
    for g in grupos.values():
        for campo in CAMPOS:
            total[campo] += g[campo]
    return {"por": por, "grupos": dict(sorted(grupos.items())), "total": total, "trabajos": trabajos}


def tabla(datos: dict) -> str:
    filas = [f"{datos['por']:24s}{'Corridas':>9s}{'Caídas':>7s}{'Entrada':>10s}{'Caché':>10s}{'Salida':>9s}"
             f"{'Costo USD':>11s}{'Equiv. API':>11s}"]
    for k, g in [*datos["grupos"].items(), ("TOTAL", datos["total"])]:
        filas.append(f"{k[:23]:24s}{g['corridas']:9d}{g['caidas']:7d}{g['entrada']:10d}{g['cache_leido']:10d}"
                     f"{g['salida']:9d}{g['costo_usd']:11.4f}{g['equivalente_api']:11.4f}")
    for id_, t in datos["trabajos"].items():
        if t["cadena_rota"]:
            filas.append(f"AVISO: la cadena de manifiestos de {id_} está rota; sus cifras pueden no ser confiables")
    return "\n".join(filas)


def main(argv: list[str] | None = None) -> int:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("trabajos", nargs="+", type=Path)
    a.add_argument("--por", choices=DIMENSIONES, default="etapa")
    a.add_argument("--json", action="store_true")
    x = a.parse_args(argv)
    datos = medir(x.trabajos, x.por)
    print(json.dumps(datos, ensure_ascii=False, indent=2) if x.json else tabla(datos))
    return 0


if __name__ == "__main__":
    sys.exit(main())
