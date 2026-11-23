"""Draws the pipeline figure of the README, over a ComfyUI background."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

OUT = Path(__file__).resolve().parents[1] / "img"
T = {"": dict(bg="#0b1426", ink="#ffffff", mut="#ffffff", line="#ffffff", code="#e1e0d9", model="#2a78d6", person="#eb6834")}
W, H = 2.15, 1.0
BOX = [("Brief", "approved by a person", "person", 0, 1), ("Context packs", "code, one per role", "code", 1, 1),
       ("Writer", "DeepSeek, no tools", "model", 2, 1), ("Mechanical review", "code, no tokens", "code", 3, 1),
       ("Source checker", "Claude, web only", "model", 3, 0), ("Cold reviewer", "Claude, no tools", "model", 2, 0),
       ("Human gate", "approve or return", "person", 1, 0), ("Delivery", "hash-tied record", "code", 0, 0)]
for mode, t in T.items():
    f, ax = plt.subplots(figsize=(11, 4.6), facecolor=t["bg"])
    ax.set_position([0, 0, 1, 1]); ax.set_xlim(-.3, 10.9); ax.set_ylim(-.75, 4.4); ax.axis("off")
    ax.imshow(plt.imread(Path(__file__).parent / "pipeline-bg.jpg"), extent=(-.3, 10.9, -.75, 4.4), aspect="auto", zorder=0)
    pos = []
    for name, sub, kind, c, r in BOX:
        x, y = c * 2.8, .5 + r * 1.9
        pos.append((x, y))
        ax.add_patch(Rectangle((x, y), W, H, fc=t[kind], ec="none"))
        col = "#ffffff" if kind == "model" else "#0b0b0b"
        ax.text(x + W / 2, y + .62, name, ha="center", va="center", color=col, fontsize=12.5, fontweight="bold")
        ax.text(x + W / 2, y + .3, sub, ha="center", va="center", color=col, fontsize=10)
    arr = lambda a, b, **k: ax.annotate("", b, a, arrowprops=dict(arrowstyle="-|>", color=t["line"], lw=1.8, **k))
    for i in (0, 1, 2):
        arr((pos[i][0] + W, pos[i][1] + H / 2), (pos[i + 1][0], pos[i + 1][1] + H / 2))
    arr((pos[3][0] + W / 2, pos[3][1]), (pos[4][0] + W / 2, pos[4][1] + H))
    for i in (4, 5, 6):
        arr((pos[i][0], pos[i][1] + H / 2), (pos[i + 1][0] + W, pos[i + 1][1] + H / 2))
    arr((pos[5][0] + W / 2, pos[5][1] + H), (pos[2][0] + W / 2, pos[2][1]), ls="--")
    ax.text(pos[2][0] + W / 2 - .12, 1.95, "findings: correction rounds", ha="right", va="center", color=t["mut"], bbox=dict(fc="#0b1426", ec="none", pad=3), fontsize=10)
    for i, (k, l) in enumerate([("model", "Model"), ("code", "Code"), ("person", "Person")]):
        ax.add_patch(Rectangle((i * 1.5, 3.9), .28, .28, fc=t[k], ec="none"))
        ax.text(i * 1.5 + .4, 4.04, l, color=t["ink"], va="center", fontsize=11, bbox=dict(fc="#0b1426", ec="none", pad=3))
    ax.text(0, -.25, "The mechanical review and the source checker can also return the piece to the writer. Code decides every route.",
            color=t["mut"], bbox=dict(fc="#0b1426", ec="none", pad=3), fontsize=10.5, va="center")
    f.savefig(OUT / "pipeline.png", facecolor=t["bg"], dpi=160); plt.close(f)
