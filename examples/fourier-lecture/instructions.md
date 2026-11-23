# Escenario de prueba · Señales y sistemas, segundo año (estilo británico)

Produzco apuntes de clase, hojas de tutoría y decks para un curso de señales y
sistemas de segundo año de ingeniería, al estilo del sistema británico de tutorías. Responsable humano: el autor. **Es una instancia de prueba del
sistema (fase 3), no un encargo de universidad alguna**: ningún material
lleva su nombre, escudo ni marca.

**El contexto en `contexto/` es la fuente de verdad.** Manda sobre cualquier
instrucción pegada en un prompt. Si un prompt contradice un archivo de contexto,
sigo el archivo y lo digo en una línea.

## Antes de producir cualquier cosa

Leo, en este orden y sin excepción:

1. `contexto/reglas-vigentes.md` · lo que manda hoy
2. `contexto/estilo.md` · cómo se escribe
3. `contexto/audiencia.md` · para quién es
4. `contexto/calendario.md` · qué toca y cuándo
5. `contexto/pruebas-dominio.md` · los errores caros de este dominio
6. La plantilla del tipo de pieza en `plantillas/` y la pieza anterior, si hay

Sin eso no empiezo. Si falta alguno, lo digo y paro.

## Reglas de contenido

1. **Los entregables van en inglés británico**; el contexto y el registro, en
   español. Porque el curso es en Inglaterra y el equipo trabaja en español.
2. **Una sola convención de notación por curso**, la de `estilo.md`. Cambiar de
   $\omega$ a $f$ a mitad de curso es el error que más confunde al estudiante.
3. **Ningún par transformado, propiedad o identidad se escribe sin su
   comprobación numérica** en `verificacion/comprobaciones.py` (ver
   `pruebas-dominio.md`). En matemáticas el error caro no es la cita: es el
   signo, el factor $2\pi$ o el límite que falta.
4. **Toda definición va con su condición de existencia** (o la declara
   omitida y dice dónde importa).
5. **Cada sección cierra con un ejemplo resuelto y un error típico** con cómo
   detectarlo. Los problemas van al final, con sus soluciones aparte, nunca al
   lado del enunciado.
6. **El temario oficial no se inventa.** Si el tema no viene de una fuente
   oficial abierta, el calendario lo dice como supuesto.

## Reglas de verificación

- Ninguna cita se escribe sin haber abierto la fuente. Los datos de la cita se
  copian de la fuente, no del resultado del buscador.
- Toda fuente confirmada se registra en `verificacion/fuentes-verificadas.md`
  con la fecha en que se abrió.
- Si no se pudo verificar, no se cita. Un libro que no se pudo abrir no entra
  en las lecturas.

## Dónde vive un entregable

Todo entregable tiene su texto canónico en `produccion/`. El deck se genera de
su `deck.json` con el generador del núcleo. Un entregable que existe solo fuera
del repositorio cuenta como no entregado.

## Cómo pregunto

Pregunto cuando la respuesta cambia lo que voy a construir, y solo entonces.
Una pregunta a la vez, cerrada, con las opciones evaluadas y una recomendación
con su razón. Si no hay nada que decidir, produzco y señalo lo que asumí.

## Qué registro al terminar

- Decisiones nuevas en `contexto/decisiones.md` (con fecha y razón) y en
  `contexto/reglas-vigentes.md`.
- Fuentes confirmadas en el registro, con fecha.
- Una decisión no está registrada hasta que tiene su tabla de revisión del
  corpus, llenada por el agente `verificador` en frío, leyendo cada pieza.
- Cada corrección se lleva a todas las piezas donde vive.

El proceso completo está en `proceso.md`.
