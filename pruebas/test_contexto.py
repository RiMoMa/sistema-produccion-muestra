"""Bloque 1: el paquete de reglas se arma desde la instancia. Sin red y sin gastar."""
import json
import subprocess

import pytest

from motor import contexto as X
from motor import nodos as N
from motor import runtime as R
from motor import state as S
from pruebas.test_verificador import LIMPIO, Producir, claude_guion  # noqa: F401 (fixture)

DECISIONES = """# Decisiones

### D1 · Regla para todo
*1 de octubre de 2026*

Sin guiones largos.

### D2 · Marco al abrir
*2 de octubre de 2026*

**Precisada por D3 (3 de octubre de 2026):** cabe en dos caras.

El marco abre la lección. No confundir con D5.

**Tabla de revisión del corpus:**

| Pieza | Estado |
|---|---|
| L1 | alineada |

### D3 · Marco corto
*3 de octubre de 2026*

Precisa D2. Dos caras como máximo.

### D4 · Anclas de clase
*4 de octubre de 2026*

**Precisada por D2:** nada.

Entre seis y ocho anclas.

### D5 · Vieja
*5 de octubre de 2026*

Ya no rige.

## Pendientes abiertos

- Revisar el tono.
"""

INDICE = """# Índice

| Entrada | Tipos | Por qué |
|---|---|---|
| D1 | todas | Redacción |
| D2 | leccion | Marco |
| D3 | leccion | Marco corto |
| D4 | clase | Anclas |
| D5 | sin-efecto | Vencida |
"""

CLAUDE = """# Instrucciones

## Reglas de contenido

1. El marco abre la lección.

## Cómo pregunto

Una pregunta a la vez.

## Vacía

## Reglas de redacción

- Trato de usted.
"""

TOML = """nombre = "prueba"
decisiones = "contexto/decisiones.md"
indice = "contexto/indice.md"
tipos = ["leccion", "clase"]

[roles.verificador]
archivos = ["contexto/estilo.md"]
secciones = { "CLAUDE.md" = ["Reglas de contenido", "Reglas de redacción"] }

[roles.borrador]
secciones = { "CLAUDE.md" = ["Reglas de redacción"] }
"""


@pytest.fixture
def inst(tmp_path):
    raiz = tmp_path / "instancia"
    (raiz / "contexto").mkdir(parents=True)
    (raiz / "contexto/decisiones.md").write_text(DECISIONES, encoding="utf-8")
    (raiz / "contexto/indice.md").write_text(INDICE, encoding="utf-8")
    (raiz / "contexto/estilo.md").write_text("ESTILO: sin guiones largos.\n", encoding="utf-8")
    (raiz / "CLAUDE.md").write_text(CLAUDE, encoding="utf-8")
    (raiz / "instancia.toml").write_text(TOML, encoding="utf-8")
    return raiz


def editar(raiz, archivo, viejo, nuevo):
    p = raiz / archivo
    texto = p.read_text(encoding="utf-8")
    assert viejo in texto
    p.write_text(texto.replace(viejo, nuevo, 1), encoding="utf-8")


# El manifiesto de la instancia

def test_lee_la_instancia(inst):
    i = X.leer_instancia(inst)
    assert i.nombre == "prueba" and i.tipos == {"leccion", "clase", "todas", "sin-efecto"}
    assert set(i.roles) == {"verificador", "borrador"}
    assert i.roles["borrador"].decisiones and i.roles["verificador"].archivos == ("contexto/estilo.md",)


@pytest.mark.parametrize("viejo, nuevo, error", [
    ('decisiones = "contexto/decisiones.md"\n', "", "falta decisiones"),
    ('"contexto/estilo.md"', '"../fuera.md"', "dentro de la instancia"),
    ('"contexto/estilo.md"', '"/etc/hostname"', "dentro de la instancia"),
    ('"contexto/estilo.md"', '"contexto/no-existe.md"', "no existe"),
    ('tipos = ["leccion", "clase"]', 'tipos = ["leccion", "todas"]', "los pone el motor"),
    ('tipos = ["leccion", "clase"]', "tipos = []", "lista de nombres"),
    ('["Reglas de redacción"] }\n', '[] }\n', "lista de títulos"),
    ("nombre =", "nombre = = ", "no se puede leer"),
])
def test_manifiesto_mal_escrito(inst, viejo, nuevo, error):
    editar(inst, "instancia.toml", viejo, nuevo)
    with pytest.raises(S.Bloqueado, match=error):
        X.leer_instancia(inst)


