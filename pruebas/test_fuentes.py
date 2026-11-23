"""Bloque 16: verificador de fuentes, filtro y anexo del registro, con un `claude` falso. Sin red y sin gastar."""
import json
import subprocess

import pytest

from motor import modelos as M
from motor import nodos as N
from motor import runtime as R
from motor import state as S
from pruebas.test_verificador import claude_guion  # noqa: F401  (fixture)

YO = "Persona Aprobadora"
HOY = "2026-11-07T10:00:00-05:00"
LINEA = {"version": "1", "aprobadores": [YO], "etapas": {
    "producir": {},
    "filtrar": {"depende": ["producir"]},
    "fuentes": {"depende": ["producir", "filtrar"], "ciclo": {"vuelve_a": "producir", "max_rondas": 2}},
    "cerrar": {"depende": ["producir", "fuentes"], "puerta": "P4", "aprueba": ["producir"]},
    "anexar": {"depende": ["cerrar", "fuentes"]},
}}
PIEZA = "Según Autora (doi:10.1000/ABC.1.), y la norma en https://norma.gov.co/ley-1 , pasa X."
FILA_VIEJA = "| Autora E, et al. 2024. doi:10.1000/abc.1 | dato | M3 | 16 oct 2026 |"
FILA_NUEVA = "| Norma 1. https://norma.gov.co/ley-1 | art. 2 | M4 | 7 nov 2026 |"
REGISTRO = f"# Registro\n\nPROSA: el caso de 10.1000/abc.1 enseñó algo.\n\n| Fuente | Qué | Dónde | Abierta el |\n|---|---|---|---|\n{FILA_VIEJA}\n| Otra. https://otra.org/x | y | M3 | 1 oct 2026 |\n"


def confirmada(**k):
    return {"cita": "Norma 1", "comprobado": "art. 2", "url": "https://norma.gov.co/ley-1", "abierta_el": "2026-11-07",
            "fila": FILA_NUEVA, **k}


def corregida(**k):
    return {"dice_la_pieza": "Autor B", "dice_la_fuente": "Autora", "cita_correcta": "Autora E, et al.",
            "url": "https://doi.org/10.1000/abc.1", **k}


def no_verificable(**k):
    return {"cita": "Nassiri & Akhloufi", "por_que": "no aparece", "recomendacion": "cortar", **k}


def informe(c=(), co=(), nv=()):
    return json.dumps({"confirmadas": list(c), "corregidas": list(co), "no_verificables": list(nv)})


LIMPIO = informe([confirmada(), confirmada(cita="Autora", url="https://doi.org/10.1000/abc.1", fila="")])
CON_ERROR = informe([confirmada()], [corregida()])


@pytest.fixture
def t(tmp_path):
    c = tmp_path / "trabajo"
    c.mkdir()
    for a in (["init", "-q"], ["config", "user.name", "Prueba"], ["config", "user.email", "p@ejemplo.invalid"]):
        subprocess.run(["git", *a], cwd=c, check=True)
    S.nuevo(c, "t", LINEA)
    (tmp_path / "registro.md").write_text(REGISTRO, encoding="utf-8")
    return c


class Producir:
    def __init__(self):
        self.n = 0

    def nodo(self):
        def f(ctx):
            self.n += 1
            return R.Resultado({"pieza.md": f"{PIEZA} Versión {self.n}."})
        return R.Nodo(f, rol="producir")


def nodos(t, p):
    reg = t.parent / "registro.md"
    return {"producir": p.nodo(), "filtrar": N.filtrar_registro(reg),
            "fuentes": N.verificador_fuentes([("claude", "sonnet")]),
            "cerrar": R.Nodo(lambda ctx: R.Resultado({"cierre.md": "ok"}), rol="cerrar"),
            "anexar": N.anexar_registro(reg)}


def registro(t):
    return (t.parent / "registro.md").read_text(encoding="utf-8")


# Forma del informe

def test_informe_valido():
    assert N.validar_fuentes(informe([confirmada()], [corregida()], [no_verificable()])) == []
    assert N.validar_fuentes(informe()) == []
    assert N.validar_fuentes("```json\n" + LIMPIO + "\n```") == []


@pytest.mark.parametrize("texto, error", [
    ("nada", "no es JSON"),
    (json.dumps({"confirmadas": [], "corregidas": []}), "tres listas"),
    (informe(["x"]), "no es un objeto"),
    (informe([confirmada(url="")]), "URL"),
    (informe([confirmada(url="no es url")]), "URL"),
    (informe([], [corregida(url="")]), "URL"),
    (informe([confirmada(abierta_el="")]), "fecha de apertura"),
    (informe([confirmada(abierta_el="7 nov 2026")]), "fecha de apertura"),
    (informe([confirmada(fila="sin barras")]), "fila de tabla"),
    (informe([], [corregida(cita_correcta=" ")]), "cita correcta"),
    (informe([], [], [no_verificable(por_que="")]), "sin por qué"),
    (informe([], [], [no_verificable(recomendacion="dejar")]), "recomendación"),
])
def test_informe_mal_formado(texto, error):
    assert any(error in e for e in N.validar_fuentes(texto))


