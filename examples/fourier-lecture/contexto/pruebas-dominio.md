# Pruebas del dominio

Las pruebas que el verificador aplica, además de las generales, porque este
dominio tiene sus propios errores caros.

## Prueba 1 · Todo par y toda propiedad tienen comprobación numérica

**Pasa** si cada par transformado, propiedad o identidad que la pieza afirma
tiene una función en `verificacion/comprobaciones.py` que la comprueba con
números (integral numérica contra la fórmula cerrada, en varios $\omega$) y
`python3 verificacion/comprobaciones.py` sale con todas en OK.
**No pasa** si una fórmula de la pieza no tiene su comprobación, o si la
comprobación mide otra cosa que lo que la pieza escribe (por ejemplo, la pieza
usa $\mathrm{sinc}$ sin $\pi$ y la comprobación con $\pi$).
**Pregunta que decide:** ¿se puede señalar la función que comprueba esta
fórmula, tal como está escrita, y fallaría esa función si el signo estuviera
cambiado? (D4: con una señal par, no falla.) La evidencia es su versión
`f(error=True)`, que el script corre siempre y exige que falle (D6). La prueba
no pasa si la versión con error no expresa el error caro de esa fórmula (por
ejemplo, si la cantidad que el error cambiaría está escrita a mano).

## Prueba 2 · La convención es una sola

**Pasa** si toda fórmula de todas las piezas usa la convención de `estilo.md`
(signo del exponente, factor $1/2\pi$ en la inversa, $\mathrm{sinc}$ sin $\pi$).
**No pasa** si aparece $X(f)$, $e^{-j2\pi ft}$ o $\mathrm{sinc}$ con $\pi$ sin
el aviso de conversión. Palabras delatoras: `2\pi f`, `X(f)`, `\pi t)/(\pi t`.

## Prueba 3 · Condición de existencia

**Pasa** si cada definición o par dice para qué señales vale (absolutamente
integrable, energía finita, o "en el sentido de las distribuciones").
**No pasa** si un par como el del escalón o el coseno se da como integral
ordinaria sin decir que la integral no converge.

## Prueba 4 · La pieza no se resuelve a sí misma

**Pasa** si las soluciones de la hoja de problemas van al final, después de
todos los enunciados. **No pasa** si el enunciado de un problema trae su
resultado ("show that X(ω) = …" está permitido; "find X(ω), which is …" no).
