"""Draws the creative panel used in the private system."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

OUT = Path(__file__).resolve().parents[1] / "img"
BG, CODE, MODEL, PERSON = "#0b1426", "#e1e0d9", "#2a78d6", "#eb6834"
f, ax = plt.subplots(figsize=(12, 4.9), facecolor=BG)
ax.set_position([0, 0, 1, 1]); ax.set_xlim(0, 12); ax.set_ylim(0, 4.9); ax.axis("off")


def box(x, y, title, sub, c, w=1.75):
    ax.add_patch(Rectangle((x - w / 2, y - .36), w, .72, fc=c, ec="none", zorder=3))
    k = "white" if c == MODEL else "#0b0b0b"
    ax.text(x, y + (.14 if sub else 0), title, ha="center", va="center", color=k, fontsize=12, fontweight="bold", zorder=4)
    ax.text(x, y - .16, sub, ha="center", va="center", color=k, fontsize=9.5, zorder=4)


def arrow(a, b):
    ax.annotate("", b, a, arrowprops=dict(arrowstyle="-|>", color="#d8d7cf", lw=1.6))


M = 2.35
box(1.15, M, "Short brief", "no house rules", CODE)
for i, v in enumerate(["Skepticism", "Experience", "Play", "Mobile"]):
    y = 3.85 - i
    box(3.65, y, v, "independent voice", MODEL)
    arrow((2.05, M), (2.75, y)); arrow((4.55, y), (5.25, M))
box(6.15, M, "Idea sheet", "matches are noted", CODE)
box(8.5, M, "Person", "accepts or rejects", PERSON)
box(10.85, M, "Writer", "approved ideas", MODEL)
arrow((7.05, M), (7.6, M)); arrow((9.4, M), (9.95, M))
ax.text(.28, 4.6, "Creative panel: independent voices, human selection", color="white", fontsize=14, fontweight="bold", va="center")
ax.text(.28, .22, "Used in the private system. Not part of this engine yet.", color="#d8d7cf", fontsize=10)
f.savefig(OUT / "panel.png", dpi=150, facecolor=BG)
