"""Prueba LangGraph con nodos falsos: sin red y sin gastar tokens."""
import json
import subprocess
from collections import Counter

import pytest

from motor import runtime as R
from motor import state as S

HOY = "2026-11-06T10:00:00-05:00"
YO = "Persona Aprobadora"
LINEA = {"version": "1", "aprobadores": [YO], "etapas": {
    "extraer": {},
    "analizar": {"depende": ["extraer"], "puerta": "P1"},
    "producir": {"depende": ["analizar"]},
    "revisar": {"depende": ["producir"], "puerta": "PJ", "condicional": True,
                "ciclo": {"vuelve_a": "producir", "max_rondas": 2}},
    "publicar": {"depende": ["producir", "revisar"], "puerta": "P4", "aprueba": ["producir"]},
}}


class Falsos:
    """Cuenta llamadas. `guion` da por etapa una lista de dicts para cada llamada sucesiva."""

    def __init__(self, guion=None, fijo=()):
        self.llamadas, self.guion, self.fijo, self.vistos = Counter(), guion or {}, set(fijo), []

    def nodos(self):
        return {e: R.Nodo(self.funcion(e), rol=e, origen="modelo", ejecutor={"modelo": "falso"}) for e in LINEA["etapas"]}

    def funcion(self, etapa):
        def f(ctx):
            self.llamadas[etapa] += 1
            n = self.llamadas[etapa]
            self.vistos.append((etapa, list(ctx.entradas), list(ctx.extras)))
            pasos = self.guion.get(etapa, [])
            paso = pasos[n - 1] if n <= len(pasos) else {}
            if paso.get("falla"):
                raise RuntimeError("caída simulada")
            texto = f"{etapa} MARCA-DE-TEXTO" if etapa in self.fijo else f"{etapa} MARCA-DE-TEXTO {n}"
            return R.Resultado({"salida.md": texto}, tokens={"salida": 10}, costo_usd=0.01,
                               hallazgos=paso.get("hallazgos", 0), juicios=paso.get("juicios", 0))
        return f


@pytest.fixture
def t(tmp_path):
    def git(*a):
        subprocess.run(["git", *a], cwd=tmp_path, check=True, capture_output=True)
    git("init", "-q")
    git("config", "user.name", "Prueba")
    git("config", "user.email", "prueba@ejemplo.invalid")
    S.nuevo(tmp_path, "trabajo-a", LINEA)
    return tmp_path


def correr(t, f, reanudar=None):
    return R.correr(t, LINEA, f.nodos(), reanudar)


def aprobar_y_seguir(t, f, puerta):
    return correr(t, f, R.decidir(t, LINEA, puerta, YO, HOY))


def hasta_el_final(t, f):
    assert correr(t, f)["puerta"] == "P1"
    assert aprobar_y_seguir(t, f, "P1")["puerta"] == "P4"
    return aprobar_y_seguir(t, f, "P4")


def test_se_detiene_en_la_puerta_sin_correr_lo_siguiente(t):
    f = Falsos()
    r = correr(t, f)
    assert r["estado"] == "detenido" and r["puerta"] == "P1"
    assert f.llamadas == {"extraer": 1, "analizar": 1}
    assert list(r["sujetos"].values()) == list(S.sujetos(t, LINEA, "P1").values())


def test_flujo_completo(t):
    f = Falsos()
    assert hasta_el_final(t, f)["estado"] == "terminado"
    assert S.siguiente(t, LINEA) == "terminado"
    assert set(f.llamadas.values()) == {1}


def test_reanudar_no_repite_lo_ya_corrido(t):
    f = Falsos()
    correr(t, f)
    aprobar_y_seguir(t, f, "P1")
    assert f.llamadas["extraer"] == f.llamadas["analizar"] == 1


def test_entradas_son_las_salidas_de_las_dependencias(t):
    f = Falsos()
    correr(t, f)
    etapa, entradas, _ = f.vistos[1]
    assert etapa == "analizar" and entradas == list(S.ultimo_manifiesto(t, "extraer")["salidas"])