def test_sin_roles_no_hay_instancia(inst):
    (inst / "instancia.toml").write_text(TOML.split("[roles")[0], encoding="utf-8")
    with pytest.raises(S.Bloqueado, match="ningún rol"):
        X.leer_instancia(inst)


def test_sin_manifiesto(tmp_path):
    with pytest.raises(S.Bloqueado, match="instancia.toml"):
        X.leer_instancia(tmp_path)


def test_rol_vacio_no_se_arma(inst):
    editar(inst, "instancia.toml", '[roles.borrador]\n', '[roles.borrador]\ndecisiones = false\n')
    editar(inst, "instancia.toml", 'secciones = { "CLAUDE.md" = ["Reglas de redacción"] }\n', "")
    with pytest.raises(S.Bloqueado, match="no recibe nada"):
        X.armar(X.leer_instancia(inst), ["leccion"])


# El paquete

def test_paquete_por_tipo_con_cierre_en_una_direccion(inst):
    i = X.leer_instancia(inst)
    ents = X.entradas(DECISIONES)
    _, _, filas = X.comprobar(DECISIONES, INDICE, i.tipos)
    orden, base, cuerpo = X.paquete(ents, filas, DECISIONES, ["leccion"])
    assert base == {"D1", "D2", "D3"} and orden == ["D1", "D2", "D3"]
    # D4 nombra a D2 en su cabecera, pero D2 no lo arrastra; y D4 es de clase.
    assert "Anclas" not in cuerpo and "Ya no rige" not in cuerpo
    assert cuerpo.endswith("## Pendientes abiertos\n\n- Revisar el tono.\n")


def test_cierre_solo_suma_lo_que_comparte_tipo(inst):
    i = X.leer_instancia(inst)
    _, ents, filas = X.comprobar(DECISIONES, INDICE, i.tipos)
    orden, base, _ = X.paquete(ents, filas, DECISIONES, ["clase"])
    assert base == {"D1", "D4"} and orden == ["D1", "D4"]  # D4 nombra a D2, que es de lección


def test_cierre_no_suma_otro_tipo(inst):
    editar(inst, "contexto/indice.md", "| D3 | leccion |", "| D3 | clase |")
    i = X.leer_instancia(inst)
    texto = (inst / "contexto/decisiones.md").read_text(encoding="utf-8")
    _, ents, filas = X.comprobar(texto, (inst / "contexto/indice.md").read_text(encoding="utf-8"), i.tipos)
    assert X.paquete(ents, filas, texto, ["leccion"])[0] == ["D1", "D2"]
    editar(inst, "contexto/indice.md", "| D3 | clase |", "| D3 | clase, leccion |")
    _, ents, filas = X.comprobar(texto, (inst / "contexto/indice.md").read_text(encoding="utf-8"), i.tipos)
    orden, base, _ = X.paquete(ents, filas, texto, ["clase"])
    assert "D2" not in base and "D2" not in orden  # D3 precisa a D2, pero D2 es de lección


def test_remision_arrastra(inst):
    """D2 nombra a D3 en su cabecera: si D3 entra solo por remisión, entra."""
    editar(inst, "contexto/indice.md", "| D3 | leccion |", "| D3 | sin-efecto |")
    i = X.leer_instancia(inst)
    texto = (inst / "contexto/decisiones.md").read_text(encoding="utf-8")
    _, ents, filas = X.comprobar(texto, (inst / "contexto/indice.md").read_text(encoding="utf-8"), i.tipos)
    orden, base, _ = X.paquete(ents, filas, texto, ["leccion"])
    assert "D3" not in base and orden == ["D1", "D2", "D3"]


def test_mencion_en_el_cuerpo_no_arrastra(inst):
    """D2 nombra a D5 en su cuerpo, no en su cabecera: D5 (sin-efecto) no entra al paquete de lección."""
    i = X.leer_instancia(inst)
    _, ents, filas = X.comprobar(DECISIONES, INDICE, i.tipos)
    assert "D5" not in X.paquete(ents, filas, DECISIONES, ["leccion"])[0]


def test_cierre_no_va_hacia_atras(inst):
    """D4 nombra a D2 en su cabecera; D2 no nombra a D4. Aunque D4 sea sin-efecto, D2 no lo arrastra."""
    editar(inst, "contexto/indice.md", "| D4 | clase |", "| D4 | sin-efecto |")
    i = X.leer_instancia(inst)
    _, ents, filas = X.comprobar(DECISIONES, (inst / "contexto/indice.md").read_text(encoding="utf-8"), i.tipos)
    assert X.paquete(ents, filas, DECISIONES, ["leccion"])[0] == ["D1", "D2", "D3"]


