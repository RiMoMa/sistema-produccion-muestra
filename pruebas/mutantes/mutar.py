"""Rompe cada control de state.py y runtime.py en una copia y exige que alguna prueba falle.

Uso: .venv/bin/python pruebas/mutantes/mutar.py. Sale con error si un mutante sobrevive.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TMP = Path(tempfile.mkdtemp()) / "copia"
MUTANTES = [
    ("aprobador no se exige", 'if por not in linea.get("aprobadores", []):', "if False:"),
    ("por vuelve a tener valor por defecto", 'puerta: str, por: str, fecha: str, decision', 'puerta: str, por: str = "Persona Aprobadora", fecha: str = "", decision'),
    ("aprobar acepta etapa vencida", 'if v["estado"] in ("pendiente", "vencida"):', 'if v["estado"] in ("pendiente",):'),
    ("aprobar acepta etapa pendiente", 'if v["estado"] in ("pendiente", "vencida"):', 'if v["estado"] in ("vencida",):'),
    ("devolver sin observación", 'if decision == "devuelta" and not observacion.strip():', "if False:"),
    ("salida cambiada no se detecta", 'elif sha256_archivo(f) != digest:', "elif False:"),
    ("archivo faltante no se detecta", 'if not f.exists():', "if False:"),
    ("vencimiento no es transitivo", 'if estados[previa]["estado"] not in SIGUEN:\n                causas', 'if False:\n                causas'),
    ("constancia no compara digest", 'if _digest_constancia(c) == actual]', 'if True]'),
    ("constancia de otro trabajo vale", 'and p.get("trabajo") == trabajo and', 'and'),
    ("constancia alterada vale", 'c.get("sello") == _sello(_sin_archivo(c))\n', 'True\n'),
    ("gana la primera decisión", 'return hechas[-1]["predicate"]', 'return hechas[0]["predicate"]'),
    ("id con ruta se acepta", 'if "/" in id_ or "\\\\" in id_ or ".." in id_:', "if False:"),
    ("sello del manifiesto no se comprueba", 'or m.get("sello") != _sello(_sin_archivo(m))', ""),
    ("cadena no comprueba previo ni secuencia", 'm["secuencia"] != esperado or m.get("previo") != previo\n', 'False\n'),
    ("se registra con cadena rota", 'if _rotura(todos) is not None:\n        raise', 'if False:\n        raise'),
    ("manifiesto roto no vence", 'if rota is not None and m["secuencia"] >= rota:\n            causas', 'if False:\n            causas'),
    ("escritura exclusiva pisa", 'if exclusivo:', "if False:"),
    ("origen humano se acepta", 'ORIGENES = {"modelo", "script"}', 'ORIGENES = {"modelo", "script", "humano"}'),
    ("ruta fuera del trabajo pasa", 'if p.is_absolute() or ".." in p.parts or not final.is_relative_to(carpeta.resolve()):', "if False:"),
    ("puerta no bloquea", 'if decision is None:', "if False:"),
    ("aviso vence en vez de avisar", 'estados[etapa] = {"estado": "aviso" if avisos else "vigente", "causas": avisos}', 'estados[etapa] = {"estado": "vencida" if avisos else "vigente", "causas": avisos}'),
    ("rechazo no detiene", 'if e["estado"] == "rechazada":\n            raise', 'if False:\n            raise'),
    ("puerta ignora aprueba", 'for e in [*linea["etapas"][etapa].get("aprueba", []), etapa]:', "for e in [etapa]:"),
    ("edición no exige aprobador", '_etapa(linea, etapa)\n    _exigir_aprobador(linea, por)\n    previo', '_etapa(linea, etapa)\n    previo'),
    ("rehacer en otra ruta no vence", 'if m["entradas"].get(ruta) != digest:', "if False:"),
]
RUNTIME = [
    ("avisos no se informan", 'extra = {"avisos": avisos} if avisos else {}', "extra = {}"),
    ("huella sin prompt", 'h = {"prompt_sha256": n.prompt_sha256, "reglas_sha256": n.reglas_sha256}', 'h = {"reglas_sha256": n.reglas_sha256}'),
    ("huella sin modelo", 'if n.ejecutor.get("modelo"):\n            h["modelo"]', 'if False:\n            h["modelo"]'),
    ("commit no se exige", 'if not _en_git(carpeta, f"constancias/{id_}.json"):', "if False:"),
    ("no salta lo vigente", 'if not extras and S.vigencia(carpeta, linea)[etapa]["estado"] in SALTA:', "if False:"),
    ("nodo corre sin sus previas", '        S.puede_correr(carpeta, linea, etapa)\n', ""),
    ("nombre de salida no se valida", 'if "/" in nombre or "\\\\" in nombre or nombre in ("", ".", ".."):', "if False:"),
    ("nodo sin salidas pasa", 'if not archivos:', "if False:"),
    ("ciclo sin límite", ' and S.rondas(carpeta, etapa) < ciclo["max_rondas"]', ""),
    ("reanudar avanza sin decisión", 'raise S.Bloqueado(f"{respuesta} no decide sobre lo que hay hoy en {puerta}")', 'return {"detenido_por": None}'),
    ("reanudar no lee la constancia", '        S.leer_constancia(carpeta, puerta, respuesta)\n', ""),
    ("puerta acepta etapa vencida", 'if estado["estado"] not in (*S.SIGUEN, "por_aprobar", "devuelta"):', "if False:"),
    ("devolución no exige commit", '        if estado["estado"] == "devuelta":\n            _exigir_commit(carpeta, id_)\n', '        if estado["estado"] == "devuelta":\n'),
    ("observación no entra como entrada", 'S.digests(carpeta, [*rutas, *extras])', "S.digests(carpeta, rutas)"),
    ("caída no se anota", '        _anotar_llamada(carpeta, {**base, "estado": f"error: {x}"[:300]})\n', ""),
    ("costo no se acumula", '"costo_usd": est["costo_usd"] + costo', '"costo_usd": costo'),
    ("corrección sin su pieza anterior", '[*(anterior["salidas"] if anterior else []), *m["salidas"]]', 'list(m["salidas"])'),
    ("pieza anterior después del informe", '[*(anterior["salidas"] if anterior else []), *m["salidas"]]', '[*m["salidas"], *(anterior["salidas"] if anterior else [])]'),
    ("corridas pisan artefactos", 'base = f"artefactos/{etapa}/{S.proxima_secuencia(carpeta):06d}"', 'base = f"artefactos/{etapa}"'),
]
REVISAR = [
    ("falla_sin ignora la salida", 'if r.search(l) and not r2.search(l)]', "if r.search(l)]"),
    ("aviso_sin al revés", 'if not r2.search(vecinas):', "if r2.search(vecinas):"),
    ("vecinas no se miran", 'lineas[max(i - 1, 0):i + 2]', "lineas[i:i + 1]"),
    ("aviso_cifras ignora la cita", 'if con and not any(r2.search(l) for l in lineas):', "if con:"),
    ("ámbito no se respeta", 'if ambito and not ambito.search(ruta):', "if False:"),
    ("todo es falla", '"falla" if tipo.startswith("falla") else "aviso"', '"falla"'),
    ("nada es falla", '"falla" if tipo.startswith("falla") else "aviso"', '"aviso"'),
    ("comando siempre sale limpio", 'if fallas == 0:', "if True:"),
    ("distingue mayúsculas", 'r = re.compile(patron, re.I | re.M)', "r = re.compile(patron, re.M)"),
    ("html incluye claves", 'if len(c.split()) >= 3:', "if True:"),
    ("html incluye estilos", 't = re.sub(r"(?is)<(script|style)[^>]*>.*?</\\1>", " ", t)\n', ""),
    ("tipo desconocido pasa", 'if tipo not in ("falla", "aviso", "falla_sin", "aviso_sin", "aviso_cerca", "aviso_cifras"):', "if False:"),
    ("patrón2 faltante pasa", 'and r2 is None:', "and False:"),
]
NODOS = [
    ("fallas no devuelven la pieza", 'hallazgos=fallas)', "hallazgos=0)"),
    ("avisos devuelven la pieza", 'if h["clase"] == "falla")', "if True)"),
    ("revisa cualquier archivo", 'if ruta.lower().endswith(REVISABLES):', "if True:"),
    ("reglas sin huella", 'reglas_sha256=S.sha256_archivo(reglas)', 'reglas_sha256=""'),
]
SANEO = [
    ("correo no se detecta", '("correo", re.compile(r"[\\w.+-]+@[\\w-]+\\.[\\w.-]+")),\n', ""),
    ("documento no se detecta", 'c[eé]dula|T\\.?\\s?I\\.?|documento)\\D{0,15}', 'c[eé]dula_no|T_no|documento_no)\\D{0,15}'),
    ("teléfono acepta cualquier cifra", '(?<![\\d.])(?:\\+?57[\\s-]?)?3\\d{2}', '\\d{3}'),
    ("términos privados no se miran", 'if any(t.lower() in minusculas for t in terminos or []):', "if False:"),
    ("distingue mayúsculas en términos", 'minusculas = texto.lower()', "minusculas = texto"),
    ("exigir_limpio no detiene", '        if hallados:\n', "        if False:\n"),
    ("el error repite el dato", "({', '.join(hallados)})", "({texto})"),
]
MODELOS = [
    ("saneo no se aplica", 'saneo.exigir_limpio({"el sistema": p.sistema, "el encargo": p.texto}, terminos)', "pass"),
    ("el sistema no se revisa", '{"el sistema": p.sistema, "el encargo": p.texto}', '{"el encargo": p.texto}'),
    ("local también se filtra", 'if NIVELES[via] != "local":', "if True:"),
    ("imagen sale a un externo", 'if p.imagenes:\n            raise Bloqueado', 'if False:\n            raise Bloqueado'),
    ("clave con permisos abiertos", 'not in (0o600, 0o400):', "not in (0o600, 0o400, 0o644):"),
    ("clave vacía pasa", 'if not clave:', "if False:"),
    ("clave aparece en el error", 'str(x).replace(secreto, "***") if secreto else str(x)', "str(x)"),
    ("claude acepta cualquier herramienta", 'extra = set(p.herramientas) - HERRAMIENTAS_CLAUDE', "extra = set()"),
    ("claude hereda la API key", 'if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN")}', "}"),
    ("claude no concede las herramientas", 'cmd += ["--allowedTools", ",".join(p.herramientas)]', "pass"),
    ("claude concede permisos sin herramientas", '        if p.herramientas:  # sin permiso', '        if True:  # sin permiso'),
    ("respuesta cortada escapa", 'ValueError, http.client.HTTPException, OSError) as x:', "ValueError) as x:"),
    ("flujo sin [DONE] se acepta", '    if not completo:\n        raise ErrorModelo("respuesta cortada', '    if False:\n        raise ErrorModelo("respuesta cortada'),
    ("keep-alive rompe el flujo", 'if not linea.startswith("data:"):', "if not linea:"),
    ("uso del flujo se pierde", 'uso = e.get("usage") or uso', "uso = uso"),
    ("deepseek sin streaming", '"stream": True, "stream_options": {"include_usage": True}', '"stream": False'),
    ("claude carga configuración", '"--setting-sources", "local", ', ""),
    ("ollama acepta cloud", 'if ":cloud" in p.modelo:', "if False:"),
    ("ollama acepta otra máquina", 'if urlparse(base).hostname not in LOCALES:', "if False:"),
    ("opencode acepta otros modelos", 'if not p.modelo.startswith("opencode/"):', "if False:"),
    ("agente de opencode con permisos", '\\"*\\": deny', '\\"*\\": allow'),
    ("sin tope de tiempo", 'timeout=p.timeout_s, stdin=', "stdin="),
    ("respuesta vacía pasa", 'if not r.texto.strip():', "if False:"),
    ("salida sin tope", 'if len(r.texto.encode()) > p.max_bytes:', "if False:"),
    ("respaldo no valida", 'errores = validar(r.texto) if validar else []', "errores = []"),
    ("dato personal cae a la siguiente ruta", 'except ErrorModelo as x:', "except (ErrorModelo, Bloqueado) as x:"),
    ("costo ignora la caché", 'cache * p["cache"]', 'cache * p["entrada"]'),
    ("deepseek no pide JSON", 'if p.json:\n        cuerpo["response_format"]', 'if False:\n        cuerpo["response_format"]'),
]
NODOS += [
    ("niveles no se revisan", 'if M.NIVELES[via] not in niveles:', "if False:"),
    ("gratuitos encendidos por defecto", 'niveles: tuple[str, ...] = ("pago", "local")', 'niveles: tuple[str, ...] = ("pago", "local", "libre")'),
    ("lo variable va primero", 'texto=fijo + variable', "texto=variable + fijo"),
    ("encabezado del rol se envía", 'if s.startswith("---\\n"):', "if False:"),
    ("prompt sin huella", 'prompt_sha256=S.sha256_bytes(sistema.encode())', 'prompt_sha256=""'),
    ("contar se ignora", 'hallazgos, juicios = contar(r.texto) if contar else (0, 0)', "hallazgos, juicios = 0, 0"),
    # Bloque 1
    ("paquete de otro rol se envía", "resto = [r for r in entradas if not PAQUETE.match(Path(r).name)]", "resto = list(entradas)"),
    ("paquete no va primero", "return [*propio, *resto]", "return [*resto, *propio]"),
    ("verificador corre sin paquete", 'if not reglas and not any(Path(r).name == "paquete-verificador.md" for r in ctx.entradas):', "if False:"),
    ("modelo ignora el reparto", "for ruta in entradas_del_rol(rol, ctx.entradas))", "for ruta in ctx.entradas)"),
    ("contexto sin huella", "reglas_sha256=S.sha256_bytes(huella.encode()))", 'reglas_sha256="")'),
    ("contexto no valida tipos al construir", "    X.validar_tipos(inst, tipos)\n    huella", "    huella"),
    # Bloque 15
    ("verificador sin validar", 'validar=validar_informe, contar', "validar=None, contar"),
    ("verificador sin contar", 'contar=contar_informe, terminos', "contar=None, terminos"),
    ("verificador admite local", 'niveles=("pago",), json_salida', 'niveles=("pago", "local", "libre"), json_salida'),
    ("cerca no se quita", '    if s.startswith("```"):\n', "    if False:\n"),
    ("clase no se valida", 'if h.get("clase") not in CLASES:', "if False:"),
    ("gravedad no se valida", 'if h.get("gravedad") not in GRAVEDADES:', "if False:"),
    ("R sin regla pasa", 'if h.get("clase") == "R" and not', 'if False and not'),
    ("J sin decidir pasa", 'if h.get("clase") == "J" and not', 'if False and not'),
    ("hallazgo sin qué pasa", 'if not str(h.get("que", "")).strip():', "if False:"),
    ("informe sin lista pasa", 'or not isinstance(doc.get("hallazgos"), list):', ":"),
    ("J devuelve la pieza", 'return sum(1 for h in hs if h["clase"] in ("M", "R")), sum', "return sum(1 for h in hs), sum"),
    ("tipo1 no se busca", '        if anterior:\n            tipo1', '        if False:\n            tipo1'),
    ("tipo1 sigue el ciclo", 'r.hallazgos, r.juicios = 0, r.juicios + len(tipo1)', "r.juicios = r.juicios + len(tipo1)"),
    ("tipo1 no va a la puerta", 'r.hallazgos, r.juicios = 0, r.juicios + len(tipo1)', "r.hallazgos = 0"),
    ("tipo1 compara solo la regla", 'h.get("regla", "")).lower().split()), " ".join(str(h.get("donde", "")).lower().split())', 'h.get("regla", "")).lower().split()), ""'),
    ("tipo1 compara solo el lugar", ' " ".join(str(h.get("regla", "")).lower().split()), " ".join(str(h.get("donde"', ' "", " ".join(str(h.get("donde"'),
    ("tipo1 distingue espacios y mayúsculas", 'str(h.get("donde", "")).lower().split())', 'str(h.get("donde", "")).split())'),
    ("tipo1 incluye J", 'for h in leer_informe(anterior)["hallazgos"] if h["clase"] in ("M", "R")}', 'for h in leer_informe(anterior)["hallazgos"]}'),
    # Bloque 3
    ("escritor admite otra vía", 'if via != "deepseek":', "if False:"),
    ("marcas no cuentan", 'return 0, len(MARCAS.findall(BLOQUES.sub("", texto)))', "return 0, 0"),
    ("marcas devuelven la pieza", 'return 0, len(MARCAS.findall(BLOQUES.sub("", texto)))', "return len(MARCAS.findall(texto)), 0"),
    ("marcas distinguen mayúsculas", 'PENDIENTE)\\b[^\\]]*\\]", re.I)', 'PENDIENTE)\\b[^\\]]*\\]")'),
    ("marcas en prompts cuentan", 'MARCAS.findall(BLOQUES.sub("", texto))', "MARCAS.findall(texto)"),
    ("escritor sin contar marcas", 'contar=contar_marcas, terminos', "contar=None, terminos"),
    ("entrada sin huella", 'reglas_sha256=S.sha256_archivo(ruta))', 'reglas_sha256="")'),
    # Bloque 16
    ("fuentes admite otra vía", 'if via != "claude":', "if False:"),
    ("fuentes sin web", 'herramientas=HERRAMIENTAS_WEB, validar', "herramientas=(), validar"),
    ("fuentes sin validar", 'validar=validar_fuentes,', "validar=None,"),
    ("fuentes sin contar", 'contar=contar_fuentes, terminos', "contar=None, terminos"),
    ("no verificable no devuelve", 'len(doc["corregidas"]) + len(doc["no_verificables"]), 0', 'len(doc["corregidas"]), 0'),
    ("corregida no devuelve", 'len(doc["corregidas"]) + len(doc["no_verificables"]), 0', 'len(doc["no_verificables"]), 0'),
    ("filtro trae todo", 'if l.startswith("|") and referencias(l) & citadas]', 'if l.startswith("|")]'),
    ("filtro trae prosa", 'if l.startswith("|") and referencias(l) & citadas]', "if referencias(l) & citadas]"),
    ("referencias distinguen mayúsculas", 'x.rstrip(".,;:").lower()', 'x.rstrip(".,;:")'),
    ("referencias con puntuación final", 'x.rstrip(".,;:").lower()', "x.lower()"),
    ("confirmada sin URL pasa", 'if k != "no_verificables" and not URL.fullmatch', "if False and not URL.fullmatch"),
    ("fecha de apertura no se exige", 'if not FECHA.match(str(x.get("abierta_el", ""))):', "if False:"),
    ("fila sin forma pasa", 'if fila and not (fila.startswith("|") and fila.endswith("|")):', "if False:"),
    ("corregida incompleta pasa", 'if k == "corregidas" and not all(', 'if False and not all('),
    ("no verificable sin por qué", 'if not str(x.get("por_que", "")).strip():', "if False:"),
    ("recomendación libre", 'if x.get("recomendacion") not in RECOMENDACIONES:', "if False:"),
    ("informe sin las tres listas", 'or not all(isinstance(doc.get(k), list) for k in listas):', ":"),
    ("anexar duplica", 'if fila and fila not in ya and fila not in nuevas:', "if fila:"),
    ("anexar sin informe", 'if len(informes) != 1:', "if False:"),
    ("anexar no escribe", '            S._escribir(registro,', "            pass or (registro,"),
    ("filtro sin huella del registro", 'reglas_sha256=S.sha256_archivo(registro))', 'reglas_sha256="")'),
]
CONTEXTO = [
    # Bloque 1
    ("la instancia declara todas", "if set(tipos) & MECANICOS:", "if False:"),
    ("ruta fuera de la instancia pasa", 'if p.is_absolute() or ".." in p.parts:', "if False:"),
    ("archivo inexistente pasa", "if not (raiz / p).is_file():", "if False:"),
    ("sin roles pasa", "if not roles:", "if False:"),
    ("títulos vacíos pasan", "if not isinstance(titulos, list) or not titulos:", "if not isinstance(titulos, list):"),
    ("índice con fallas arma", '    if fallas:\n        raise S.Bloqueado(f"el índice', '    if False:\n        raise S.Bloqueado(f"el índice'),
    ("entrada sin fila pasa", 'if k not in filas:\n            fallas', 'if False:\n            fallas'),
    ("fila huérfana pasa", 'if k not in ents:\n            fallas', 'if False:\n            fallas'),
    ("fila duplicada pasa", "if len(apar) > 1:", "if False:"),
    ("fila sin tipos pasa", "if not tipos:\n                fallas", "if False:\n                fallas"),
    ("tipo desconocido pasa", "if t not in vocabulario:", "if False:"),
    ("sin-efecto con otros pasa", 'if "sin-efecto" in tipos and len(tipos) > 1:', "if False:"),
    ("texto suelto pasa", 'fallas = [f"l. {n}: texto fuera de la tabla" for n in sueltas]', "fallas = []"),
    ("tabla de corpus entra", "res[m.group(1)] = cuerpo[:c.start()] if c else cuerpo", "res[m.group(1)] = cuerpo"),
    ("remisión no enlaza", "if not REMISION.search(linea):\n                continue", "if False:\n                continue"),
    ("cierre en dos direcciones", "                    g[k].add(otro)", "                    g[k].add(otro)\n                    g[otro].add(k)"),
    ("cierre ignora el tipo", 'if otro not in vistos and tipos_otro & (quiere | {"sin-efecto"}):', "if otro not in vistos:"),
    ("sin todas", 'quiere = set(pedidos) | {"todas"}', "quiere = set(pedidos)"),
    ("sin pendientes", '+ "\\n" + pendientes(texto)', '+ "\\n"'),
    ("sección inexistente pasa", "    if not m:\n        raise S.Bloqueado(f\"no existe", "    if False:\n        raise S.Bloqueado(f\"no existe"),
    ("sección vacía pasa", "if not cuerpo[m.end() - m.start():].strip():", "if False:"),
    ("sección sin corte", "cuerpo = texto[m.start():m.end() + sig.start()] if sig else texto[m.start():]", "cuerpo = texto[m.start():]"),
    ("tipos vacíos pasan", "    if not tipos:\n        raise S.Bloqueado(\"el paquete", "    if False:\n        raise S.Bloqueado(\"el paquete"),
    ("pide todas a mano", "malos = [t for t in tipos if t not in inst.tipos or t in MECANICOS]", "malos = [t for t in tipos if t not in inst.tipos]"),
    ("rol vacío pasa", "if not partes:", "if False:"),
    ("rol sin decisiones las recibe", "if rol.decisiones:", "if True:"),
    ("manifiesto fuera de la huella", "rutas = [MANIFIESTO, self.decisiones, self.indice]", "rutas = [self.decisiones, self.indice]"),
    ("secciones fuera de la huella", "rutas += [*r.archivos, *r.secciones]", "rutas += [*r.archivos]"),
]
MEDIR = [
    ("edición humana suma", 'if m.get("corrupto") or m.get("origen") == "humano":', 'if m.get("corrupto"):'),
    ("equivalente suma al costo", 'g["costo_usd"] += m.get("costo_usd") or 0.0', 'g["costo_usd"] += (m.get("costo_usd") or 0.0) + (t.get("costo_estimado") or 0.0)'),
    ("equivalente no se cuenta", 'g["equivalente_api"] += t.get("costo_estimado") or 0.0', "pass"),
    ("caídas no se cuentan", 'if str(r.get("estado", "")).startswith("error"):', "if False:"),
    ("toda llamada es caída", 'if str(r.get("estado", "")).startswith("error"):', "if True:"),
    ("caché no se suma", 'for campo in ("entrada", "cache_leido", "salida"):', 'for campo in ("entrada", "salida"):'),
    ("cadena rota no se avisa", 'rota = S._rotura(manifiestos) is not None', "rota = False"),
    ("vía del resultado se ignora", 'if resultado and resultado.get("via"):', "if False:"),
    ("dimensión libre", '    if por not in DIMENSIONES:\n        raise', '    if False:\n        raise'),
    ("total sin sumar", '            total[campo] += g[campo]', "            pass"),
    ("aviso no se imprime", '        if t["cadena_rota"]:', "        if False:"),
]
ORIGINALES = {"motor/contexto.py": CONTEXTO, "motor/medir.py": MEDIR, "motor/state.py": MUTANTES, "motor/runtime.py": RUNTIME, "motor/revisar.py": REVISAR,
              "motor/nodos.py": NODOS, "motor/saneo.py": SANEO, "motor/modelos.py": MODELOS}
base = subprocess.run([str(REPO / ".venv/bin/pytest"), "-q", "-p", "no:cacheprovider"], cwd=REPO,
                      capture_output=True, text=True)
if base.returncode:
    sys.exit("la base no está limpia: el resultado no significaría nada\n" + base.stdout[-500:])
print("base limpia:", base.stdout.strip().splitlines()[-1])
vivos, invalidos = [], []
total = 0
for archivo, lista in ORIGINALES.items():
    original = (REPO / archivo).read_text(encoding="utf-8")
    for nombre, viejo, nuevo in lista:
        total += 1
        if viejo not in original:
            invalidos.append(nombre)
            continue
        shutil.rmtree(TMP, ignore_errors=True)
        shutil.copytree(REPO, TMP, ignore=shutil.ignore_patterns(".venv", ".git", "__pycache__", ".pytest_cache"))
        (TMP / archivo).write_text(original.replace(viejo, nuevo, 1), encoding="utf-8")
        try:
            r = subprocess.run([str(REPO / ".venv/bin/python"), "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider"],
                               cwd=TMP, capture_output=True, text=True, timeout=120)
            if r.returncode == 0:
                vivos.append(nombre)
        except subprocess.TimeoutExpired:
            pass  # un bucle sin fin también delata al mutante
print(f"{total} mutantes, {total - len(vivos) - len(invalidos)} detectados")
print("VIVOS:", vivos)
print("NO APLICARON:", invalidos)
shutil.rmtree(TMP.parent, ignore_errors=True)
sys.exit(1 if vivos or invalidos else 0)
