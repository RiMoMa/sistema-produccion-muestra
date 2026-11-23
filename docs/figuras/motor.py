"""Draws the engine modules and the real LangGraph flow.

1. With the engine environment: python docs/figuras/motor.py edges   (exports the compiled graph)
2. With matplotlib:             python docs/figuras/motor.py draw
"""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "img"
DATA = Path(__file__).parent / "flow-edges.json"
BG, CODE, MODEL, PERSON, STORE = "#0b1426", "#e1e0d9", "#2a78d6", "#eb6834", "#4b4b47"

# The line that ran on 23 November 2026.
LINE = {"version": "1", "aprobadores": ["approver"], "etapas": {
    "brief": {"puerta": "P1"}, "contexto": {},
    "producir": {"depende": ["brief", "contexto"], "puerta": "PM", "condicional": True},
    "mecanica": {"depende": ["producir"]},
    "verificar": {"depende": ["producir", "mecanica", "contexto"], "puerta": "PJ", "condicional": True,
                  "ciclo": {"vuelve_a": "producir", "max_rondas": 2}},
    "entregar": {"depende": ["producir", "verificar"], "puerta": "P4"}}}


def edges():
    sys.path.insert(0, str(ROOT))
    from motor import runtime as R
    nodes = {e: R.Nodo(lambda c: R.Resultado({}), rol=e) for e in LINE["etapas"]}
    g = R.construir(ROOT, LINE, nodes).compile().get_graph()
    DATA.write_text(json.dumps([[e.source, e.target, bool(e.conditional)] for e in g.edges], indent=1) + "\n")