def test_la_tabla_de_corpus_no_entra():
    assert "alineada" not in X.entradas(DECISIONES)["D2"]
    assert "El marco abre la lección." in X.entradas(DECISIONES)["D2"]


def test_armar_reparte_por_rol(inst):
    p = X.armar(X.leer_instancia(inst), ["leccion"])
    v, b = p["verificador"], p["borrador"]
    assert v.startswith("## contexto/decisiones.md · leccion\n\n### D1")
    assert "## contexto/estilo.md\n\nESTILO" in v
    assert "## CLAUDE.md · Reglas de contenido\n\n## Reglas de contenido\n\n1. El marco" in v
    assert "## CLAUDE.md · Reglas de redacción" in v
    assert "Una pregunta a la vez" not in v  # instrucciones de sesión: no entran
    assert "ESTILO" not in b and "Reglas de contenido" not in b and "### D2" in b


def test_seccion():
    assert X.seccion(CLAUDE, "Reglas de redacción") == "## Reglas de redacción\n\n- Trato de usted.\n"
    assert X.seccion(CLAUDE, "Cómo pregunto") == "## Cómo pregunto\n\nUna pregunta a la vez.\n"
    with pytest.raises(S.Bloqueado, match="no existe"):
        X.seccion(CLAUDE, "Reglas de contenid")
    with pytest.raises(S.Bloqueado, match="vacía"):
        X.seccion(CLAUDE, "Vacía")


def test_seccion_que_falta_para_el_paquete(inst):
    editar(inst, "CLAUDE.md", "## Reglas de redacción", "## Redacción")
    with pytest.raises(S.Bloqueado, match="CLAUDE.md: no existe la sección «Reglas de redacción»"):
        X.armar(X.leer_instancia(inst), ["leccion"])


@pytest.mark.parametrize("tipos, error", [([], "al menos un tipo"), (["deck"], "no declara"),
                                          (["todas"], "no declara"), (["sin-efecto"], "no declara")])
def test_tipos_pedidos(inst, tipos, error):
    with pytest.raises(S.Bloqueado, match=error):
        X.armar(X.leer_instancia(inst), tipos)


# El índice

@pytest.mark.parametrize("viejo, nuevo, falla", [
    ("| D5 | sin-efecto | Vencida |\n", "", "D5: sin fila"),
    ("| D4 | clase |", "| D4 | taller |", "tipo desconocido: taller"),
    ("| D4 | clase |", "| D4 |  |", "D4 sin tipos"),
    ("| D5 | sin-efecto |", "| D5 | sin-efecto, clase |", "sin-efecto y lleva otros"),
    ("| D5 | sin-efecto | Vencida |\n", "| D5 | sin-efecto | Vencida |\n| D5 | clase | Otra |\n", "D5: 2 filas"),
    ("| D5 | sin-efecto | Vencida |\n", "| D5 | sin-efecto | Vencida |\n| D9 | clase | Huérfana |\n", "D9: fila sin entrada"),
    ("| D5 | sin-efecto | Vencida |\n", "| D5 | sin-efecto | Vencida |\n\nNota suelta.\n", "texto fuera de la tabla"),
])
def test_indice_con_fallas_no_arma(inst, viejo, nuevo, falla):
    editar(inst, "contexto/indice.md", viejo, nuevo)
    with pytest.raises(S.Bloqueado, match="el índice tiene") as e:
        X.armar(X.leer_instancia(inst), ["leccion"])
    assert falla in str(e.value)


def test_indice_limpio():
    i_tipos = {"leccion", "clase", "todas", "sin-efecto"}
    assert X.comprobar(DECISIONES, INDICE, i_tipos)[0] == []


# El nodo en la línea

YO = "Persona Aprobadora"
LINEA = {"version": "1", "aprobadores": [YO], "etapas": {
    "contexto": {},
    "producir": {},
    "verificar": {"depende": ["contexto", "producir"], "puerta": "PJ", "condicional": True},
}}


@pytest.fixture
def t(tmp_path):
    c = tmp_path / "trabajo"
    c.mkdir()
    for a in (["init", "-q"], ["config", "user.name", "Prueba"], ["config", "user.email", "p@ejemplo.invalid"]):
        subprocess.run(["git", *a], cwd=c, check=True)
    S.nuevo(c, "t", LINEA)
    return c


def linea_nodos(inst):
    return {"contexto": N.contexto(inst, ["leccion"]), "producir": Producir().nodo(),
            "verificar": N.verificador([("claude", "sonnet")], ())}


def test_nodo_rechaza_tipos_al_construir(inst):
    with pytest.raises(S.Bloqueado, match="no declara"):
        N.contexto(inst, ["deck"])


