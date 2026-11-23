"""Bloque 3: el escritor, con un DeepSeek falso que responde por guion. Sin red y sin gastar."""
import json
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from motor import nodos as N
from motor import runtime as R
from motor import state as S

YO = "Persona Aprobadora"
HOY = "2026-11-07T10:00:00-05:00"
LINEA = {"version": "1", "aprobadores": [YO], "etapas": {
    "brief": {"puerta": "P1"},
    "producir": {"depende": ["brief"], "puerta": "PM", "condicional": True},
    "revisar": {"depende": ["producir"], "ciclo": {"vuelve_a": "producir", "max_rondas": 2}},
}}


class Guion(BaseHTTPRequestHandler):
    textos, recibido = [], []

    def do_POST(self):
        cuerpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Guion.recibido.append(cuerpo)
        n = len(Guion.recibido) - 1
        texto = Guion.textos[min(n, len(Guion.textos) - 1)]
        datos = json.dumps({"model": "deepseek-v4-pro", "usage": {"prompt_tokens": 10, "completion_tokens": 5},
                            "choices": [{"message": {"content": texto}}]}).encode()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(datos)

    def log_message(self, *a):
        pass


@pytest.fixture
def deepseek(monkeypatch, tmp_path):
    s = HTTPServer(("127.0.0.1", 0), Guion)
    threading.Thread(target=s.serve_forever, args=(0.01,), daemon=True).start()
    Guion.textos, Guion.recibido = [], []
    monkeypatch.setenv("DEEPSEEK_URL", f"http://127.0.0.1:{s.server_port}")
    claves = tmp_path / "claves"
    claves.mkdir()
    (claves / "borrador").write_text("clave-de-prueba\n", encoding="utf-8")
    (claves / "borrador").chmod(0o600)
    monkeypatch.setenv("MOTOR_CLAVES", str(claves))

    def poner(*textos):
        Guion.textos = list(textos)

    yield poner
    s.shutdown()


@pytest.fixture
def t(tmp_path):
    c = tmp_path / "trabajo"
    c.mkdir()
    for a in (["init", "-q"], ["config", "user.name", "Prueba"], ["config", "user.email", "p@ejemplo.invalid"]):
        subprocess.run(["git", *a], cwd=c, check=True)
    S.nuevo(c, "t", LINEA)
    (tmp_path / "brief.md").write_text("BRIEF: escriba sobre agendas.", encoding="utf-8")
    (tmp_path / "paquete.md").write_text("REGLA: sin guiones largos.", encoding="utf-8")
    return c


def nodos(t, hallazgos=(0,)):
    llamadas = []

    def revisar(ctx):
        llamadas.append(1)
        n = hallazgos[min(len(llamadas) - 1, len(hallazgos) - 1)]
        return R.Resultado({"hallazgos.json": json.dumps({"hallazgos": ["x"] * n})}, hallazgos=n)

    return {"brief": N.entrada(t.parent / "brief.md"),
            "producir": N.borrador([("deepseek", "deepseek-v4-pro")], (t.parent / "paquete.md",)),
            "revisar": R.Nodo(revisar, rol="revisar")}


def seguir(t, n, puerta):
    return R.correr(t, LINEA, n, R.decidir(t, LINEA, puerta, YO, HOY))


def mensaje(i):
    return Guion.recibido[i]["messages"][1]["content"]


# Marcas

def test_contar_marcas():
    texto = "a [FUENTE PENDIENTE: x] b [FALTA: y] c [COMPROBACIÓN PENDIENTE: f] d [comprobacion pendiente: g] [OTRA]"
    assert N.contar_marcas(texto) == (0, 4)
    assert N.contar_marcas("limpia [nota]") == (0, 0)


def test_marcas_dentro_de_un_prompt_no_cuentan():
    texto = "Prompt:\n\n```text\nSi no sabe, marque [FALTA: definir salida].\n```\n\nFuera [FALTA: el dato]\n```\n[FALTA: x]\n```\n"
    assert N.contar_marcas(texto) == (0, 1)


@pytest.mark.parametrize("via, modelo", [("claude", "sonnet"), ("opencode", "opencode/x-free"), ("ollama", "q")])
def test_solo_deepseek_escribe(via, modelo):
    with pytest.raises(S.Bloqueado, match="D90"):
        N.borrador([(via, modelo)], ())


# Entrada

def test_el_brief_entra_y_espera_p1(t, deepseek):
    deepseek("pieza")
    r = R.correr(t, LINEA, nodos(t))
    assert r["puerta"] == "P1" and Guion.recibido == []
    m = S.ultimo_manifiesto(t, "brief")
    assert m["reglas_sha256"] == S.sha256_archivo(t.parent / "brief.md")
    assert (t / next(iter(m["salidas"]))).read_text(encoding="utf-8") == "BRIEF: escriba sobre agendas."


# Producción y corrección

def test_primera_ronda_recibe_reglas_y_brief(t, deepseek):
    deepseek("pieza v1")
    R.correr(t, LINEA, nodos(t))
    assert seguir(t, nodos(t), "P1")["estado"] == "terminado"
    sistema, texto = Guion.recibido[0]["messages"][0]["content"], mensaje(0)
    assert sistema.startswith("Escribes una pieza") and "name: borrador" not in sistema
    assert texto.index("REGLA: sin guiones") < texto.index("BRIEF: escriba")
    m = S.ultimo_manifiesto(t, "producir")
    assert len(m["entradas"]) == 1 and next(iter(m["salidas"])).endswith("/pieza.md")


def test_correccion_recibe_su_pieza_anterior_y_el_informe(t, deepseek):
    deepseek("pieza v1", "pieza v2")
    R.correr(t, LINEA, nodos(t, hallazgos=(2, 0)))
    n = nodos(t, hallazgos=(2, 0))
    assert seguir(t, n, "P1")["estado"] == "terminado"
    assert len(Guion.recibido) == 2
    texto = mensaje(1)
    assert "BRIEF: escriba" in texto and "pieza v1" in texto and "hallazgos" in texto
    assert texto.index("pieza v1") < texto.index('{"hallazgos"')
    entradas = S.ultimo_manifiesto(t, "producir")["entradas"]
    assert any(e.endswith("producir/000002/pieza.md") for e in entradas)
    assert any(e.endswith("hallazgos.json") for e in entradas)


def test_marcas_paran_en_la_puerta_y_no_corrigen(t, deepseek):
    deepseek("pieza con [FALTA: el dato de la EPS]")
    R.correr(t, LINEA, nodos(t))
    r = seguir(t, nodos(t), "P1")
    assert r["estado"] == "detenido" and r["puerta"] == "PM" and len(Guion.recibido) == 1
    assert S.ultimo_manifiesto(t, "producir")["resultado"]["juicios"] == 1
    assert seguir(t, nodos(t), "PM")["estado"] == "terminado" and len(Guion.recibido) == 1
