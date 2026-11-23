"""Freno de último recurso antes de enviar texto a un proveedor externo. No anonimiza.

La protección principal es la lista de lo que cada paso puede leer. Esto solo atrapa accidentes,
como un correo real pegado en un caso. Detecta y detiene; nunca reescribe el texto, y el error no
repite el dato. Procedencia en PROCEDENCIA.md.
"""
from __future__ import annotations

import re
from pathlib import Path

from motor.state import Bloqueado

PATRONES = [
    ("correo", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("documento", re.compile(r"\b(?:C\.?\s?C\.?|c[eé]dula|T\.?\s?I\.?|documento)\D{0,15}\d[\d.\s]{5,12}\d\b", re.I)),
    ("teléfono", re.compile(r"(?<![\d.])(?:\+?57[\s-]?)?3\d{2}[\s-]?\d{3}[\s-]?\d{4}(?!\d)")),
]


def privados(carpeta: Path) -> list[str]:
    """Términos del trabajo que nunca salen de la máquina (privado.txt)."""
    f = carpeta / "privado.txt"
    return [x.strip() for x in f.read_text(encoding="utf-8").splitlines() if x.strip()] if f.exists() else []


def detectar(texto: str, terminos: list[str] | None = None) -> list[str]:
    """Nombres de lo encontrado, sin el dato."""
    hallados = [nombre for nombre, patron in PATRONES if patron.search(texto)]
    minusculas = texto.lower()
    if any(t.lower() in minusculas for t in terminos or []):
        hallados.append("término privado")
    return hallados


def exigir_limpio(textos: dict[str, str], terminos: list[str] | None = None) -> None:
    """`textos` va de origen a texto. Lanza Bloqueado si algo no debe salir."""
    for origen, texto in textos.items():
        hallados = detectar(texto, terminos)
        if hallados:
            raise Bloqueado(f"posible dato personal en {origen} ({', '.join(hallados)}): no sale a un proveedor externo")