def draw():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    def canvas(w, h):
        f, ax = plt.subplots(figsize=(w, h), facecolor=BG)
        ax.set_position([0, 0, 1, 1]); ax.set_xlim(0, w); ax.set_ylim(0, h); ax.axis("off")
        return f, ax

    def box(ax, x, y, w, h, title, sub, c):
        ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, fc=c, ec="none", zorder=3))
        k = "white" if c in (MODEL, STORE) else "#0b0b0b"
        ax.text(x, y + (.15 if sub else 0), title, ha="center", va="center", color=k, fontsize=12, fontweight="bold", zorder=4)
        ax.text(x, y - .17, sub, ha="center", va="center", color=k, fontsize=9.5, zorder=4)

    def arrow(ax, a, b, rad=0, dash=False):
        ax.annotate("", b, a, zorder=2, arrowprops=dict(arrowstyle="-|>", color="#d8d7cf", lw=1.5, ls="--" if dash else "-",
                    connectionstyle=f"arc3,rad={rad}"))

    # Flow: positions are by hand, edges come from the compiled graph.
    f, ax = canvas(12, 5.6)
    w, h = 1.75, .8
    P = {"brief": (1.3, 4.1), "P1": (3.65, 4.1), "contexto": (6.0, 4.1), "producir": (8.35, 4.1), "PM": (10.7, 4.1),
         "mecanica": (10.7, 1.7), "verificar": (8.35, 1.7), "PJ": (6.0, 1.7), "entregar": (3.65, 1.7), "P4": (1.3, 1.7)}
    T = {"brief": ("Brief", "input", CODE), "P1": ("Gate P1", "approve brief", PERSON), "contexto": ("Context packs", "one per role", CODE),
         "producir": ("Writer", "DeepSeek", MODEL), "PM": ("Gate PM", "if data is missing", PERSON),
         "mecanica": ("Mechanical", "pattern rules", CODE), "verificar": ("Cold reviewer", "Claude", MODEL),
         "PJ": ("Gate PJ", "if judgement needed", PERSON), "entregar": ("Delivery", "output file", CODE), "P4": ("Gate P4", "final approval", PERSON)}
    for n, (x, y) in P.items():
        box(ax, x, y, w, h, *T[n])
    for a, b, cond in json.loads(DATA.read_text()):
        if a not in P or b not in P:
            continue
        (x1, y1), (x2, y2) = P[a], P[b]
        if y1 == y2:
            forward = (x2 > x1) == (y1 > 3)
            s = 1 if x2 > x1 else -1
            if forward:
                arrow(ax, (x1 + s * w / 2, y1), (x2 - s * w / 2, y2), 0, cond)
            else:
                up = 1 if y1 > 3 else -1
                arrow(ax, (x1, y1 + up * h / 2), (x2, y2 + up * h / 2), .35, cond)
        elif x1 == x2:
            arrow(ax, (x1, y1 - h / 2), (x2, y2 + h / 2), 0, cond)
        else:
            arrow(ax, (x1 + .3, y1 + h / 2), (x2 - .3, y2 - h / 2), 0, cond)
    ax.text(.45, 5.25, "Real flow: edges exported from the compiled LangGraph line", color="white", fontsize=14, fontweight="bold", va="center")
    ax.text(.45, .3, "Solid: always.  Dashed: depends on a gate or a review result.  Start and end are omitted.", color="#d8d7cf", fontsize=10)
    f.savefig(OUT / "flow.png", dpi=150, facecolor=BG); plt.close(f)

    f, ax = canvas(12, 6.6)
    w = 2.35
    N = {"inst": (2.1, 5.3, "Project", "rules and line", PERSON), "person": (9.9, 5.3, "Person", "signs the gates", PERSON),
         "runtime": (6, 5.3, "runtime.py", "LangGraph: stages, loops", CODE),
         "nodos": (4.0, 3.9, "nodos.py", "roles, validation", CODE), "state": (8.6, 3.9, "state.py", "hashes, approvals", CODE),
         "contexto": (1.5, 2.55, "contexto.py", "one pack per role", CODE), "revisar": (4.0, 2.55, "revisar.py", "pattern rules", CODE),
         "modelos": (6.5, 2.55, "modelos.py", "one interface", CODE), "files": (9.1, 2.55, "Project files", "records, outputs", STORE),
         "saneo": (9.1, 1.2, "saneo.py", "private-data filter", CODE), "medir": (11.0, 3.9, "medir.py", "cost, rounds", CODE)}
    for k, (x, y, t, s, c) in N.items():
        box(ax, x, y, 1.7 if k == "medir" else w, .8, t, s, c)
    for i, (t, s) in enumerate([("DeepSeek", "writes"), ("Claude", "reviews"), ("opencode", "free"), ("Ollama", "local")]):
        x = 1.2 + i * 1.75
        box(ax, x, 1.05, 1.5, .8, t, s, MODEL)
        arrow(ax, (6.2, 2.15), (x, 1.45))
    def link(a, b):
        (x1, y1), (x2, y2) = N[a][:2], N[b][:2]
        if y1 == y2:
            s = 1 if x2 > x1 else -1
            arrow(ax, (x1 + s * w / 2, y1), (x2 - s * w / 2, y2))
        else:
            arrow(ax, (x1, y1 - .4), (x2, y2 + .4))
    for a, b in [("inst", "runtime"), ("person", "runtime"), ("runtime", "nodos"), ("runtime", "state"), ("nodos", "contexto"),
                 ("nodos", "revisar"), ("nodos", "modelos"), ("state", "files"), ("medir", "files")]:
        link(a, b)
    arrow(ax, (7.0, 2.15), (7.9, 1.35))
    ax.text(.45, 6.25, "The engine: modules and data", color="white", fontsize=14, fontweight="bold", va="center")
    ax.text(.45, .25, "modelos.py checks text with saneo.py before any non-local call. LangGraph also keeps a disposable SQLite checkpoint.",
            color="#d8d7cf", fontsize=10)
    f.savefig(OUT / "engine.png", dpi=150, facecolor=BG); plt.close(f)


{"edges": edges, "draw": draw}[sys.argv[1]]()
