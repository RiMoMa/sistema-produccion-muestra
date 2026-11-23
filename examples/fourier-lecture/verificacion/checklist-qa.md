# Checklist de verificación

Lo que el script no detecta y hay que mirar leyendo. Una sección por tipo de
pieza, más las comunes. Cada ítem nace de un error que ya ocurrió: si un ítem no
ha atrapado nada en mucho tiempo, se revisa si sigue siendo necesario.

## Común a toda pieza

- [ ] El tema corresponde exactamente al del calendario.
- [ ] No contradice ninguna regla vigente.
- [ ] Toda cita, norma, noticia o cifra atribuida tiene su fuente abierta y
      registrada, y la afirmación no es más fuerte que la fuente.
- [ ] Toda corrección reciente se buscó en todo el corpus (propagación).
- [ ] La salida publicada se regeneró desde la fuente y se recorrió mirándola.

## Apuntes

- [ ] Sigue el orden de `plantillas/apuntes.md`; cada sección cierra con
      ejemplo resuelto y error típico con cómo detectarlo (regla 5).
- [ ] Cada fórmula de la pieza tiene su función en `comprobaciones.py`, que la
      comprueba tal como está escrita, y el script sale en OK (prueba 1).
- [ ] El script dice "0 ciegas · 0 sin versión con error", y cada
      `f(error=True)` expresa el error caro de su fórmula, no uno cualquiera (D6).
- [ ] Una sola convención, la de `estilo.md` (prueba 2).
- [ ] Toda definición y todo par dicen su condición de existencia (prueba 3).
- [ ] Los enunciados no traen su resultado; las soluciones van al final (prueba 4).
- [ ] Inglés británico, sin palabras que culpan al lector.
- [ ] Nada de marca de una universidad británica (D1).

## Deck

- [ ] Cada fórmula de las diapositivas coincide con la de los apuntes.
- [ ] Las gráficas salen de `graficas.py` y usan la convención del curso.
- [ ] Se miró como imágenes (`qa/`), diapositiva por diapositiva.
