# trawl-design-lab

```{image} _static/img/banner.svg
:alt: trawl-design-lab · trawlkit: diseño de redes de arrastre, nacido en la Ingeniería Pesquera de la UTN (FRTDF, FRCh y FRMDP)
:width: 100%
```

**Diseño y dimensionamiento de redes de arrastre de fondo: teoría, cálculo reproducible y software.**

Este libro documenta `trawlkit`, un motor de cálculo abierto que reimplementa y extiende el modelo
de diseño de la red de arrastre FAO A-3 para pesqueros de 150–180 HP del Canal Beagle, desarrollado
originalmente en un libro de Excel por Ariel Luján Giamportone en Ingeniería Pesquera de la
Universidad Tecnológica Nacional, Facultad Regional Tierra del Fuego {cite:p}`giamportone2024`. La
historia de ese origen y las tres Facultades donde se dicta la carrera están en {doc}`utn`.

## Para quién es

- **Ingenieros pesqueros y estudiantes**: cada etapa del cálculo se presenta con su teoría, sus
  ecuaciones, los coeficientes empíricos y la referencia del autor que los propuso.
- **Diseñadores, armadores y patrones**: el caso de estudio muestra cómo pasar de la potencia del
  buque a la red, el aparejo, la flotación, el lastre y el cable, y cuál es la velocidad
  remolcable; el catálogo, los componentes y los lotes llevan ese cálculo a otras redes, al costo
  y a una flota entera.
- **Desarrolladores**: la última parte describe la arquitectura del software, los informes, la API
  y la aplicación web.

## Probar la aplicación

La aplicación web está publicada junto a este libro:
**<https://arielgiamportone.github.io/trawl-design-lab/app/>**. Tiene dos modos: el **guiado**, cuatro
pasos (buque, red, operación y resultado) con un diagnóstico en lenguaje llano, y el **experto**,
con gráficos, diseño interactivo sobre el plano, optimización, simulación 3D, selectividad,
catálogo FAO, componentes y costo, y lotes de flota. Usa la API pública del motor y, sin conexión,
el mismo motor dentro del teléfono ({doc}`web`). El primer cálculo con la API puede tardar hasta un
minuto si estaba dormida (plan gratuito; ver {doc}`despliegue`).

## Cómo leerlo

1. **Fundamentos**: el problema, la nomenclatura y el origen del proyecto en la UTN ({doc}`utn`).
2. **Teoría y métodos**: un capítulo por etapa, en el mismo orden en que se resuelve el diseño
   (capítulos 10 a 19). Cada capítulo ejecuta el cálculo con `trawlkit` y lo verifica contra el
   libro Excel original. Siguen la optimización del tamaño de la red y de la velocidad
   ({doc}`20_optimizacion`), la simulación de la forma de la red remolcada ({doc}`21_simulacion`) y
   el simulador realista: captura, fondo y portones acoplados ({doc}`22_simulacion_realista`), el
   mar real ({doc}`23_mar_real`), la malla y la selectividad ({doc}`24_malla_selectividad`), y la
   incertidumbre y la calibración ({doc}`25_incertidumbre_calibracion`).
3. **Caso de estudio y validación**: la red FAO A-3 estándar y modificada, la validación contra el
   Excel y contra el simulador DynamiT, el catálogo de redes FAO con su procedencia
   ({doc}`33_catalogo_fao`), los componentes y el costo ({doc}`34_componentes`), los lotes y la
   proyección de redes a una flota ({doc}`35_lotes_proyeccion`), la guía de construcción para el
   taller ({doc}`36_construccion`) y las erratas del modelo original.
4. **Software**: motor, informes y planos, aplicación web, API, despliegue en línea y cómo citar.

Los capítulos son notebooks ejecutables: el código y los números que muestran se recalculan cada vez
que se construye el libro.

## Modos de cálculo

El modelo original contiene erratas documentadas ({doc}`erratas`). Los cálculos pueden hacerse en
modo `excel` (reproduce exactamente el libro original, para validar) o `corrected` (fórmulas
corregidas, recomendado para diseñar). Cada capítulo indica qué modo usa.

## Cómo citar

> Giamportone, A. L. (2026). *Trawl Design Lab (trawlkit): diseño y dimensionamiento de redes de
> arrastre*. Universidad Tecnológica Nacional, Facultad Regional Tierra del Fuego.
> Zenodo. https://doi.org/10.5281/zenodo.23657981

Los metadatos completos y el DOI de cada versión están en {doc}`citar`.

Código bajo licencia MIT; documentación y datos bajo CC BY 4.0.
