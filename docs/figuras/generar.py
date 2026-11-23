#!/usr/bin/env python3
"""Genera las figuras del README, en versión clara y oscura, como SVG.

Cada cifra viene de un archivo del repositorio, anotado junto al dato. No se calcula nada: lo que no está aquí no se dibuja.

    python3 docs/figuras/generar.py        # escribe docs/img/*.svg

Requiere matplotlib. Paleta validada con scripts/validate_palette.js del skill dataviz (CVD y contraste en claro y
oscuro): azul y naranja de la paleta categórica, y un gris para lo que no es el foco.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

SALIDA = Path(__file__).resolve().parents[1] / "img"
plt.rcParams.update({"svg.fonttype": "path", "font.family": "DejaVu Sans", "axes.unicode_minus": False})

TEMAS = {
    "light": dict(surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", muted="#8a8984", grid="#e6e5e0",
                  azul="#2a78d6", naranja="#eb6834", gris="#b4b3ac"),
    "dark": dict(surface="#1a1a19", ink="#f0efec", ink2="#c3c2b7", muted="#8f8e86", grid="#2c2c2a",
                 azul="#3987e5", naranja="#d95926", gris="#5f5e58"),
}

# --- Datos. Cada uno con su fuente ----------------------------------------------------------------------------
# development notes, "Prueba con cupo (7 de noviembre)": gasto de la corrida real de punta a punta.
COSTO_ESCRITOR_USD = 0.15       # DeepSeek, dos versiones de la pieza (gasto real)
COSTO_REVISION_USD = 0.73       # Claude Sonnet, dos verificaciones de fuentes y dos verificaciones (equivalente en API)
# development notes, tabla de rondas: hallazgos por ronda del ciclo de corrección.
RONDAS = [("Round 1", 8, 1), ("Round 2", 2, 1)]    # (ronda, M o R que vuelven al escritor, J que van a una persona)
# `wc -l motor/*.py` y `wc -l pruebas/*.py pruebas/mutantes/*.py` del 23 de noviembre de 2026.
MODULOS = [("state.py", 455), ("nodos.py", 325), ("modelos.py", 262), ("runtime.py", 242), ("contexto.py", 238),
           ("revisar.py", 150), ("medir.py", 102), ("saneo.py", 41)]
LINEAS_PRUEBAS = 2641
# KPI: pytest -q (303 en 7 s), development notes (194 de 194), development notes
# (6 de 6 sembrados), git log (47 commits), motor/modelos.py (VIAS: cuatro).
KPIS = [("303", "tests pass", "in 7 s, no network"), ("194 / 194", "mutants detected", "controls broken on purpose"),
        ("6 / 6", "errors caught", "seeded; none invented"), ("4", "model routes", "one function each")]


def preparar(t, ancho, alto):
    fig = plt.figure(figsize=(ancho, alto), dpi=100)
    fig.patch.set_facecolor(t["surface"])
    return fig


def barra_h(ax, y, largo, alto, color, r=0.0):
    """Barra horizontal anclada a la base. Recta: el redondeo de matplotlib va en unidades de datos y deforma."""
    ax.add_patch(Rectangle((0, y - alto / 2), largo, alto, fc=color, ec="none"))


def titulo(fig, t, texto, sub):
    fig.text(0.03, 0.93, texto, color=t["ink"], fontsize=14.5, fontweight="bold", va="top")
    fig.text(0.03, 0.855, sub, color=t["ink2"], fontsize=10.5, va="top")


def estilo_ejes(ax, t):
    ax.set_facecolor(t["surface"])
    for lado in ("top", "right", "left", "bottom"):
        ax.spines[lado].set_visible(False)
    ax.tick_params(length=0, colors=t["ink2"], labelsize=10)


def fig_costo(t, nombre):
    fig = preparar(t, 8.8, 3.1)
    titulo(fig, t, "Reviewing cost more than writing", "One real run, end to end: brief, draft, mechanical check, "
           "source check, cold review. Two versions of the piece.")
    ax = fig.add_axes([0.25, 0.10, 0.60, 0.58])
    estilo_ejes(ax, t)
    filas = [("Reviewers · Claude Sonnet", COSTO_REVISION_USD, t["azul"], "API-equivalent USD"),
             ("Writer · DeepSeek", COSTO_ESCRITOR_USD, t["gris"], "billed USD")]
    for i, (nom, v, c, nota) in enumerate(filas):
        y = 1 - i
        barra_h(ax, y, v, 0.5, c, r=0.012)
        ax.text(v + 0.015, y, f"${v:.2f}", color=t["ink"], fontsize=13, fontweight="bold", va="center")
        ax.text(v + 0.015, y - 0.27, nota, color=t["ink2"], fontsize=9, va="center")
    ax.set_yticks([1, 0], [f[0] for f in filas])
    ax.set_xlim(0, 0.95)
    ax.set_ylim(-0.5, 1.5)
    ax.set_xticks([])
    fig.text(0.03, 0.03, "Source: development notes", color=t["muted"], fontsize=8.5)
    fig.savefig(SALIDA / f"{nombre}-{t['modo']}.svg", facecolor=t["surface"])
    plt.close(fig)


def fig_ronda(t, nombre):
    fig = preparar(t, 8.8, 3.5)
    titulo(fig, t, "One correction round cut the returnable findings from 8 to 2",
           "Findings per round of the verify and correct loop. Judgement calls stay with a person.")
    ax = fig.add_axes([0.07, 0.17, 0.50, 0.58])
    estilo_ejes(ax, t)
    ancho = 0.5
    for i, (nom, mr, j) in enumerate(RONDAS):
        ax.add_patch(Rectangle((i - ancho / 2, 0), ancho, mr, fc=t["azul"], ec="none"))
        ax.add_patch(Rectangle((i - ancho / 2, mr + 0.12), ancho, j, fc=t["naranja"], ec="none"))
        ax.text(i, mr / 2, str(mr), color="white", fontsize=13, fontweight="bold", ha="center", va="center")
        ax.text(i, mr + 0.12 + j / 2, str(j), color="white", fontsize=12, fontweight="bold", ha="center", va="center")
    ax.set_xticks(range(len(RONDAS)), [r[0] for r in RONDAS])
    ax.set_yticks([])
    ax.set_xlim(-0.6, len(RONDAS) - 0.4)
    ax.set_ylim(0, 10.2)
    ax.tick_params(axis="x", labelsize=11, colors=t["ink"])
    # Leyenda con marcador, a la derecha del gráfico.
    for k, (c, txt, sub) in enumerate([(t["naranja"], "Needs a person (J)", "goes to a gate; the loop does not fix it"),
                                       (t["azul"], "Returns to the writer (M or R)", "mechanical or rule-based fix")]):
        yy = 0.66 - k * 0.22
        fig.patches.append(Rectangle((0.62, yy - 0.035), 0.022, 0.07, transform=fig.transFigure, fc=c, ec="none"))
        fig.text(0.655, yy + 0.012, txt, color=t["ink"], fontsize=10.5, va="center")
        fig.text(0.655, yy - 0.04, sub, color=t["ink2"], fontsize=9, va="center")
    fig.text(0.03, 0.03, "Source: development notes. No finding repeated between rounds.",
             color=t["muted"], fontsize=8.5)
    fig.savefig(SALIDA / f"{nombre}-{t['modo']}.svg", facecolor=t["surface"])
    plt.close(fig)


def fig_codigo(t, nombre):
    fig = preparar(t, 8.8, 4.4)
    titulo(fig, t, "More test code than engine code",
           "1,815 lines in 8 engine modules; 2,641 lines across the test files, the parity checks and the mutant generator.")
    ax = fig.add_axes([0.20, 0.10, 0.66, 0.66])
    estilo_ejes(ax, t)
    filas = [("tests", LINEAS_PRUEBAS, t["naranja"])] + [(n, v, t["azul"]) for n, v in MODULOS]
    for i, (nom, v, c) in enumerate(filas):
        y = len(filas) - 1 - i
        barra_h(ax, y, v, 0.58, c, r=18)
        ax.text(v + 30, y, f"{v:,}", color=t["ink"], fontsize=10.5, fontweight="bold", va="center")
    ax.set_yticks(range(len(filas) - 1, -1, -1), [f[0] for f in filas])
    ax.set_xlim(0, 3000)
    ax.set_xticks([])
    for lab in ax.get_yticklabels():
        lab.set_family("DejaVu Sans Mono" if lab.get_text().endswith(".py") else "DejaVu Sans")
    fig.text(0.03, 0.03, "Source: wc -l motor/*.py and pruebas/ on 2026-11-23", color=t["muted"], fontsize=8.5)
    fig.savefig(SALIDA / f"{nombre}-{t['modo']}.svg", facecolor=t["surface"])
    plt.close(fig)


def fig_kpis(t, nombre):
    fig = preparar(t, 8.8, 1.9)
    n = len(KPIS)
    for i, (num, etiqueta, nota) in enumerate(KPIS):
        x0 = 0.02 + i * (0.96 / n)
        fig.patches.append(FancyBboxPatch((x0, 0.10), 0.96 / n - 0.015, 0.80, transform=fig.transFigure,
                                          boxstyle="round,pad=0,rounding_size=0.02", fc=t["grid"], ec="none"))
        fig.text(x0 + 0.015, 0.68, num, color=t["azul"] if i % 2 == 0 else t["ink"], fontsize=23, fontweight="bold", va="center")
        fig.text(x0 + 0.015, 0.40, etiqueta, color=t["ink"], fontsize=11, fontweight="bold", va="center")
        fig.text(x0 + 0.015, 0.24, nota, color=t["ink2"], fontsize=8.5, va="center")
    fig.savefig(SALIDA / f"{nombre}-{t['modo']}.svg", facecolor=t["surface"])
    plt.close(fig)


def main() -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    for modo, t in TEMAS.items():
        t = {**t, "modo": modo}
        fig_kpis(t, "kpis")
        fig_costo(t, "cost")
        fig_ronda(t, "loop")
        fig_codigo(t, "code")
    print("figuras en", SALIDA)


if __name__ == "__main__":
    main()
