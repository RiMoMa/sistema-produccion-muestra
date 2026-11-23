# Bloque 15 en el grafo

Generado desde el código con `runtime.dibujar`, con la línea de `pruebas/test_verificador.py`. `producir`,
`mecanica` y `siguiente` son de ejemplo.

```mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD;
	__start__([<p>__start__</p>]):::first
	producir(producir)
	mecanica(mecanica)
	verificar(verificar)
	PJ(PJ)
	siguiente(siguiente)
	__end__([<p>__end__</p>]):::last
	PJ -.-> producir;
	PJ -.-> siguiente;
	PJ -.-> verificar;
	__start__ --> producir;
	mecanica --> verificar;
	producir --> mecanica;
	verificar --> PJ;
	siguiente --> __end__;
	classDef default fill:#f2f0ff,line-height:1.2
	classDef first fill-opacity:0
	classDef last fill:#bfb6fc

```

Todas las rutas pasan por `PJ`, pero la puerta solo se detiene si el informe trae un J o un tipo 1. Si trae M o R,
vuelve a `producir`, con dos rondas como máximo. Un tipo 1 no vuelve: espera a Ricardo, porque hay que arreglar el
contexto, no la pieza.
