# Bloque 14 en el grafo

Generado desde el código con `runtime.dibujar`. `producir` y `siguiente` son de ejemplo.

```mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD;
	__start__([<p>__start__</p>]):::first
	producir(producir)
	revision_mecanica(revision_mecanica)
	siguiente(siguiente)
	__end__([<p>__end__</p>]):::last
	__start__ --> producir;
	producir --> revision_mecanica;
	revision_mecanica -.-> producir;
	revision_mecanica -.-> siguiente;
	siguiente --> __end__;
	revision_mecanica -.-> revision_mecanica;
	classDef default fill:#f2f0ff,line-height:1.2
	classDef first fill-opacity:0
	classDef last fill:#bfb6fc

```

La flecha punteada de vuelta a `producir` es el ciclo de corrección: solo ocurre si hay fallas, con dos rondas como
máximo. Los avisos no devuelven la pieza.
