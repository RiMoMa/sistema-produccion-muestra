# Decisiones

El historial: cada decisión con su fecha, su razón y su tabla de revisión del
corpus. Cada entrada tiene su fila en `indice-decisiones.md`, en la misma
pasada: el motor arma el paquete de cada pieza desde ahí y no arranca si falta
una fila.

## Formato de una decisión

### D<n> · <la regla, en una línea>
*<fecha>*

<Qué se decide, en viñetas cortas. Si precisa o anula otra, se dice:
"Precisa D<m>" / "Anula D<m>", y en D<m> se agrega "Precisada por D<n>".>

**Razón:** <el caso concreto que la originó: qué pasó, en qué pieza.>

**Tabla de revisión del corpus** (agente `verificador`, en frío, <fecha>):

| Pieza | Revisada | Qué quedó desalineado |
|---|---|---|
| <ruta> | <fecha> | <cita textual y línea, o "Nada" si se leyó completa> |

Una decisión sin su tabla está incompleta. Mientras falte, se escribe:
**Tabla de revisión del corpus: pendiente.**
