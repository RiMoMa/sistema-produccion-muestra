"""Las dos primeras vienen de un proyecto anterior del autor, adaptadas: detectar en vez de reemplazar."""
import pytest

from motor import saneo as Z
from motor.state import Bloqueado


def test_correo_del_origen():
    assert Z.detectar("escribe a ana.p+1@mail.co hoy") == ["correo"]


def test_terminos_privados_del_origen():
    assert Z.detectar("cuenta CuentaX gmail", ["cuentax"]) == ["término privado"]


@pytest.mark.parametrize("texto, esperado", [
    ("Tel 300 123 4567", ["teléfono"]),
    ("+57 300 123 4567", ["teléfono"]),
    ("CC 1.234.567.890", ["documento"]),
    ("cédula: 12345678", ["documento"]),
    ("TI 1234567890", ["documento"]),
])
def test_datos_que_se_detectan(texto, esperado):
    assert Z.detectar(texto) == esperado


@pytest.mark.parametrize("texto", [
    "120 130 140 150",
    "10.1038/s41598-025-97652-6",
    "Table 2: 1200 1350 1475 1600",
    "ISBN 978-84-376-0494-7",
    "OR = 4.85 (3.06-7.70)",
    "texto limpio",
    "1.300 123 4567",
])
def test_cifras_e_identificadores_no_se_detectan(texto):
    assert Z.detectar(texto) == []


def test_exigir_limpio_detiene_y_no_repite_el_dato():
    with pytest.raises(Z.Bloqueado) as e:
        Z.exigir_limpio({"encargo": "ok", "brief.md": "de ana@mail.co"})
    assert "brief.md" in str(e.value) and "correo" in str(e.value) and "ana@" not in str(e.value)


def test_exigir_limpio_con_termino_privado():
    with pytest.raises(Bloqueado, match="término privado"):
        Z.exigir_limpio({"a": "Hospital Secreto"}, ["hospital secreto"])


def test_exigir_limpio_deja_pasar_lo_limpio():
    Z.exigir_limpio({"a": "texto limpio", "b": "120 130 140"}, ["otro"])


def test_privados_lee_el_archivo(tmp_path):
    assert Z.privados(tmp_path) == []
    (tmp_path / "privado.txt").write_text("Uno\n\n  dos  \n", encoding="utf-8")
    assert Z.privados(tmp_path) == ["Uno", "dos"]