def test_contar():
    assert N.contar_fuentes(LIMPIO) == (0, 0)
    assert N.contar_fuentes(informe([confirmada()], [corregida()], [no_verificable(), no_verificable()])) == (3, 0)


def test_referencias():
    assert N.referencias(PIEZA) == {"10.1000/abc.1", "https://norma.gov.co/ley-1"}


# Nodos

@pytest.mark.parametrize("via, modelo", [("deepseek", "deepseek-v4-pro"), ("ollama", "qwen")])
def test_solo_claude_navega(via, modelo):
    with pytest.raises(S.Bloqueado, match="web"):
        N.verificador_fuentes([("claude", "sonnet"), (via, modelo)])


def test_recibe_solo_la_web_la_pieza_y_las_filas_citadas(t, claude_guion):
    poner, pedidos = claude_guion
    poner(LIMPIO)
    R.correr(t, LINEA, nodos(t, Producir()))
    p = pedidos()[0]
    assert p["argv"][p["argv"].index("--tools") + 1] == "WebSearch,WebFetch"
    assert p["sistema"].startswith("Abres fuentes") and "name:" not in p["sistema"]
    assert "Versión 1" in p["texto"] and FILA_VIEJA in p["texto"]
    assert "otra.org" not in p["texto"] and "# Registro" not in p["texto"] and "PROSA" not in p["texto"]
    assert S.ultimo_manifiesto(t, "filtrar")["reglas_sha256"] == S.sha256_archivo(t.parent / "registro.md")


def test_sin_citas_el_filtro_no_trae_nada(t):
    ctx = R.Contexto(t, "filtrar", {"pieza.md": ""}, [])
    (t / "pieza.md").write_text("Sin fuentes.", encoding="utf-8")
    r = N.filtrar_registro(t.parent / "registro.md").funcion(ctx)
    assert r.archivos == {"registro-filtrado.md": "Sin filas del registro para esta pieza.\n"}


def test_limpio_llega_a_la_puerta_y_anexa_despues(t, claude_guion):
    poner, _ = claude_guion
    poner(LIMPIO)
    p = Producir()
    r = R.correr(t, LINEA, nodos(t, p))
    assert r["puerta"] == "P4" and p.n == 1
    assert FILA_NUEVA not in registro(t)
    assert R.correr(t, LINEA, nodos(t, p), R.decidir(t, LINEA, "P4", YO, HOY))["estado"] == "terminado"
    assert registro(t).count(FILA_NUEVA) == 1 and registro(t).count(FILA_VIEJA) == 1


def test_corregida_devuelve_la_pieza(t, claude_guion):
    poner, pedidos = claude_guion
    poner(CON_ERROR, LIMPIO)
    p = Producir()
    assert R.correr(t, LINEA, nodos(t, p))["puerta"] == "P4"
    assert p.n == 2 and "Versión 2" in pedidos()[1]["texto"]


def test_anexar_no_duplica(t):
    (t / "f").mkdir()
    (t / "f" / "fuentes.json").write_text(informe([confirmada(), confirmada(), confirmada(fila=FILA_VIEJA)]),
                                         encoding="utf-8")
    ctx = R.Contexto(t, "anexar", {"f/fuentes.json": ""}, [])
    r = N.anexar_registro(t.parent / "registro.md").funcion(ctx)
    assert registro(t).count(FILA_NUEVA) == 1 and registro(t).count(FILA_VIEJA) == 1
    assert r.archivos["anexadas.md"] == FILA_NUEVA + "\n"
    r = N.anexar_registro(t.parent / "registro.md").funcion(ctx)
    assert r.archivos["anexadas.md"] == "Ninguna fila nueva.\n" and registro(t).count(FILA_NUEVA) == 1


def test_anexar_sin_informe_falla(t):
    with pytest.raises(S.Bloqueado, match="informe de fuentes"):
        N.anexar_registro(t.parent / "registro.md").funcion(R.Contexto(t, "anexar", {"x.md": ""}, []))


def test_informe_ilegible_no_cuenta_como_limpio(t, claude_guion):
    poner, _ = claude_guion
    poner(informe([confirmada(abierta_el="")]))
    with pytest.raises(M.ErrorModelo, match="fecha de apertura"):
        R.correr(t, LINEA, nodos(t, Producir()))
    assert S.ultimo_manifiesto(t, "fuentes") is None
