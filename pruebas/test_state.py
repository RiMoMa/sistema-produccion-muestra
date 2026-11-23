"""Las cuatro primeras vienen de un proyecto anterior del autor. Las demás prueban cada control."""
import json

import pytest

from motor import state as S

HOY = "2026-11-06T10:00:00-05:00"
YO = "Persona Aprobadora"
LINEA = {"version": "1", "aprobadores": [YO], "etapas": {
    "extraer": {"depende": []},
    "analizar": {"depende": ["extraer"], "puerta": "P1"},
    "producir": {"depende": ["analizar"]},
    "publicar": {"depende": ["producir"], "puerta": "P2", "aprueba": ["producir"]},
}}
SALIDA = {e: f"artefactos/{e}.txt" for e in LINEA["etapas"]}


@pytest.fixture
def t(tmp_path):
    S.nuevo(tmp_path, "trabajo-a", LINEA)
    return tmp_path


def correr(carpeta, etapa, texto="v1", **extra):
    entradas = S.digests(carpeta, [SALIDA[d] for d in LINEA["etapas"][etapa]["depende"]])
    (carpeta / SALIDA[etapa]).write_text(texto, encoding="utf-8")
    return S.registrar_corrida(carpeta, LINEA, etapa, rol="r", origen="script", ejecutor={"modelo": "m"},
                               entradas=entradas, salidas=[SALIDA[etapa]], inicio=HOY, fin=HOY, **extra)


def hasta_p1(carpeta):
    correr(carpeta, "extraer")
    correr(carpeta, "analizar")
    return S.aprobar(carpeta, LINEA, "P1", YO, HOY)


def completo(carpeta):
    hasta_p1(carpeta)
    correr(carpeta, "producir")
    correr(carpeta, "publicar")
    return S.aprobar(carpeta, LINEA, "P2", YO, HOY)


def estado(carpeta, etapa):
    return S.vigencia(carpeta, LINEA)[etapa]["estado"]


# Línea base traída del origen

def test_no_salta_etapas(t):
    with pytest.raises(S.Bloqueado):
        S.puede_correr(t, LINEA, "analizar")


def test_puerta_bloquea_siguiente(t):
    correr(t, "extraer")
    correr(t, "analizar")
    with pytest.raises(S.Bloqueado, match="P1"):
        S.puede_correr(t, LINEA, "producir")
    S.aprobar(t, LINEA, "P1", YO, HOY)
    S.puede_correr(t, LINEA, "producir")


def test_no_aprueba_etapa_sin_hacer(t):
    with pytest.raises(S.Bloqueado):
        S.aprobar(t, LINEA, "P1", YO, HOY)


def test_rehacer_invalida_lo_posterior(t):
    hasta_p1(t)
    correr(t, "extraer", "v2")
    assert estado(t, "analizar") == "vencida"
    with pytest.raises(S.Bloqueado):
        S.puede_correr(t, LINEA, "producir")


def test_rehacer_en_otra_ruta_vence_aunque_el_archivo_viejo_siga_igual(t):
    correr(t, "extraer")
    correr(t, "analizar")
    (t / "artefactos/extraer-2.txt").write_text("v2", encoding="utf-8")
    S.registrar_corrida(t, LINEA, "extraer", rol="r", origen="script", ejecutor={}, entradas={},
                        salidas=["artefactos/extraer-2.txt"], inicio=HOY, fin=HOY)
    v = S.vigencia(t, LINEA)["analizar"]
    assert v["estado"] == "vencida" and "se rehízo" in v["causas"][0]


# Aprobación ligada al hash

def test_flujo_completo_termina(t):
    completo(t)
    assert S.siguiente(t, LINEA) == "terminado"


def test_siguiente_nombra_la_revision(t):
    correr(t, "extraer")
    assert S.siguiente(t, LINEA) == "analizar"
    correr(t, "analizar")
    assert S.siguiente(t, LINEA) == "revisión P1"


def test_un_byte_cambiado_vence_y_arrastra(t):
    completo(t)
    (t / SALIDA["analizar"]).write_text("v1 ", encoding="utf-8")
    v = S.vigencia(t, LINEA)
    assert v["analizar"]["estado"] == "vencida"
    assert "cambió la salida" in v["analizar"]["causas"][0]
    assert v["producir"]["estado"] == v["publicar"]["estado"] == "vencida"


def test_archivo_borrado_vence(t):
    completo(t)
    (t / SALIDA["publicar"]).unlink()
    assert estado(t, "publicar") == "vencida"