def test_correr_otra_vez_sin_decidir_no_avanza(t):
    f = Falsos()
    correr(t, f)
    assert correr(t, f)["puerta"] == "P1"
    assert f.llamadas == {"extraer": 1, "analizar": 1}


def test_reanudar_con_identificador_falso_no_avanza(t):
    f = Falsos()
    correr(t, f)
    with pytest.raises(S.Bloqueado, match="no hay constancia"):
        correr(t, f, "000099-P1")
    assert f.llamadas["producir"] == 0
    assert aprobar_y_seguir(t, f, "P1")["puerta"] == "P4"


def test_constancia_sin_commit_no_avanza(t):
    f = Falsos()
    correr(t, f)
    c = S.aprobar(t, LINEA, "P1", YO, HOY)
    with pytest.raises(S.Bloqueado, match="no tiene commit"):
        correr(t, f, c["id"])
    assert f.llamadas["producir"] == 0


def test_constancia_cambiada_despues_del_commit_no_avanza(t):
    f = Falsos()
    correr(t, f)
    id_ = R.decidir(t, LINEA, "P1", YO, HOY)
    ruta = t / "constancias" / f"{id_}.json"
    ruta.write_text(ruta.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(S.Bloqueado, match="no tiene commit"):
        correr(t, f, id_)


def test_cambio_entre_aprobar_y_reanudar_no_avanza(t):
    f = Falsos()
    correr(t, f)
    id_ = R.decidir(t, LINEA, "P1", YO, HOY)
    (t / next(iter(S.sujetos(t, LINEA, "P1")))).write_text("cambio", encoding="utf-8")
    with pytest.raises(S.Bloqueado, match="vencida"):
        correr(t, f, id_)
    assert f.llamadas["producir"] == 0


def test_reanudar_con_decision_anterior_no_avanza(t):
    f = Falsos()
    correr(t, f)
    vieja = R.decidir(t, LINEA, "P1", YO, HOY)
    R.decidir(t, LINEA, "P1", YO, HOY, decision="rechazada")
    assert correr(t, f, vieja)["estado"] == "rechazado"
    assert f.llamadas["producir"] == 0


def test_reanudar_con_constancia_de_una_version_anterior_no_avanza(t):
    f = Falsos()
    correr(t, f)
    vieja = R.decidir(t, LINEA, "P1", YO, HOY, decision="devuelta", observacion="x")
    correr(t, f, vieja)
    with pytest.raises(S.Bloqueado, match="no decide"):
        correr(t, f, vieja)
    assert f.llamadas["producir"] == 0
    assert aprobar_y_seguir(t, f, "P1")["puerta"] == "P4"


def test_devolucion_sin_commit_no_rehace(t):
    f = Falsos()
    correr(t, f)
    c = S.aprobar(t, LINEA, "P1", YO, HOY, decision="devuelta", observacion="x")
    with pytest.raises(S.Bloqueado, match="no tiene commit"):
        correr(t, f, c["id"])
    assert f.llamadas["analizar"] == 1


def test_sin_commit_tampoco_avanza_con_checkpoint_borrado(t):
    f = Falsos()
    correr(t, f)
    S.aprobar(t, LINEA, "P1", YO, HOY)
    (t / ".cache" / "checkpoints.sqlite").unlink()
    with pytest.raises(S.Bloqueado, match="no tiene commit"):
        correr(t, f)


def test_rechazada_termina(t):
    f = Falsos()
    correr(t, f)
    r = correr(t, f, R.decidir(t, LINEA, "P1", YO, HOY, decision="rechazada"))
    assert r["estado"] == "rechazado" and f.llamadas["producir"] == 0
    assert correr(t, f)["estado"] == "rechazado"


def test_devuelta_rehace_con_la_observacion_como_entrada(t):
    f = Falsos()
    correr(t, f)
    id_ = R.decidir(t, LINEA, "P1", YO, HOY, decision="devuelta", observacion="falta alcance")
    r = correr(t, f, id_)
    assert r["puerta"] == "P1" and f.llamadas["analizar"] == 2
    assert f.vistos[-1][2] == [f"constancias/{id_}.json"]
    assert f"constancias/{id_}.json" in S.ultimo_manifiesto(t, "analizar")["entradas"]


def test_devuelta_con_salida_identica_vuelve_a_preguntar_y_no_gira(t):
    f = Falsos(fijo=["analizar"])
    correr(t, f)
    r = correr(t, f, R.decidir(t, LINEA, "P1", YO, HOY, decision="devuelta", observacion="otra vez"))
    assert r["puerta"] == "P1" and f.llamadas["analizar"] == 2
    assert aprobar_y_seguir(t, f, "P1")["puerta"] == "P4"


def test_ciclo_corrige_y_sigue(t):
    f = Falsos({"revisar": [{"hallazgos": 2}, {"hallazgos": 0}]})
    correr(t, f)
    assert aprobar_y_seguir(t, f, "P1")["puerta"] == "P4"
    assert f.llamadas["producir"] == 2 and f.llamadas["revisar"] == 2
    informe = S.ultimo_manifiesto(t, "revisar")["entradas"]
    assert len(informe) == 1 and "producir" in next(iter(informe))
    assert any(e == "producir" and x for e, _, x in f.vistos)


def test_el_ciclo_se_detiene_en_el_maximo_y_llega_a_la_puerta(t):
    f = Falsos({"revisar": [{"hallazgos": 3}] * 9})
    correr(t, f)
    assert aprobar_y_seguir(t, f, "P1")["puerta"] == "P4"
    assert f.llamadas["revisar"] == 2 and f.llamadas["producir"] == 2


def test_puerta_condicional_solo_aparece_si_hay_juicio(t):
    f = Falsos({"revisar": [{"hallazgos": 1, "juicios": 1}, {}]})
    correr(t, f)
    r = aprobar_y_seguir(t, f, "P1")
    assert r["puerta"] == "PJ" and f.llamadas["producir"] == 1
    assert aprobar_y_seguir(t, f, "PJ")["puerta"] == "P4"
    assert f.llamadas["producir"] == 2


def test_borrar_el_checkpoint_no_pierde_nada(t):
    f = Falsos()
    correr(t, f)
    id_ = R.decidir(t, LINEA, "P1", YO, HOY)
    (t / ".cache" / "checkpoints.sqlite").unlink()
    assert correr(t, f, id_)["puerta"] == "P4"
    assert f.llamadas["extraer"] == f.llamadas["analizar"] == 1


def test_borrar_el_checkpoint_conserva_la_devolucion(t):
    f = Falsos()
    correr(t, f)
    R.decidir(t, LINEA, "P1", YO, HOY, decision="devuelta", observacion="falta")
    (t / ".cache" / "checkpoints.sqlite").unlink()
    assert correr(t, f)["puerta"] == "P1"
    assert f.llamadas["analizar"] == 2


def test_borrar_el_checkpoint_respeta_el_limite_de_rondas(t):
    f = Falsos({"revisar": [{"hallazgos": 3}] * 9})
    correr(t, f)
    aprobar_y_seguir(t, f, "P1")
    (t / ".cache" / "checkpoints.sqlite").unlink()
    assert correr(t, f)["puerta"] == "P4"
    assert f.llamadas["revisar"] == 2


def test_caida_no_paga_dos_veces(t):
    f = Falsos({"analizar": [{"falla": True}]})
    with pytest.raises(RuntimeError):
        correr(t, f)
    assert correr(t, f)["puerta"] == "P1"
    assert f.llamadas["extraer"] == 1 and f.llamadas["analizar"] == 2


def test_caida_queda_registrada_y_sin_manifiesto(t):
    f = Falsos({"analizar": [{"falla": True}]})
    with pytest.raises(RuntimeError):
        correr(t, f)
    assert S.ultimo_manifiesto(t, "analizar") is None
    lineas = [json.loads(x) for x in (t / "llamadas.jsonl").read_text(encoding="utf-8").splitlines()]
    assert lineas[-1]["estado"].startswith("error")


def test_gasto_se_registra_y_no_interrumpe(t):
    f = Falsos()
    r = hasta_el_final(t, f)
    lineas = (t / "llamadas.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lineas) == 5 and r["estado"] == "terminado"
    assert r["costo_usd"] == pytest.approx(0.05)


def test_el_checkpoint_no_guarda_texto(t):
    hasta_el_final(t, Falsos())
    for archivo in (t / ".cache").iterdir():
        assert b"MARCA-DE-TEXTO" not in archivo.read_bytes()


def test_un_nodo_no_escribe_fuera_de_su_carpeta(t):
    for nombre in ("../fuera.md", "a/b.md", ".."):
        nodos = Falsos().nodos()
        nodos["extraer"] = R.Nodo(lambda ctx, n=nombre: R.Resultado({n: "x"}), rol="r")
        with pytest.raises(S.Bloqueado, match="no válido"):
            R.correr(t, LINEA, nodos)
    assert not (t.parent / "fuera.md").exists()


def test_un_nodo_sin_salidas_falla(t):
    nodos = Falsos().nodos()
    nodos["extraer"] = R.Nodo(lambda ctx: R.Resultado({}), rol="r")
    with pytest.raises(S.Bloqueado, match="no devolvió"):
        R.correr(t, LINEA, nodos)


def test_las_corridas_no_pisan_artefactos(t):
    f = Falsos()
    correr(t, f)
    primera = next(iter(S.ultimo_manifiesto(t, "analizar")["salidas"]))
    correr(t, f, R.decidir(t, LINEA, "P1", YO, HOY, decision="devuelta", observacion="x"))
    assert (t / primera).read_text(encoding="utf-8").endswith("1")
    assert primera != next(iter(S.ultimo_manifiesto(t, "analizar")["salidas"]))


def test_un_nodo_no_corre_sin_sus_previas_aunque_el_grafo_lo_llame(t):
    f = Falsos()
    correr(t, f)
    nodo = R._nodo_etapa(t, LINEA, "producir", f.nodos()["producir"])
    with pytest.raises(S.Bloqueado, match="falta aprobar P1"):
        nodo({"extras": {}, "artefactos": {}, "costo_usd": 0.0})
    assert f.llamadas["producir"] == 0


def test_dibujo_muestra_puertas_y_ciclo():
    dibujo = R.dibujar(LINEA)
    for nombre in (*LINEA["etapas"], "P1", "PJ", "P4"):
        assert nombre in dibujo
    assert "PJ -.-> producir" in dibujo
    assert "P1 -.-> __end__" not in dibujo


def test_faltan_nodos(t):
    with pytest.raises(S.Bloqueado, match="faltan nodos"):
        R.correr(t, LINEA, {"extraer": R.Nodo(lambda c: None, rol="r")})


def test_decidir_exige_repositorio(tmp_path):
    S.nuevo(tmp_path, "t", LINEA)
    f = Falsos()
    R.correr(tmp_path, LINEA, f.nodos())
    with pytest.raises(S.Bloqueado, match="commit"):
        R.decidir(tmp_path, LINEA, "P1", YO, HOY)


def test_edicion_humana_en_la_puerta(t):
    f = Falsos()
    correr(t, f)
    ruta = next(iter(S.sujetos(t, LINEA, "P1")))
    (t / ruta).write_text("editado a mano", encoding="utf-8")
    S.registrar_edicion(t, LINEA, "analizar", ruta, YO, HOY)
    assert aprobar_y_seguir(t, f, "P1")["puerta"] == "P4"
    assert f.llamadas["analizar"] == 1


def test_rehacer_una_etapa_vencida_arrastra_lo_posterior(t):
    f = Falsos()
    hasta_el_final(t, f)
    ruta = next(iter(S.ultimo_manifiesto(t, "extraer")["salidas"]))
    (t / ruta).write_text("cambió", encoding="utf-8")
    assert S.vigencia(t, LINEA)["publicar"]["estado"] == "vencida"
    assert correr(t, f)["puerta"] == "P1"
    assert f.llamadas["extraer"] == 2 and f.llamadas["analizar"] == 2
