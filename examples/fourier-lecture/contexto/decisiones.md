# Decisiones

El historial: cada decisión con su fecha, su razón y su tabla de revisión del
corpus. Lo que manda hoy está destilado en `reglas-vigentes.md`; si chocan,
manda este archivo y el destilado se corrige en la misma sesión.

### D1 · El escenario no usa la marca de una universidad británica
*1 de noviembre de 2026*

- Es una prueba del sistema. Ningún material lleva nombre, escudo ni colores
  institucionales de una universidad británica; el tema de los decks es el neutro del núcleo.

**Razón:** el pedido fue "un curso de señales de nivel universitario británico"; no hay encargo
de la universidad y usar su marca haría pasar la prueba por material oficial.

**Tabla de revisión del corpus:** no aplica (no había corpus al decidir).

### D2 · Comprobación numérica obligatoria para toda fórmula
*1 de noviembre de 2026*

- Regla 3 de `instructions.md` y prueba 1 de `pruebas-dominio.md`.

**Razón:** en este dominio la cita no es el error caro; el error caro es una
fórmula mal escrita que se ve bien. Es el equivalente de "ninguna cita sin abrir
la fuente".

**Tabla de revisión del corpus:** no aplica (no había corpus al decidir).

### D3 · Las cuatro J de la primera verificación, resueltas con la recomendación del verificador
*1 de noviembre de 2026*

- J4: la clase 5 incluye Parseval y la relación de anchos; el calendario lo dice.
- J5: los apuntes se publican en PDF (`herramientas/pdf.py`, KaTeX), porque se
  leen solos antes de la tutoría y el LaTeX crudo no se lee.
- J8: las diapositivas del escalón van en la rama 2 (Definition): extienden la
  definición a las distribuciones.
- J11: el error típico del sinc escribe explícito el par equivocado.
- **Asumidas por la sesión, no por el responsable**: en esta prueba se aplicó la
  recomendación para no detener el ciclo. El responsable puede revertir cualquiera.

**Razón:** informe del verificador en frío del 1 de noviembre (hallazgos 4, 5, 8 y 11).

**Tabla de revisión del corpus** (agente `verificador`, en frío, 1 de noviembre de 2026):

| Pieza | Revisada | Qué quedó desalineado |
|---|---|---|
| `contexto/calendario.md` | 1 nov 2026, completa | Nada. J4 en l.15 y l.22-24 |
| `produccion/clase-05/notes.md` | 1 nov 2026, completa | Nada. J4: Parseval l.238-243, objetivo 5 l.20-21, anchos en problema y solución 6. J11: par equivocado explícito en l.72-74, matemática correcta |
| `produccion/clase-05/notes.pdf` (p-1 a p-9) | 1 nov 2026, mirada página por página | Nada respecto a J5; defectos de maquetación en el hallazgo 3 de la ronda 2 |
| `produccion/clase-05/deck.json` y `.pptx` | 1 nov 2026, completa y mirada | J8: nada (rama 2 en l.134 y l.143). J4: Parseval no aparece; portada l.34 "pairs · properties · convolution" (J6 de la ronda 2). J11 no aplica |
| `produccion/clase-05/graficas.py` | 1 nov 2026, completa | Nada |
| `verificacion/comprobaciones.py` | 1 nov 2026, completa | Nada: Parseval y anchos tienen comprobación |
| `herramientas/pdf.py` | 1 nov 2026, completa | Nada respecto a J5 |

### D4 · Una comprobación debe poder fallar ante el error que vigila
*1 de noviembre de 2026*

- Precisa D2. Toda comprobación de una fórmula con signo o con orientación
  (dualidad, inversa, desplazamiento) usa una señal sin simetría; si la señal
  es par, el error de signo pasa sin ser visto.
- Una afirmación general que no se puede comprobar con números (una cota) se
  escribe como "it can be shown" y se comprueba en casos concretos, diciendo
  que no es una demostración.

**Razón:** hallazgos 2 y 3 de la verificación en frío: `par_dualidad_lorentz` y
`prop_inversa` usaban funciones pares y no habrían detectado un signo cambiado;
la cota $\sigma_t\sigma_\omega \ge 1/2$ se afirmaba sin comprobación. Se probó
con una mutación que las comprobaciones nuevas sí fallan ante el signo cambiado.

**Tabla de revisión del corpus** (agente `verificador`, en frío, 1 de noviembre de 2026):

| Pieza | Revisada | Qué quedó desalineado |
|---|---|---|
| `verificacion/comprobaciones.py` | 1 nov 2026, completa, con mutaciones | l.303-308 `par_serie_muestras`: señal par, pasa con el signo cambiado (**tipo 1**, origina D5). `par_dualidad_lorentz` y `prop_inversa` siguen pares, cubiertas por sus versiones asimétricas. La cota se comprueba en tres casos y dice "no es una demostración" |
| `produccion/clase-05/notes.md` | 1 nov 2026, completa | l.289: "$\sigma_t\,\sigma_\omega = \tfrac{1}{2}$ for the Gaussian, larger for other shapes", cota general sin "it can be shown". l.275 remite a `par_serie_muestras`. l.360-363 alineada |
| `produccion/clase-05/notes.pdf` | 1 nov 2026, mirada | Lo mismo, en p-7 y p-9 |
| `produccion/clase-05/deck.json` y `.pptx` | 1 nov 2026, completa y mirada | l.58 "cₖ = X(kω₀) / T₀": su comprobación incumplía D4. l.98 cierta. Dualidad cubierta |
| `produccion/clase-05/graficas.py` | 1 nov 2026, completa | Nada |

