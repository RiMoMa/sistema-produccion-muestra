# Bloque 16 en el grafo

Generado desde el código con `runtime.dibujar`, con la línea de `pruebas/test_fuentes.py`. `producir` y `cerrar`
son de ejemplo.

```mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD;
	__start__([<p>__start__</p>]):::first
	producir(producir)
	filtrar(filtrar)
	fuentes(fuentes)
	cerrar(cerrar)
	P4(P4)
	anexar(anexar)
	__end__([<p>__end__</p>]):::last
	P4 -.-> anexar;
	P4 -.-> cerrar;
	__start__ --> producir;
	cerrar --> P4;
	filtrar --> fuentes;
	fuentes -.-> cerrar;
	fuentes -.-> producir;
	producir --> filtrar;
	anexar --> __end__;
	fuentes -.-> fuentes;
	classDef default fill:#f2f0ff,line-height:1.2
	classDef first fill-opacity:0
	classDef last fill:#bfb6fc
```

`filtrar` le pasa al verificador solo las filas del registro que la pieza cita. Si hay corregidas o no
verificables, vuelve a `producir`, con dos rondas como máximo. `anexar` corre después de la puerta P4: al registro
solo entran fuentes de piezas aprobadas.
