"""Compara motor/revisar.py con el original sobre un corpus. Solo lee.

Uso, desde la raíz del repositorio de origen:
    python paridad_revisar.py <revisar.py original> <reglas> <carpeta> [<reglas> <carpeta> ...]
"""
import os
import subprocess
import sys
from pathlib import Path

MOTOR = Path(__file__).resolve().parents[1] / "motor" / "revisar.py"


def correr(script, archivo, reglas):
    r = subprocess.run([sys.executable, "-B", str(script), archivo, "--reglas", reglas], capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr.replace(str(script), "revisar.py")


original, resto = sys.argv[1], sys.argv[2:]
comparados, distintos, con_falla = 0, [], 0
for reglas, carpeta in zip(resto[::2], resto[1::2]):
    for d, _, fs in os.walk(carpeta):
        for f in sorted(fs):
            if f.endswith((".md", ".html")) and "node_modules" not in d:
                ruta = os.path.join(d, f)
                a, b = correr(original, ruta, reglas), correr(MOTOR, ruta, reglas)
                comparados += 1
                con_falla += a[0] == 1
                if a != b:
                    distintos.append(ruta)
print(f"{comparados} comparaciones, {con_falla} con falla, {len(distintos)} distintas")
print(*distintos[:10], sep="\n")
sys.exit(1 if distintos else 0)
