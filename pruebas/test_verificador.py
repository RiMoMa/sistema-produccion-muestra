"""Bloque 15: el verificador en frío, con un `claude` falso. Sin red y sin gastar."""
import json
import stat
import subprocess

import pytest

from motor import modelos as M
from motor import nodos as N
from motor import runtime as R
from motor import state as S

YO = "Persona Aprobadora"
HOY = "2026-11-07T10:00:00-05:00"
LINEA = {"version": "1", "aprobadores": [YO], "etapas": {
    "producir": {},
    "mecanica": {"depende": ["producir"]},
    "verificar": {"depende": ["producir", "mecanica"], "puerta": "PJ", "condicional": True,
                  "ciclo": {"vuelve_a": "producir", "max_rondas": 2}},
    "siguiente": {"depende": ["verificar"]},
}}


def hallazgo(**k):
    return {"donde": "l. 3", "que": "dice X", "gravedad": "corregir", "clase": "M", "regla": "", "decidir": "", **k}


def informe(*hs):
    return json.dumps({"hallazgos": list(hs), "cierre": "listo"})


LIMPIO = informe()
CON_R = informe(hallazgo(clase="R", regla="D30"))
CON_J = informe(hallazgo(clase="J", decidir="si A o B"))
OTRO_R = informe(hallazgo(clase="R", regla="D30", donde="Ficha 2"))


