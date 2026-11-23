"""Prueba el motor de revisión con reglas de ejemplo. Las reglas reales viven en cada instancia."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from motor import nodos as N
from motor import revisar as V
from motor import runtime as R
from motor import state as S

REGLAS = """# comentario
falla | prohibida | zorro | nota de zorro |  |
aviso | dudosa | gato |  |  |
falla_sin | sin salida | condicion | falta salida |  | salida
aviso_sin | sin vecina | perro |  |  | vecina
aviso_cerca | cerca | tortuga |  |  | norma
aviso_cifras | cifras | [0-9]+ % |  |  | doi
falla | solo aqui | lobo |  | (especial) |
"""


@pytest.fixture
def reglas(tmp_path):
    f = tmp_path / "r.reglas"
    f.write_text(REGLAS, encoding="utf-8")
    return V.leer_reglas(str(f))


def etiquetas(reglas, texto, ruta="x.md"):
    return [h["etiqueta"] for h in V.revisar(texto.splitlines(), ruta, reglas)]


@pytest.mark.parametrize("texto, esperado", [
    ("un zorro", ["prohibida"]),
    ("un ZORRO", ["prohibida"]),
    ("un gato", ["dudosa"]),
    ("condicion", ["sin salida"]),
    ("condicion con salida", []),
    ("perro", ["sin vecina"]),
    ("perro\nvecina", []),
    ("vecina\nperro", []),
    ("tortuga", []),
    ("tortuga\nnorma", ["cerca"]),
    ("norma\ntortuga", ["cerca"]),
    ("40 %", ["cifras"]),
    ("40 %\ndoi lejos", []),
    ("texto limpio", []),
])
def test_tipos_de_regla(reglas, texto, esperado):
    assert etiquetas(reglas, texto) == esperado


def test_ambito_limita_por_ruta(reglas):
    assert etiquetas(reglas, "lobo", "normal.md") == []
    assert etiquetas(reglas, "lobo", "especial.md") == ["solo aqui"]


def test_hallazgo_trae_clase_nota_y_linea(reglas):
    h = V.revisar(["limpia", "un zorro"], "x.md", reglas)[0]
    assert h == {"clase": "falla", "etiqueta": "prohibida", "nota": "nota de zorro",
                 "lineas": [{"n": 2, "texto": "un zorro"}]}


@pytest.mark.parametrize("linea, error", [
    ("inventado | a | b | c |  | ", "tipo desconocido"),
    ("falla | a | ( | c |  | ", "inválida"),
    ("falla_sin | a | b | c |  | ", "necesita"),
])
def test_regla_mal_escrita_detiene(tmp_path, linea, error):
    f = tmp_path / "r.reglas"
    f.write_text(linea + "\n", encoding="utf-8")
    with pytest.raises(SystemExit, match=error):
        V.leer_reglas(str(f))


def test_html_revisa_solo_lo_visible(tmp_path):
    f = tmp_path / "a.html"
    f.write_text('<style>.zorro{}</style><p>hola&nbsp;gato</p><script>let x = "una frase con zorro";'
                 'let y = "zorro";</script>', encoding="utf-8")
    t = V.texto_visible(str(f))
    assert "gato" in t and "una frase con zorro" in t and ".zorro" not in t and 'let y' not in t
    assert t.count("zorro") == 1  # una cadena de una palabra es una clave, no texto


def cli(tmp_path, texto):
    (tmp_path / "r.reglas").write_text(REGLAS, encoding="utf-8")
    (tmp_path / "p.md").write_text(texto, encoding="utf-8")
    motor = Path(V.__file__)
    return subprocess.run([sys.executable, "-B", str(motor), "p.md", "--reglas", "r.reglas"], cwd=tmp_path,
                          capture_output=True, text=True)


def test_comando_sale_con_1_si_hay_falla(tmp_path):
    r = cli(tmp_path, "un zorro\n")
    assert r.returncode == 1 and "FALLA · prohibida" in r.stdout


def test_comando_sale_con_0_con_solo_avisos(tmp_path):
    r = cli(tmp_path, "un gato\n")
    assert r.returncode == 0 and "AVISO · dudosa" in r.stdout


# En el grafo

YO = "Persona Aprobadora"
LINEA = {"version": "1", "aprobadores": [YO], "etapas": {
    "producir": {},
    "mecanica": {"depende": ["producir"], "ciclo": {"vuelve_a": "producir", "max_rondas": 2}},
    "cierre": {"depende": ["producir", "mecanica"], "puerta": "P", "aprueba": ["producir"]},
}}


@pytest.fixture
def t(tmp_path):
    for a in (["init", "-q"], ["config", "user.name", "P"], ["config", "user.email", "p@ejemplo.invalid"]):
        subprocess.run(["git", *a], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "r.reglas").write_text(REGLAS, encoding="utf-8")
    S.nuevo(tmp_path, "t", LINEA)
    return tmp_path


def nodos(t, textos):
    vistos = []

    def producir(ctx):
        vistos.append(list(ctx.extras))
        return R.Resultado({"pieza.md": textos[min(len(vistos) - 1, len(textos) - 1)]})

    return {"producir": R.Nodo(producir, rol="p", origen="modelo"),
            "mecanica": N.revision_mecanica(t / "r.reglas"),
            "cierre": R.Nodo(lambda c: R.Resultado({"salida.html": "ok"}), rol="c")}, vistos


def test_pieza_limpia_pasa_sin_corregir(t):
    n, vistos = nodos(t, ["limpia"])
    assert R.correr(t, LINEA, n)["puerta"] == "P"
    assert len(vistos) == 1


def test_falla_devuelve_la_pieza_con_el_informe(t):
    n, vistos = nodos(t, ["un zorro", "limpia"])
    assert R.correr(t, LINEA, n)["puerta"] == "P"
    assert len(vistos) == 2 and vistos[1][0].endswith("producir/000001/pieza.md")  # su pieza anterior (bloque 3)
    assert vistos[1][1].endswith("informe.json")
    assert S.ultimo_manifiesto(t, "mecanica")["resultado"]["hallazgos"] == 0


def test_aviso_no_devuelve_la_pieza(t):
    n, vistos = nodos(t, ["un gato"])
    assert R.correr(t, LINEA, n)["puerta"] == "P"
    assert len(vistos) == 1
    informe = next(iter(S.ultimo_manifiesto(t, "mecanica")["salidas"]))
    assert "dudosa" in (t / informe).read_text(encoding="utf-8")


def test_falla_que_no_se_corrige_llega_a_la_puerta(t):
    n, vistos = nodos(t, ["un zorro"])
    assert R.correr(t, LINEA, n)["puerta"] == "P"
    assert len(vistos) == 2
    assert S.ultimo_manifiesto(t, "mecanica")["resultado"]["hallazgos"] == 1


def test_el_informe_es_json_con_la_ruta_de_la_pieza(t):
    n, _ = nodos(t, ["un zorro", "limpia"])
    R.correr(t, LINEA, n)
    primera = [f for f in (t / "artefactos/mecanica").rglob("informe.json")]
    datos = [json.loads(f.read_text(encoding="utf-8")) for f in sorted(primera)]
    assert list(datos[0].values())[0][0]["etiqueta"] == "prohibida"
    assert list(datos[-1].values())[0] == []


def test_cambiar_las_reglas_da_aviso_y_no_vence(t):
    n, _ = nodos(t, ["limpia"])
    R.correr(t, LINEA, n)
    assert S.ultimo_manifiesto(t, "mecanica")["reglas_sha256"] == S.sha256_archivo(t / "r.reglas")
    v = S.vigencia(t, LINEA, {"mecanica": {"reglas_sha256": "otras"}})
    assert v["mecanica"]["estado"] == "aviso"


def test_archivo_que_no_es_texto_no_se_revisa(t):
    def producir(ctx):
        return R.Resultado({"datos.json": "zorro"})
    n, _ = nodos(t, [""])
    n["producir"] = R.Nodo(producir, rol="p")
    R.correr(t, LINEA, n)
    assert S.ultimo_manifiesto(t, "mecanica")["resultado"]["hallazgos"] == 0
