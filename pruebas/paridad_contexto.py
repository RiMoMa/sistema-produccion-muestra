"""Compara el paquete de motor/contexto.py con el del script original, tipo por tipo. Solo lee.

Uso:
    python paridad_contexto.py <indice-decisiones.py original> <raíz de la instancia> [TIPO,TIPO ...]

Sin combinaciones, compara cada tipo de la instancia por separado. El original arma desde
`contexto/decisiones.md` de la raíz; el motor, desde lo que diga `instancia.toml`.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from motor import contexto as X  # noqa: E402

original, raiz = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
inst = X.leer_instancia(raiz)
combos = [c.split(",") for c in sys.argv[3:]] or [[t] for t in sorted(inst.tipos - X.MECANICOS)]
texto = (raiz / inst.decisiones).read_text(encoding="utf-8")
fallas, ents, filas = X.comprobar(texto, (raiz / inst.indice).read_text(encoding="utf-8"), inst.tipos)
if fallas:
    sys.exit("el índice tiene fallas: " + "; ".join(fallas))
distintos = []
with tempfile.TemporaryDirectory() as d:
    for tipos in combos:
        salida = Path(d) / "paquete.md"
        r = subprocess.run([sys.executable, "-B", str(original), "paquete", *tipos, "--raiz", str(raiz),
                            "--indice", inst.indice, "--salida", str(salida)], capture_output=True, text=True)
        if r.returncode:
            distintos.append(f"{'+'.join(tipos)}: el original falló: {r.stderr.strip()}")
            continue
        a = salida.read_bytes()
        b = X.paquete(ents, filas, texto, tipos)[2].encode()
        print(f"{'+'.join(tipos):28} {len(a):7} bytes  {'igual' if a == b else 'DISTINTO'}")
        if a != b:
            distintos.append("+".join(tipos))
print(f"{len(combos)} paquetes, {len(distintos)} distintos")
print(*distintos, sep="\n")
sys.exit(1 if distintos else 0)
