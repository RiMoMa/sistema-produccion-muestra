# Reglas vigentes

Destilado de `contexto/decisiones.md` al 1 de noviembre de 2026. Si chocan,
manda decisiones.md.

## Contenido

- Ningún material lleva la marca de una universidad británica; tema de decks neutro (D1).
- Toda fórmula afirmada tiene su comprobación numérica en
  `verificacion/comprobaciones.py` (D2).
- Toda comprobación de una fórmula con signo u orientación usa una señal sin
  simetría (D4).
- Toda comprobación es `f(error=False)`; `f(error=True)` calcula el error
  típico que vigila y tiene que fallar. El script falla si una comprobación no
  tiene versión con error (salvo `EXENTAS`, con razón) o si es ciega (D6).
- Las cantidades derivadas se calculan desde la fórmula, nunca a mano (D6).
- Una cota general se dice "it can be shown" y se comprueba en casos
  concretos, en todo lugar donde aparezca (D4).
- La regla 3 cubre pares, propiedades e identidades; las consecuencias
  numéricas las revisa la lectura (D5).
- El deck es apoyo; los apuntes cubren el tema completo (D5).
- Los apuntes se publican en PDF con `herramientas/pdf.py` (D3).
- Las seis reglas de contenido de `instructions.md`.

## Proceso y registro

- El ciclo de `proceso.md`; el verificador en frío llena las tablas de corpus.
