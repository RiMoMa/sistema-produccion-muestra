"""Bloque 18: medición desde los archivos del trabajo. Sin red y sin gastar."""
import json
import subprocess

import pytest

from motor import medir as Me
from motor import runtime as R
from motor import state as S

YO = "Persona Aprobadora"
HOY = "2026-11-07T10:00:00-05:00"
LINEA = {"version": "1", "aprobadores": [YO], "etapas": {
    "producir": {"puerta": "P1"},
    "revisar": {"depende": ["producir"]},
}}


def nodos(caer=False):
    def producir(ctx):
        return R.Resultado({"p.md": "pieza"}, tokens={"entrada": 100, "salida": 20, "cache_leido": 40},
                           costo_usd=0.5)

    def revisar(ctx):
        if caer:
            raise RuntimeError("caída simulada")
        return R.Resultado({"h.json": "{}"}, tokens={"entrada": 1000, "salida": 50, "costo_estimado": 0.3},
                           detalle={"via": "claude"})

    return {"producir": R.Nodo(producir, rol="escritor", origen="modelo",
                               ejecutor={"modelo": "deepseek-v4-pro", "rutas": [["deepseek", "deepseek-v4-pro"]]}),
            "revisar": R.Nodo(revisar, rol="verificador", origen="modelo",
                              ejecutor={"modelo": "sonnet", "rutas": [["claude", "sonnet"]]})}


@pytest.fixture
def t(tmp_path):
    c = tmp_path / "trabajo"
    c.mkdir()
    for a in (["init", "-q"], ["config", "user.name", "Prueba"], ["config", "user.email", "p@ejemplo.invalid"]):
        subprocess.run(["git", *a], cwd=c, check=True)
    S.nuevo(c, "trabajo-a", LINEA)
    return c


def completo(t, caer_antes=False):
    R.correr(t, LINEA, nodos())
    if caer_antes:
        with pytest.raises(RuntimeError):
            R.correr(t, LINEA, nodos(caer=True), R.decidir(t, LINEA, "P1", YO, HOY))
        return R.correr(t, LINEA, nodos())
    return R.correr(t, LINEA, nodos(), R.decidir(t, LINEA, "P1", YO, HOY))


def test_totales_cuadran_con_los_manifiestos(t):
    completo(t)
    d = Me.medir([t])
    assert d["grupos"]["producir"] == {"corridas": 1, "caidas": 0, "entrada": 100, "cache_leido": 40, "salida": 20,
                                       "costo_usd": 0.5, "equivalente_api": 0}
    assert d["grupos"]["revisar"]["entrada"] == 1000 and d["grupos"]["revisar"]["equivalente_api"] == 0.3
    assert d["total"]["corridas"] == 2 and d["total"]["entrada"] == 1100


def test_equivalente_api_no_suma_al_costo_real(t):
    completo(t)
    d = Me.medir([t])
    assert d["total"]["costo_usd"] == pytest.approx(0.5) and d["total"]["equivalente_api"] == pytest.approx(0.3)


def test_caidas_se_cuentan_aparte(t):
    completo(t, caer_antes=True)
    d = Me.medir([t])
    assert d["grupos"]["revisar"]["caidas"] == 1 and d["grupos"]["revisar"]["corridas"] == 1
    assert d["trabajos"]["trabajo-a"]["caidas"] == 1


def test_etapa_saltada_no_suma_dos_veces(t):
    completo(t)
    R.correr(t, LINEA, nodos())
    assert Me.medir([t])["total"]["corridas"] == 2


def test_edicion_humana_no_gasta(t):
    R.correr(t, LINEA, nodos())
    ruta = next(iter(S.ultimo_manifiesto(t, "producir")["salidas"]))
    (t / ruta).write_text("pieza editada", encoding="utf-8")
    S.registrar_edicion(t, LINEA, "producir", ruta, YO, HOY)
    d = Me.medir([t])
    assert d["grupos"]["producir"]["corridas"] == 1 and d["grupos"]["producir"]["entrada"] == 100


@pytest.mark.parametrize("por, claves", [
    ("rol", {"escritor", "verificador"}), ("modelo", {"deepseek-v4-pro", "sonnet"}), ("via", {"deepseek", "claude"})])
def test_agrupa_por_dimension(t, por, claves):
    completo(t)
    assert set(Me.medir([t], por)["grupos"]) == claves


def test_caida_se_agrupa_por_via_y_modelo(t):
    completo(t, caer_antes=True)
    assert Me.medir([t], "via")["grupos"]["claude"]["caidas"] == 1
    assert Me.medir([t], "modelo")["grupos"]["sonnet"]["caidas"] == 1


def test_varios_trabajos_suman(t, tmp_path):
    otro = tmp_path / "otro"
    otro.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=otro, check=True)
    S.nuevo(otro, "trabajo-b", LINEA)
    R.correr(otro, LINEA, nodos())
    completo(t)
    d = Me.medir([t, otro])
    assert d["total"]["corridas"] == 3 and set(d["trabajos"]) == {"trabajo-a", "trabajo-b"}


def test_cadena_rota_se_avisa_y_se_suma(t):
    completo(t)
    primero = sorted((t / "corridas").glob("*.json"))[0]
    doc = json.loads(primero.read_text(encoding="utf-8"))
    doc["costo_usd"] = 0.0
    primero.write_text(json.dumps(doc), encoding="utf-8")
    d = Me.medir([t])
    assert d["trabajos"]["trabajo-a"]["cadena_rota"] is True and d["total"]["corridas"] == 2
    assert "cadena de manifiestos de trabajo-a está rota" in Me.tabla(d)
    assert "rota" not in Me.tabla(Me.medir([t], "rol") | {"trabajos": {"x": {"cadena_rota": False}}})


def test_dimension_desconocida(t):
    with pytest.raises(S.Bloqueado, match="dimensión"):
        Me.medir([t], "color")


def test_comando(t, capsys):
    completo(t)
    assert Me.main([str(t), "--por", "via", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["grupos"]["claude"]["corridas"] == 1
    Me.main([str(t)])
    assert "TOTAL" in capsys.readouterr().out


def test_cuenta_la_via_que_respondio_no_la_primera(t):
    def respaldo(ctx):
        return R.Resultado({"h.json": "{}"}, detalle={"via": "deepseek"})
    n = nodos()
    n["revisar"] = R.Nodo(respaldo, rol="verificador", origen="modelo",
                          ejecutor={"modelo": "sonnet", "rutas": [["claude", "sonnet"], ["deepseek", "deepseek-v4-pro"]]})
    R.correr(t, LINEA, n)
    R.correr(t, LINEA, n, R.decidir(t, LINEA, "P1", YO, HOY))
    assert set(Me.medir([t], "via")["grupos"]) == {"deepseek"}


def test_nodo_sin_ejecutor_se_nombra(t):
    n = {"producir": R.Nodo(lambda ctx: R.Resultado({"p.md": "x"}), rol="p"), "revisar": nodos()["revisar"]}
    R.correr(t, LINEA, n)
    assert set(Me.medir([t], "via")["grupos"]) == {"sin declarar"}