def test_puerta_cubre_lo_que_declara_aprueba(t):
    completo(t)
    c = json.loads(next((t / "constancias").glob("*P2.json")).read_text(encoding="utf-8"))
    assert {s["name"] for s in c["subject"]} == {SALIDA["producir"], SALIDA["publicar"]}


def test_nueva_version_exige_nueva_aprobacion(t):
    hasta_p1(t)
    correr(t, "analizar", "v2")
    assert estado(t, "analizar") == "por_aprobar"
    S.aprobar(t, LINEA, "P1", YO, HOY)
    assert estado(t, "analizar") == "vigente"


def test_volver_a_la_version_aprobada_recupera_la_constancia(t):
    hasta_p1(t)
    correr(t, "analizar", "v2")
    correr(t, "analizar", "v1")
    assert estado(t, "analizar") == "vigente"


def test_aprobar_sin_decir_quien_no_existe(t):
    correr(t, "extraer")
    correr(t, "analizar")
    with pytest.raises(TypeError):
        S.aprobar(t, LINEA, "P1", fecha=HOY)


@pytest.mark.parametrize("por", ["humano", "claude_delegado", ""])
def test_solo_aprueba_un_aprobador_declarado(t, por):
    correr(t, "extraer")
    correr(t, "analizar")
    with pytest.raises(S.Bloqueado, match="aprobador"):
        S.aprobar(t, LINEA, "P1", por, HOY)


def test_no_se_aprueba_por_adelantado(t):
    correr(t, "extraer")
    with pytest.raises(S.Bloqueado, match="pendiente"):
        S.aprobar(t, LINEA, "P1", YO, HOY)


def test_edicion_sin_registrar_no_se_aprueba(t):
    correr(t, "extraer")
    correr(t, "analizar")
    (t / SALIDA["analizar"]).write_text("a mano", encoding="utf-8")
    with pytest.raises(S.Bloqueado, match="vencida"):
        S.aprobar(t, LINEA, "P1", YO, HOY)


def test_edicion_registrada_se_aprueba_y_queda_escrita(t):
    correr(t, "extraer")
    correr(t, "analizar")
    anterior = S.sha256_archivo(t / SALIDA["analizar"])
    (t / SALIDA["analizar"]).write_text("a mano", encoding="utf-8")
    m = S.registrar_edicion(t, LINEA, "analizar", SALIDA["analizar"], YO, HOY)
    assert m["origen"] == "humano" and m["edita"]["anterior"] == anterior
    S.aprobar(t, LINEA, "P1", YO, HOY)
    assert estado(t, "analizar") == "vigente"


def test_edicion_exige_aprobador_y_cambio(t):
    correr(t, "extraer")
    with pytest.raises(S.Bloqueado, match="no cambió"):
        S.registrar_edicion(t, LINEA, "extraer", SALIDA["extraer"], YO, HOY)
    with pytest.raises(S.Bloqueado, match="aprobador"):
        S.registrar_edicion(t, LINEA, "extraer", SALIDA["extraer"], "agente", HOY)


def test_devuelta_exige_observacion_y_vuelve_a_la_etapa(t):
    correr(t, "extraer")
    correr(t, "analizar")
    with pytest.raises(S.Bloqueado, match="observación"):
        S.aprobar(t, LINEA, "P1", YO, HOY, decision="devuelta")
    S.aprobar(t, LINEA, "P1", YO, HOY, decision="devuelta", observacion="falta alcance")
    assert estado(t, "analizar") == "devuelta"
    assert S.siguiente(t, LINEA) == "analizar"


def test_rechazada_termina_el_trabajo(t):
    correr(t, "extraer")
    correr(t, "analizar")
    S.aprobar(t, LINEA, "P1", YO, HOY, decision="rechazada")
    assert S.siguiente(t, LINEA) == "rechazado"
    with pytest.raises(S.Bloqueado, match="rechazado"):
        S.puede_correr(t, LINEA, "extraer")


def test_revocar_es_escribir_otra(t):
    hasta_p1(t)
    S.aprobar(t, LINEA, "P1", YO, HOY, decision="devuelta", observacion="me arrepentí")
    assert estado(t, "analizar") == "devuelta"
    assert len(list((t / "constancias").glob("*.json"))) == 2


# Lectura de constancias

def test_reanudar_con_constancia_inexistente(t):
    hasta_p1(t)
    with pytest.raises(S.Bloqueado, match="no hay constancia"):
        S.leer_constancia(t, "P1", "000099-P1")