def test_verificador_recibe_solo_su_paquete_y_primero(t, inst, claude_guion):
    poner, pedidos = claude_guion
    poner(LIMPIO)
    assert R.correr(t, LINEA, linea_nodos(inst))["estado"] == "terminado"
    texto = pedidos()[0]["texto"]
    assert texto.startswith("## artefactos/contexto/") and "paquete-verificador.md" in texto.split("\n", 1)[0]
    assert "paquete-borrador.md" not in texto
    assert texto.index("ESTILO") < texto.index("pieza versión 1")
    m = S.ultimo_manifiesto(t, "contexto")
    assert m["origen"] == "script" and m["ejecutor"]["tipos"] == ["leccion"]
    assert sorted(x.rsplit("/", 1)[1] for x in m["salidas"]) == ["paquete-borrador.md", "paquete-verificador.md"]


def test_indice_roto_detiene_la_linea(t, inst, claude_guion):
    poner, _ = claude_guion
    poner(LIMPIO)
    editar(inst, "contexto/indice.md", "| D5 | sin-efecto | Vencida |\n", "")
    with pytest.raises(S.Bloqueado, match="D5: sin fila"):
        R.correr(t, LINEA, linea_nodos(inst))
    assert not (t.parent / "pedidos.jsonl").exists()


@pytest.mark.parametrize("archivo, viejo, nuevo", [
    ("contexto/estilo.md", "ESTILO", "ESTILO NUEVO"),
    ("contexto/decisiones.md", "Sin guiones largos.", "Sin guiones largos ni cortos."),
    ("contexto/indice.md", "| D4 | clase |", "| D4 | clase, leccion |"),
    ("CLAUDE.md", "Trato de usted.", "Trato de tú."),
    ("instancia.toml", 'nombre = "prueba"', 'nombre = "otra"'),
])
def test_cambio_de_reglas_da_aviso_y_no_rehace(t, inst, claude_guion, archivo, viejo, nuevo):
    poner, pedidos = claude_guion
    poner(LIMPIO)
    primera = R.correr(t, LINEA, linea_nodos(inst))
    assert primera["estado"] == "terminado" and "avisos" not in primera
    antes = S.ultimo_manifiesto(t, "contexto")["secuencia"]
    editar(inst, archivo, viejo, nuevo)
    r = R.correr(t, LINEA, linea_nodos(inst))
    assert r["estado"] == "terminado" and r["avisos"] == {"contexto": ["cambió reglas_sha256"]}
    assert S.ultimo_manifiesto(t, "contexto")["secuencia"] == antes and len(pedidos()) == 1


def test_sin_cambio_no_avisa(t, inst, claude_guion):
    poner, _ = claude_guion
    poner(LIMPIO)
    R.correr(t, LINEA, linea_nodos(inst))
    assert "avisos" not in R.correr(t, LINEA, linea_nodos(inst))


def test_cambio_de_prompt_del_verificador_avisa(t, inst, claude_guion, tmp_path):
    poner, _ = claude_guion
    poner(LIMPIO)
    R.correr(t, LINEA, linea_nodos(inst))
    otro = tmp_path / "verificador.md"
    otro.write_text("Eres el verificador, versión 2.\n", encoding="utf-8")
    n = linea_nodos(inst)
    n["verificar"] = N.verificador([("claude", "sonnet")], (), agente=otro)
    assert R.correr(t, LINEA, n)["avisos"] == {"verificar": ["cambió prompt_sha256"]}


def test_cambio_de_modelo_avisa(t, inst, claude_guion):
    poner, _ = claude_guion
    poner(LIMPIO)
    R.correr(t, LINEA, linea_nodos(inst))
    n = linea_nodos(inst)
    n["verificar"] = N.verificador([("claude", "opus")], ())
    assert R.correr(t, LINEA, n)["avisos"] == {"verificar": ["cambió modelo"]}


def test_entradas_del_rol():
    e = ["a/paquete-borrador.md", "b/pieza.md", "a/paquete-verificador.md", "c/informe.json"]
    assert N.entradas_del_rol("verificador", e) == ["a/paquete-verificador.md", "b/pieza.md", "c/informe.json"]
    assert N.entradas_del_rol("otro", e) == ["b/pieza.md", "c/informe.json"]


def test_plantilla_de_instancia_se_lee():
    """La plantilla que copia una instancia nueva es TOML válido y declara los dos roles que el motor usa."""
    import tomllib
    from pathlib import Path
    d = tomllib.loads((Path(__file__).resolve().parents[1] / "plantillas/instancia/instancia.toml").read_text())
    assert set(d["roles"]) == {"verificador", "borrador"} and not set(d["tipos"]) & X.MECANICOS
