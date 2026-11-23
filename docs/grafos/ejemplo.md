# Grafo de ejemplo

Línea de prueba con nodos falsos, generada con `runtime.dibujar`. Aún no es el sistema real.

- **Cajas con nombre de paso:** el trabajo. Las hace un script o un modelo.
- **P1, PJ, P4:** puertas. Ahí el flujo se detiene hasta que usted decida.
- **Flecha continua:** siempre pasa por ahí.
- **Flecha punteada:** depende de lo que usted decidió o de lo que encontró la revisión.

```mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD;
	__start__([<p>__start__</p>]):::first
	extraer(extraer)
	analizar(analizar)
	P1(P1)
	producir(producir)
	revisar(revisar)
	PJ(PJ)
	publicar(publicar)
	P4(P4)
	__end__([<p>__end__</p>]):::last
	P1 -.-> analizar;
	P1 -.-> producir;
	P4 -.-> __end__;
	P4 -.-> publicar;
	PJ -.-> producir;
	PJ -.-> publicar;
	PJ -.-> revisar;
	__start__ --> extraer;
	analizar --> P1;
	extraer --> analizar;
	producir --> revisar;
	publicar --> P4;
	revisar --> PJ;
	classDef default fill:#f2f0ff,line-height:1.2
	classDef first fill-opacity:0
	classDef last fill:#bfb6fc

```

Cómo leerlo: `P1` hacia `analizar` es una devolución. `PJ` hacia `producir` es el ciclo de corrección, con dos
rondas como máximo. `PJ` solo se detiene si la revisión encontró algo que pide su juicio.
