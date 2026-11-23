#!/usr/bin/env python3
"""Gráficas del deck de la clase 5. Fuente de imagenes/*.png: se regeneran desde aquí.
Usa la convención del curso: sinc(x) = sin(x)/x."""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

AQUI = os.path.dirname(os.path.abspath(__file__))
AZUL, AMBAR, GRIS = "#1F3A5F", "#B45309", "#6B7280"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 13, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.edgecolor": GRIS})


def sinc(x):
    return np.sinc(x / np.pi)  # numpy usa sin(pi x)/(pi x); se convierte a sin(x)/x


def guardar(fig, nombre):
    fig.savefig(os.path.join(AQUI, "imagenes", nombre), dpi=200, bbox_inches="tight", transparent=False, facecolor="white")
    plt.close(fig)


# 1 · pulso y su espectro, dos anchos
t = np.linspace(-3, 3, 2000)
w = np.linspace(-20, 20, 4000)
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 3.8))
for T, c, ls in ((2.0, AZUL, "-"), (0.8, AMBAR, "--")):
    a1.plot(t, (np.abs(t) <= T / 2).astype(float), color=c, ls=ls, lw=2.5, label=f"T = {T}")
    a2.plot(w, T * sinc(w * T / 2), color=c, ls=ls, lw=2.5, label=f"T = {T}")
a1.set_title("x(t) = rect(t/T)", color=AZUL); a1.set_xlabel("t (s)"); a1.legend(frameon=False)
a2.set_title("X(ω) = T sinc(ωT/2)", color=AZUL); a2.set_xlabel("ω (rad/s)"); a2.axhline(0, color=GRIS, lw=0.8)
a2.annotate("first zero at 2π/T", xy=(2 * np.pi / 2.0, 0), xytext=(6, 1.3), color=AZUL,
            arrowprops=dict(arrowstyle="->", color=AZUL))
guardar(fig, "rect-sinc.png")

# 2 · ejemplo RC: entrada, salida y producto equivocado
t = np.linspace(0, 5, 1000)
fig, ax = plt.subplots(figsize=(7.5, 4.2))
ax.plot(t, np.exp(-t), color=GRIS, lw=2, label=r"input $x(t) = e^{-t}u(t)$")
ax.plot(t, 2 * (np.exp(-t) - np.exp(-2 * t)), color=AZUL, lw=3, label=r"output $y(t) = 2(e^{-t} - e^{-2t})u(t)$")
ax.plot(t, 2 * np.exp(-3 * t), color=AMBAR, lw=2, ls="--", label=r"wrong: $x(t)\,h(t)$, jumps at $t = 0$")
ax.set_xlabel("t (s)"); ax.legend(frameon=False, fontsize=11); ax.set_ylim(0, 2.1)
guardar(fig, "rc-salida.png")

# 3 · escalon: el limite de e^{-et}u(t)
w = np.linspace(-3, 3, 3000)
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 3.8))
for e, c in ((0.5, GRIS), (0.15, AMBAR), (0.04, AZUL)):
    a1.plot(w, e / (e * e + w * w), color=c, lw=2, label=f"ε = {e}")
    a2.plot(w, -w / (e * e + w * w), color=c, lw=2)
a1.set_title("real part: area π for every ε → πδ(ω)", color=AZUL, fontsize=12); a1.set_ylim(0, 8); a1.legend(frameon=False)
a2.set_title("imaginary part → −1/ω, i.e. 1/(jω)", color=AZUL, fontsize=12); a2.set_ylim(-8, 8)
for a in (a1, a2):
    a.set_xlabel("ω (rad/s)")
guardar(fig, "escalon-limite.png")
print("OK")