@pytest.fixture
def claude_guion(tmp_path, monkeypatch):
    """Cada llamada devuelve el siguiente informe de `guion`; deja en `pedidos` lo que recibió."""
    estado = {"guion": tmp_path / "guion.json", "pedidos": tmp_path / "pedidos.jsonl", "n": tmp_path / "n"}
    f = tmp_path / "claude"
    f.write_text(f"""#!/usr/bin/env python3
import json, os, sys
n = int(open({str(estado['n'])!r}).read()) if os.path.exists({str(estado['n'])!r}) else 0
open({str(estado['n'])!r}, "w").write(str(n + 1))
argv = sys.argv
sistema = open(argv[argv.index("--system-prompt-file") + 1]).read()
with open({str(estado['pedidos'])!r}, "a") as p:
    p.write(json.dumps({{"argv": argv, "sistema": sistema, "texto": sys.stdin.read()}}) + "\\n")
guion = json.load(open({str(estado['guion'])!r}))
print(json.dumps({{"result": guion[min(n, len(guion) - 1)], "is_error": False, "usage": {{}}}}))
""", encoding="utf-8")
    f.chmod(f.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("CLAUDE_BIN", str(f))

    def poner(*informes):
        estado["guion"].write_text(json.dumps(list(informes)), encoding="utf-8")

    def pedidos():
        return [json.loads(x) for x in estado["pedidos"].read_text(encoding="utf-8").splitlines()]

    return poner, pedidos


@pytest.fixture
def t(tmp_path):
    c = tmp_path / "trabajo"
    c.mkdir()
    for a in (["init", "-q"], ["config", "user.name", "Prueba"], ["config", "user.email", "p@ejemplo.invalid"]):
        subprocess.run(["git", *a], cwd=c, check=True)
    S.nuevo(c, "t", LINEA)
    (tmp_path / "paquete.md").write_text("### D30 · Corte por rol\n", encoding="utf-8")
    (c / "fuera.md").write_text("NO-DEBE-SALIR", encoding="utf-8")
    return c


class Producir:
    def __init__(self):
        self.n = 0

    def nodo(self):
        def f(ctx):
            self.n += 1
            return R.Resultado({"pieza.md": f"pieza versión {self.n}"})
        return R.Nodo(f, rol="producir")


def nodos(t, p):
    mecanica = R.Nodo(lambda ctx: R.Resultado({"informe.json": "{}"}), rol="mecanica")
    return {"producir": p.nodo(), "mecanica": mecanica, "siguiente": R.Nodo(lambda ctx: R.Resultado({"s.md": "s"}), rol="s"),
            "verificar": N.verificador([("claude", "sonnet")], (t.parent / "paquete.md",))}


# Forma del informe

def test_informe_valido():
    assert N.validar_informe(informe(hallazgo(), hallazgo(clase="R", regla="D1"), hallazgo(clase="J", decidir="x"))) == []
    assert N.validar_informe(LIMPIO) == []


def test_tolera_la_cerca_json():
    assert N.validar_informe("```json\n" + CON_R + "\n```") == []
    assert N.contar_informe("```json\n" + CON_R + "\n```") == (1, 0)


@pytest.mark.parametrize("texto, error", [
    ("no es json", "no es JSON"),
    ('{"cierre": "x"}', "lista de hallazgos"),
    ('["a"]', "lista de hallazgos"),
    (informe("texto suelto"), "no es un objeto"),
    (informe(hallazgo(clase="X")), "clase no válida"),
    (informe(hallazgo(gravedad="leve")), "gravedad no válida"),
    (informe(hallazgo(que="  ")), "no dice qué"),
    (informe(hallazgo(clase="R")), "R sin regla"),
    (informe(hallazgo(clase="J")), "J sin qué decidir"),
])
def test_informe_mal_formado(texto, error):
    assert any(error in e for e in N.validar_informe(texto))


def test_contar():
    assert N.contar_informe(LIMPIO) == (0, 0)
    assert N.contar_informe(informe(hallazgo(), hallazgo(clase="R", regla="D1"))) == (2, 0)
    assert N.contar_informe(informe(hallazgo(), hallazgo(clase="J", decidir="x"))) == (1, 1)


def test_el_modelo_no_decide_el_tipo1():
    assert N.contar_informe(informe(hallazgo(clase="R", regla="D42", tipo1=True))) == (1, 0)


def test_repetidos():
    antes = informe(hallazgo(clase="R", regla="D30", donde="Ficha 1"), hallazgo(clase="J", decidir="x", donde="Marco"))
    assert N.repetidos(antes, informe(hallazgo(clase="R", regla=" d30 ", donde="ficha  1", que="otra redacción")))
    assert not N.repetidos(antes, informe(hallazgo(clase="R", regla="D30", donde="Ficha 2")))
    assert not N.repetidos(antes, informe(hallazgo(clase="R", regla="D42", donde="Ficha 1")))
    assert not N.repetidos(antes, informe(hallazgo(clase="M", regla="D30", donde="Ficha 1")))
    assert not N.repetidos(antes, informe(hallazgo(clase="J", decidir="x", donde="Marco")))


# El nodo

def test_sin_paquete_no_corre(t, claude_guion):
    """Sin reglas pasadas y sin la etapa contexto, el verificador no llama al modelo."""
    poner, pedidos = claude_guion
    poner(LIMPIO)
    n = nodos(t, Producir())
    n["verificar"] = N.verificador([("claude", "sonnet")], ())
    with pytest.raises(S.Bloqueado, match="paquete"):
        R.correr(t, LINEA, n)
    assert not (t.parent / "pedidos.jsonl").exists()


@pytest.mark.parametrize("via, modelo", [("ollama", "qwen"), ("opencode", "opencode/x-free")])
def test_solo_vias_de_pago(t, via, modelo):
    with pytest.raises(S.Bloqueado, match="no admite"):
        N.verificador([(via, modelo)], (t.parent / "paquete.md",))


def test_recibe_solo_rol_paquete_y_lo_que_depende(t, claude_guion):
    poner, pedidos = claude_guion
    poner(LIMPIO)
    R.correr(t, LINEA, nodos(t, Producir()))
    p = pedidos()[0]
    assert p["sistema"].startswith("Eres el verificador") and "name: verificador" not in p["sistema"]
    assert p["argv"][p["argv"].index("--tools") + 1] == ""
    assert p["texto"].index("D30 · Corte por rol") < p["texto"].index("pieza versión 1")
    assert "informe.json" in p["texto"] and "NO-DEBE-SALIR" not in p["texto"]
    m = S.ultimo_manifiesto(t, "verificar")
    assert m["salidas"] and next(iter(m["salidas"])).endswith("/hallazgos.json")
    assert m["prompt_sha256"] == S.sha256_bytes(N.cuerpo_agente(N.VERIFICADOR).encode())


def test_limpio_sigue_sin_puerta(t, claude_guion):
    poner, _ = claude_guion
    poner(LIMPIO)
    p = Producir()
    assert R.correr(t, LINEA, nodos(t, p))["estado"] == "terminado"
    assert p.n == 1


def test_m_o_r_devuelve_la_pieza(t, claude_guion):
    poner, pedidos = claude_guion
    poner(CON_R, LIMPIO)
    p = Producir()
    assert R.correr(t, LINEA, nodos(t, p))["estado"] == "terminado"
    assert p.n == 2 and "pieza versión 2" in pedidos()[1]["texto"]


def test_j_para_en_la_puerta(t, claude_guion):
    poner, _ = claude_guion
    poner(CON_J)
    p = Producir()
    r = R.correr(t, LINEA, nodos(t, p))
    assert r["estado"] == "detenido" and r["puerta"] == "PJ" and p.n == 1


def test_hallazgo_repetido_tras_corregir_es_tipo1_y_para(t, claude_guion):
    poner, _ = claude_guion
    poner(CON_R, CON_R)
    p = Producir()
    r = R.correr(t, LINEA, nodos(t, p))
    assert r["estado"] == "detenido" and r["puerta"] == "PJ" and p.n == 2
    m = S.ultimo_manifiesto(t, "verificar")
    assert m["resultado"]["tipo1"] == ["R D30 en l. 3"] and m["resultado"]["hallazgos"] == 0
    assert R.correr(t, LINEA, nodos(t, p), R.decidir(t, LINEA, "PJ", YO, HOY))["estado"] == "terminado"
    assert p.n == 2


def test_hallazgo_nuevo_en_la_segunda_ronda_no_es_tipo1(t, claude_guion):
    poner, _ = claude_guion
    poner(CON_R, OTRO_R)
    p = Producir()
    assert R.correr(t, LINEA, nodos(t, p))["estado"] == "terminado"
    assert p.n == 2 and "tipo1" not in S.ultimo_manifiesto(t, "verificar")["resultado"]


def test_informe_ilegible_no_cuenta_como_limpio(t, claude_guion):
    poner, _ = claude_guion
    poner("todo bien")
    with pytest.raises(M.ErrorModelo, match="no es JSON"):
        R.correr(t, LINEA, nodos(t, Producir()))
    assert S.ultimo_manifiesto(t, "verificar") is None
