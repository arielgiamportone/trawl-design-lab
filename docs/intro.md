# trawl-design-lab

**Diseño y dimensionamiento de redes de arrastre de fondo: teoría, cálculo reproducible y software.**

Este libro documenta `trawlkit`, un motor de cálculo abierto que reimplementa y extiende el modelo
de diseño de la red de arrastre FAO A-3 para pesqueros de 150–180 HP del Canal Beagle, desarrollado
originalmente en un libro de Excel por Ariel Luján Giamportone (Ingeniería Pesquera, UTN Ushuaia)
{cite:p}`giamportone2024`.

## Para quién es

- **Ingenieros pesqueros y estudiantes**: cada etapa del cálculo se presenta con su teoría, sus
  ecuaciones, los coeficientes empíricos y la referencia del autor que los propuso.
- **Diseñadores y armadores**: el caso de estudio muestra cómo pasar de la potencia del buque a la
  red, el aparejo, la flotación, el lastre y el cable, y cuál es la velocidad remolcable.
- **Desarrolladores**: la última parte describe la arquitectura del software, los informes, la API
  y la aplicación web.

## Probar la aplicación

La aplicación web está publicada junto a este libro:
**<https://arielgiamportone.github.io/trawl-design-lab/app/>**. Calcula en el navegador el caso
FAO A-3 (o el que se arme), con gráficos, plano, optimización y simulación, usando la API pública
del motor. El primer cálculo puede tardar hasta un minuto si la API estaba dormida (plan gratuito;
ver {doc}`despliegue`).

## Cómo leerlo

1. **Fundamentos**: el problema y la nomenclatura.
2. **Teoría y métodos**: un capítulo por etapa, en el mismo orden en que se resuelve el diseño. Cada
   capítulo ejecuta el cálculo con `trawlkit` y lo verifica contra el libro Excel original. Cierran
   la parte la optimización del tamaño de la red y de la velocidad ({doc}`20_optimizacion`) y la
   simulación de la forma de la red remolcada ({doc}`21_simulacion`).
3. **Caso de estudio y validación**: la red FAO A-3 estándar y modificada, la validación contra el
   Excel y contra el simulador DynamiT, y las erratas encontradas en el modelo original.
4. **Software**: motor, informes y planos, aplicación web, API y despliegue en línea.

Los capítulos son notebooks ejecutables: el código y los números que muestran se recalculan cada vez
que se construye el libro.

## Modos de cálculo

El modelo original contiene erratas documentadas ({doc}`erratas`). Los cálculos pueden hacerse en
modo `excel` (reproduce exactamente el libro original, para validar) o `corrected` (fórmulas
corregidas, recomendado para diseñar). Cada capítulo indica qué modo usa.

## Cómo citar

> Giamportone, A. L. (2026). *trawl-design-lab: diseño de redes de arrastre*.
> https://github.com/arielgiamportone/trawl-design-lab

Código bajo licencia MIT; documentación y datos bajo CC BY 4.0.
