# Estilo

Cómo se escribe en este proyecto. Cada regla con un ejemplo de lo que se
corrigió, porque una regla sin ejemplo se cumple de nombre.

## Registro y trato

- Inglés británico: *analyse, behaviour, centre, modelling, signalling*. Nunca
  la grafía americana (`revisar.reglas` la marca).
- Se escribe en primera persona del plural académica ("we now show"), sin
  "you" imperativo salvo en los problemas.
- Ni *obviously*, *clearly*, *trivially* ni *it is easy to see*: si fuera obvio
  no estaría escrito, y al que no lo ve le dice que el problema es él.
  Ejemplo corregido: "Clearly the integral converges" → "The integral
  converges because $|x(t)e^{-j\omega t}| = |x(t)|$ and $x$ is absolutely
  integrable."

## Notación del curso (una sola, regla 2)

- Unidad imaginaria $j$. Frecuencia angular $\omega$ en rad/s.
- Transformada: $X(\omega) = \int_{-\infty}^{\infty} x(t)\,e^{-j\omega t}\,dt$.
- Inversa: $x(t) = \frac{1}{2\pi}\int_{-\infty}^{\infty} X(\omega)\,e^{j\omega t}\,d\omega$.
- Par: $x(t) \leftrightarrow X(\omega)$. Escalón $u(t)$. Pulso
  $\mathrm{rect}(t/T)$ de ancho $T$ centrado en 0.
  $\mathrm{sinc}(x) = \sin(x)/x$ (sin $\pi$; se dice en la primera aparición,
  porque hay libros que usan la otra).
- Matemática en LaTeX entre `$...$` y `$$...$$`.

## Lo que no se escribe nunca (y cómo se detecta)

- Grafía americana: script.
- *obviously, clearly, trivially*: script (aviso).
- Un par o propiedad sin comprobación numérica: lectura, contra
  `verificacion/comprobaciones.py`.
- La frecuencia $f$ en hertz mezclada con $\omega$ sin decir la conversión.

## Estructura de las piezas

Ver `plantillas/apuntes.md`. Pregunta, idea, definición con su condición,
ejemplo resuelto, error típico; problemas al final y soluciones después.

## Ejemplos corregidos

- "The Fourier transform of $u(t)$ is $1/j\omega$" → falta el término
  $\pi\delta(\omega)$: $u(t) \leftrightarrow \pi\delta(\omega) + \frac{1}{j\omega}$.
  Es el error típico que se enseña, no uno que se comete.