@pytest.mark.parametrize("id_", ["../x", "a/b", "..\\x"])
def test_reanudar_con_id_que_sale_de_la_carpeta(t, id_):
    with pytest.raises(S.Bloqueado, match="no válido"):
        S.leer_constancia(t, "P1", id_)


def test_constancia_de_otro_trabajo_no_cuenta(t, tmp_path_factory):
    c = hasta_p1(t)
    otro = tmp_path_factory.mktemp("otro")
    S.nuevo(otro, "trabajo-b", LINEA)
    correr(otro, "extraer")
    correr(otro, "analizar")
    fuente = next((t / "constancias").glob("*.json"))
    (otro / "constancias" / fuente.name).write_bytes(fuente.read_bytes())
    assert estado(otro, "analizar") == "por_aprobar"
    with pytest.raises(S.Bloqueado, match="no hay constancia"):
        S.leer_constancia(otro, "P1", c["id"])


def test_constancia_alterada_no_cuenta(t):
    hasta_p1(t)
    f = next((t / "constancias").glob("*.json"))
    doc = json.loads(f.read_text(encoding="utf-8"))
    doc["predicate"]["por"] = "otra persona"
    f.write_text(json.dumps(doc), encoding="utf-8")
    assert estado(t, "analizar") == "por_aprobar"


def test_constancia_ilegible_no_rompe_ni_cuenta(t):
    hasta_p1(t)
    next((t / "constancias").glob("*.json")).write_text("{no es json", encoding="utf-8")
    assert estado(t, "analizar") == "por_aprobar"


# Manifiestos

def test_artefacto_sin_manifiesto_no_cuenta(t):
    (t / SALIDA["extraer"]).write_text("suelto", encoding="utf-8")
    assert estado(t, "extraer") == "pendiente"


def test_manifiesto_alterado_vence(t):
    hasta_p1(t)
    f = sorted((t / "corridas").glob("*.json"))[1]
    doc = json.loads(f.read_text(encoding="utf-8"))
    doc["rol"] = "otro"
    f.write_text(json.dumps(doc), encoding="utf-8")
    assert "manifiesto alterado o borrado" in S.vigencia(t, LINEA)["analizar"]["causas"]


def test_manifiesto_ilegible_vence(t):
    hasta_p1(t)
    sorted((t / "corridas").glob("*.json"))[1].write_text("{", encoding="utf-8")
    assert estado(t, "analizar") == "vencida"


def test_manifiesto_sin_campos_vence_sin_caerse(t):
    hasta_p1(t)
    sorted((t / "corridas").glob("*.json"))[1].write_text("{}", encoding="utf-8")
    assert estado(t, "analizar") == "vencida"


def test_archivo_extrano_en_corridas_no_cae_y_frena_lo_nuevo(t):
    correr(t, "extraer")
    (t / "corridas" / "abc.json").write_text("[]", encoding="utf-8")
    assert estado(t, "extraer") == "vigente"
    with pytest.raises(S.Bloqueado, match="cadena"):
        correr(t, "extraer", "v2")


def test_manifiesto_borrado_rompe_la_cadena(t):
    hasta_p1(t)
    correr(t, "producir")
    sorted((t / "corridas").glob("*.json"))[1].unlink()
    v = S.vigencia(t, LINEA)
    assert v["analizar"]["estado"] == "pendiente"
    assert v["producir"]["estado"] == "vencida"


def test_borrar_un_manifiesto_antiguo_lo_detecta_la_cadena(t):
    correr(t, "extraer", "v1")
    correr(t, "extraer", "v2")
    sorted((t / "corridas").glob("*.json"))[0].unlink()
    assert S.vigencia(t, LINEA)["extraer"]["causas"] == ["manifiesto alterado o borrado"]


def test_con_la_cadena_rota_no_se_registra_mas(t):
    correr(t, "extraer")
    next((t / "corridas").glob("*.json")).write_text("{", encoding="utf-8")
    with pytest.raises(S.Bloqueado, match="cadena"):
        correr(t, "extraer", "v2")


def test_registrar_valida_antes_de_escribir(t):
    with pytest.raises(S.Bloqueado, match="desconocida"):
        S.registrar_corrida(t, LINEA, "inventada", rol="r", origen="script", ejecutor={}, entradas={},
                            salidas=["artefactos/x"], inicio=HOY, fin=HOY)
    assert not list((t / "corridas").glob("*.json"))