### D5 · Toda comprobación sensible al signo registra su mutante, y el script exige que falle
*1 de noviembre de 2026*

- Precisa D4, que nombraba ejemplos ("dualidad, inversa, desplazamiento") y se
  leyó como lista cerrada. Alcance: toda fórmula donde aparezca el signo de un
  exponente, una orientación ($t \to -t$, $\omega \to -\omega$) o un valor
  absoluto que el error quitaría.
- La mutación deja de ser algo que se pide y pasa a ser estructura:
  `comprobaciones.py` tiene `MUTANTES`, y sale con 1 si algún mutante pasa.
- La regla 3 cubre pares, propiedades e identidades; las consecuencias
  numéricas derivadas (un cero, un pico, un orden de decaimiento) las revisa la
  lectura (J5 de la ronda 2).
- El deck es apoyo de la clase; los apuntes cubren el tema completo y el deck
  lo dice en su portada (J6 de la ronda 2).
- J5 y J6, **asumidas por la sesión** con la recomendación del verificador.

**Razón:** tipo 1 de la ronda 2 del 1 de noviembre: `par_serie_muestras`,
escrita después de D4, usaba un pulso par y pasaba con el signo cambiado. Es la
misma falla que originó D4, en la misma sesión que la acababa de corregir. Con
dos rondas gastadas, se rehízo desde el contexto la sección que la produce (las
comprobaciones de signo), no solo esa función.

**Tabla de revisión del corpus** (agente `verificador`, en frío, 1 de noviembre de 2026):

| Pieza | Revisada | Qué quedó desalineado |
|---|---|---|
| `verificacion/comprobaciones.py` | 1 nov 2026, completa, con mutaciones en memoria | l.182-187 `prop_parseval` y l.250-254 `problema_energia_banda`: "\|X\|²" escrito a mano (`1 / (a * a + w * w)`), ciegas al valor absoluto, sin mutante (**tipo 1**, origina D6). l.85-96 `par_escalon` y l.173-179 `prop_convolucion_directa`: pueden fallar pero no están en `MUTANTES`. l.346-347 "lo mira el verificador": la completitud de `MUTANTES` no es estructura. l.349-424: 14 de 15 mutantes son copias; solo l.390-391 llama a su comprobación. Los otros mutantes fallan ante su error |
| `produccion/clase-05/notes.md` | 1 nov 2026, completa | l.152 y l.281 (escalón) y l.228 (convolución): sus comprobaciones no tienen mutante. l.240, l.287 y l.352 (Parseval y problema 5): comprobación ciega al \|·\|. l.270-271 "Each line is checked numerically" queda más fuerte que lo que el script sostiene en esas filas. Consecuencias por lectura: todas correctas |
| `produccion/clase-05/notes.pdf` (p-1 a p-9) | 1 nov 2026, mirada página por página | Lo mismo que notes.md; además, tabla partida en p-4/p-5 y título huérfano en p-6 |
| `produccion/clase-05/deck.json` y `.pptx` | 1 nov 2026, completa y mirada | l.144 (d-08) escalón sin mutante. Viñeta 4 cumplida en l.34 (d-01) |
| `produccion/clase-05/graficas.py` | 1 nov 2026, completa | Nada |
| `herramientas/pdf.py` | 1 nov 2026, completa | Nada respecto a D5 |
| `contexto/reglas-vigentes.md`, `pruebas-dominio.md`, `verificacion/checklist-qa.md` | 1 nov 2026, completas | Recogen D5. La checklist l.23 acepta "N/N detectan su error", y ese N solo cuenta los mutantes registrados: no ve uno que falta |

### D6 · El mutante es la misma comprobación con `error=True`, y el script exige que toda comprobación lo tenga
*1 de noviembre de 2026*

- Anula la lista `MUTANTES` de D5 (precisa D5).
- Toda comprobación es `f(error=False)`. `f(error=True)` calcula la fórmula con
  el error típico que vigila (signo, factor, valor absoluto, orientación,
  convención). El script exige que `f()` pase y `f(error=True)` falle.
- Una comprobación sin `error` hace fallar el script, salvo que esté en
  `EXENTAS` con su razón. La completitud deja de depender del verificador.
- Las cantidades derivadas (como $|X|^2$) se calculan desde la fórmula, nunca
  se escriben a mano: si se escriben a mano, el error que vigilan no se puede
  expresar.
- Cada comprobación vigila un error; las que tienen señal par (dualidad e
  inversa con funciones pares) vigilan el factor $2\pi$ y el signo lo vigila su
  versión asimétrica.
- J5 de la ronda 3, opción (a), **asumida por la sesión** con la recomendación
  del verificador.

**Razón:** tipo 1 de la ronda 3 del 1 de noviembre, el tercero de la misma
familia en el día: `prop_parseval` y `problema_energia_banda` escribían
$|X|^2$ a mano y no podían ver el valor absoluto quitado; `par_escalon` y
`prop_convolucion_directa` no tenían mutante, y el script decía "15/15" porque
solo contaba los registrados. Se probó con una comprobación ficticia que el
script nuevo falla ante una comprobación sin versión con error y ante una
ciega.

**Tabla de revisión del corpus:** pendiente (agente `verificador`, en frío).
