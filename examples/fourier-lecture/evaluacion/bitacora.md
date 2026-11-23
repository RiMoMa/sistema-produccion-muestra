# Bitácora · escenario 1 de la fase 3 (Fourier, segundo año, estilo británico)

*1 de noviembre de 2026.* Primera instancia montada solo desde `sistema/`,
en un dominio, un idioma y un tipo de error distintos de los de la primera instancia.

## Qué se hizo

| Paso | Resultado |
|---|---|
| Instanciar (`instanciar.md`, sección 1) | Estructura y archivos del núcleo copiados en minutos; la envoltura de `revisar.sh` funcionó con una ruta relativa al sistema |
| Contexto (sección 2) | Audiencia marcada entera como supuesto; calendario sin fuente oficial (no se pudo abrir ningún temario de una universidad británica) y declarado como supuesto; estilo en español para un entregable en inglés británico |
| Producción | Apuntes con hoja de tutoría, deck de 13 diapositivas, tres gráficas desde código |
| Verificación en frío, ronda 1 | 11 hallazgos: 2 bloqueantes, 0 tipo 1, 4 J |
| Corrección | Una pasada, todas las clases; J resueltas con la recomendación del verificador (D3) |
| Verificación en frío, ronda 2 | **1 tipo 1** (bloqueante), 2 correcciones, 1 mejora de maquetación, 2 J. El tipo 1: `par_serie_muestras`, escrita por la sesión *después* de D4, usaba un pulso par y no podía ver un signo cambiado: el mismo error que D4 acababa de corregir |
| Respuesta al tipo 1 | Con dos rondas gastadas no se parchó la función: se rehízo desde el contexto la sección que produce el error. D5 vuelve estructural la prueba de mutación (`MUTANTES`, 15 mutantes que el script exige que fallen) y la regla universal pasó al núcleo (`proceso.md`, "Un control se prueba contra su error") |
| Verificación de lo rehecho (ronda 3) | **Otro tipo 1**, el tercero de la familia: Parseval escribía $\lvert X\rvert^2$ a mano y no podía ver el valor absoluto quitado; dos comprobaciones sensibles no tenían mutante y el script decía "15/15" porque solo contaba los registrados. La causa: D5 dejó la completitud de la lista "a cargo del verificador" |
| Respuesta (D6) | Se eliminó la lista: el mutante es la misma función con `error=True`, y el script falla si una comprobación no tiene versión con error o si es ciega. Probado con dos comprobaciones ficticias (una sin versión con error, una ciega): el script falla con las dos. 33/33 en OK, 33/33 detectan su error |
| Estado al cerrar la sesión | **Borrador.** D6 no tiene verificación en frío ni tabla de corpus. El PDF tiene una limitación conocida: un título puede quedar al pie con solo el encabezado de una tabla larga (Chrome no la respeta) |

## Lo que el sistema hizo bien

1. **La regla del calendario impidió inventar el temario.** Sin ella, lo fácil
   era escribir "A1, lecture 5" con un temario plausible.
2. **"Ninguna cita sin abrir la fuente" se tradujo al dominio.** En
   matemáticas el error caro es la fórmula, no la cita: la regla equivalente
   fue "ninguna fórmula sin comprobación numérica" (D2). El núcleo lo permitió
   sin cambios, vía `pruebas-dominio.md`.
3. **El verificador en frío encontró lo que el autor no vio:** dos
   comprobaciones con funciones pares que no habrían detectado un signo
   cambiado (el autor las había dado por buenas), una cota afirmada sin
   comprobar, y la ruta local del equipo dentro del `.pptx`.
4. **"Un falso positivo se corrige en el detector"** se aplicó cuatro veces
   (tres en `comprobaciones.py`, una en `revisar.reglas`) y ninguna tocó el
   contenido.

## Lo que la prueba mostró que le falta al núcleo

| Falta | Qué se hizo | Estado |
|---|---|---|
| Diapositiva de figura a todo el ancho | Tipo `figura` en `generar.js` | Resuelto en el núcleo |
| Tablas a 13 pt en media diapositiva vacía | El tamaño crece con pocas filas | Resuelto en el núcleo |
| El `.pptx` guardaba la ruta local completa como texto alternativo | `altText` = `descripcion` de la imagen | Resuelto en el núcleo; afecta también a los decks de la primera instancia que pasen por el generador |
| Ecuaciones en diapositivas | Texto con `exp(...)` y Unicode | **Abierto**: pptxgenjs no dibuja LaTeX; opción, una imagen por ecuación generada desde LaTeX |
| Generador de PDF con fórmulas | `herramientas/pdf.py` (markdown + KaTeX + Chrome), en la instancia | **Abierto**: el núcleo no trae generador de PDF; la herramienta de la primera instancia no maneja fórmulas |
| La comprobación del dominio puede ser ciega a su propio error | D4: probar con mutación que la comprobación falla ante el error que vigila | Aprendizaje universal candidato al núcleo |

## El dato más útil de la prueba

La sesión que escribió D4 ("una comprobación debe poder fallar ante su error")
escribió diez minutos después una comprobación que no podía fallar. Una regla
escrita no impidió el error; el verificador en frío sí lo vio. Es la evidencia
más directa hasta ahora de dos principios del núcleo: **quien produce no
verifica**, y **una regla que depende de que alguien se acuerde se convierte en
estructura** (aquí, mutantes que el script corre siempre).

## La escalera de las tres rondas

| Ronda | Lo que se arregló | Dónde quedó el hueco |
|---|---|---|
| 1 → D4 | "Usar señales sin simetría" (regla escrita) | Dependía de que el autor se acordara |
| 2 → D5 | Lista de mutantes que el script corre | La completitud de la lista dependía del verificador |
| 3 → D6 | El mutante es la misma función; el script exige que exista | Ninguno conocido en la estructura; queda que cada `error=True` exprese el error *caro*, y eso sigue siendo lectura |

Cada ronda movió el control un escalón más lejos de la memoria de alguien. Es
el patrón que el inventario de la primera instancia llama "una regla que
depende de la memoria se automatiza o se pierde", visto aquí en tiempo real.

## Aprendizaje universal nuevo

**Un control que no puede fallar no controla nada.** Toda comprobación (un
script, una regla, una prueba de dominio) se prueba una vez contra el error que
vigila, a propósito, antes de confiar en que sale en OK. Es la versión general
de D4 y del falso negativo de D36 que se vio el mismo día en la primera
instancia: la regla existía y salía limpia porque no podía ver el caso.