def test_origen_humano_solo_por_edicion(t):
    (t / SALIDA["extraer"]).write_text("x", encoding="utf-8")
    with pytest.raises(S.Bloqueado, match="origen"):
        S.registrar_corrida(t, LINEA, "extraer", rol="r", origen="humano", ejecutor={}, entradas={},
                            salidas=[SALIDA["extraer"]], inicio=HOY, fin=HOY)


@pytest.mark.parametrize("ruta", ["../fuera.txt", "/etc/hostname"])
def test_ruta_no_sale_del_trabajo(t, ruta):
    with pytest.raises(S.Bloqueado, match="fuera del trabajo"):
        S.digests(t, [ruta])


def test_escritura_exclusiva_no_pisa(t):
    f = t / "x.json"
    S._escribir(f, b"1", exclusivo=True)
    with pytest.raises(S.Bloqueado):
        S._escribir(f, b"2", exclusivo=True)
    assert f.read_bytes() == b"1"
    assert not list(t.glob("*.tmp"))


# Avisos

def test_cambio_de_prompt_da_aviso_y_no_vence(t):
    hasta_p1(t)
    v = S.vigencia(t, LINEA, {"analizar": {"prompt_sha256": "otro"}})
    assert v["analizar"] == {"estado": "aviso", "causas": ["cambió prompt_sha256"]}
    assert v["producir"]["estado"] == "pendiente"


def test_cambio_de_modelo_da_aviso(t):
    hasta_p1(t)
    assert S.vigencia(t, LINEA, {"analizar": {"modelo": "otro"}})["analizar"]["estado"] == "aviso"
    assert S.vigencia(t, LINEA, {"analizar": {"modelo": "m"}})["analizar"]["estado"] == "vigente"


# Línea

def test_etapas_vienen_de_la_linea(t):
    with pytest.raises(S.Bloqueado, match="desconocida"):
        S.puede_correr(t, LINEA, "voz")


def test_linea_rechaza_dependencia_que_no_va_antes():
    with pytest.raises(S.Bloqueado, match="no va antes"):
        S.validar_linea({"version": "1", "etapas": {"a": {"depende": ["b"]}, "b": {"depende": ["a"]}}})


def test_linea_rechaza_aprueba_fuera_de_dependencias():
    with pytest.raises(S.Bloqueado, match="dependencias"):
        S.validar_linea({"version": "1", "aprobadores": [YO], "etapas": {
            "a": {}, "b": {}, "c": {"depende": ["b"], "puerta": "P", "aprueba": ["a"]}}})


def test_linea_rechaza_puerta_repetida():
    with pytest.raises(S.Bloqueado, match="repetida"):
        S.validar_linea({"version": "1", "aprobadores": [YO], "etapas": {
            "a": {"puerta": "P"}, "b": {"depende": ["a"], "puerta": "P"}}})


def test_linea_con_puertas_exige_aprobadores():
    with pytest.raises(S.Bloqueado, match="aprobadores"):
        S.validar_linea({"version": "1", "etapas": {"a": {"puerta": "P"}}})


def test_digest_de_conjunto_no_depende_del_orden():
    assert S.digest_conjunto({"a": "1", "b": "2"}) == S.digest_conjunto({"b": "2", "a": "1"})
    assert S.digest_conjunto({"a": "1"}) != S.digest_conjunto({"a": "2"})


def test_estado_del_grafo_no_lleva_texto():
    assert set(S.EstadoGrafo.__annotations__) == {
        "trabajo", "corrida", "linea_version", "artefactos", "ronda", "costo_usd", "detenido_por",
        "hallazgos", "extras"}


def test_ultima_constancia_es_sobre_los_digests_de_hoy(t):
    c = hasta_p1(t)
    assert S.ultima_constancia(t, LINEA, "P1") == c["id"]
    correr(t, "analizar", "v2")
    assert S.ultima_constancia(t, LINEA, "P1") is None


def test_puerta_condicional_solo_se_exige_si_se_pidio(t):
    linea = {"version": "1", "aprobadores": [YO], "etapas": {"a": {"puerta": "P", "condicional": True}}}
    S.nuevo(t, "c", linea)
    for pide, esperado in ((False, "vigente"), (True, "por_aprobar")):
        (t / f"artefactos/{pide}.txt").write_text("x", encoding="utf-8")
        S.registrar_corrida(t, linea, "a", rol="r", origen="script", ejecutor={}, entradas={},
                            salidas=[f"artefactos/{pide}.txt"], inicio=HOY, fin=HOY, pide_puerta=pide)
        assert S.vigencia(t, linea)["a"]["estado"] == esperado
