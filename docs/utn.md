# Nacido en la UTN

```{image} _static/img/emblema-utn-pesquera.svg
:alt: Emblema del proyecto: la costa atlántica argentina con Mar del Plata, Puerto Madryn y Ushuaia, y una red de arrastre
:width: 260px
:align: right
```

Este proyecto nació en las aulas de **Ingeniería Pesquera de la Universidad Tecnológica Nacional
(UTN)**. Allí, en la Facultad Regional Tierra del Fuego, su autor hizo el primer trabajo en el que
aprendió a calcular una red de arrastre: el dimensionamiento de la red FAO A-3 para los pesqueros
de 150–180 HP del Canal Beagle {cite:p}`giamportone2024`.

## Del Excel a `trawlkit`

El cálculo se resolvió primero en un libro de Excel de unas 5 500 fórmulas, repartidas en hojas que
siguen el orden del diseño: potencia disponible, paños y cortes, mecánica de la red, dimensiones,
resistencia, portones, flotación, lastre y cables
([repositorio original](https://github.com/arielgiamportone/Trawl_net_model_in_Advanced_Excel),
[informe en ResearchGate](https://www.researchgate.net/publication/379257264)).

Ese libro es la base de `trawlkit`:

- **Migración y validación.** Cada fórmula se migró a Python y se validó contra los valores del
  Excel, con tolerancia relativa de 10⁻⁶ ({doc}`31_validacion_excel`).
- **Erratas.** Las erratas que aparecieron en la auditoría se documentaron y se corrigieron
  ({doc}`erratas`). El modo `excel` las sigue reproduciendo para comparar.
- **Generalización.** El cálculo se extendió a cualquier red definida por paneles, desde el
  catálogo FAO ({doc}`33_catalogo_fao`) hasta las planillas de una flota entera
  ({doc}`35_lotes_proyeccion`).
- **Herramientas nuevas.** Se sumaron la optimización, la simulación de la forma, la selectividad y
  los componentes con su costo, y una aplicación que funciona en el teléfono sin conexión.

La meta sigue siendo la del trabajo práctico original: que un estudiante, un técnico o un patrón
pueda saber qué red puede remolcar un buque y cómo armarla, y entender por qué.

## Las tres Facultades de Ingeniería Pesquera

La UTN dicta Ingeniería Pesquera en tres Facultades Regionales sobre el Mar Argentino. El proyecto
está dedicado a las tres:

| Facultad Regional | Ciudad | Sitio |
|---|---|---|
| **FRTDF** · Tierra del Fuego | Ushuaia | <https://www.frtdf.utn.edu.ar/> |
| **FRCh** · Chubut | Puerto Madryn | <https://www.frch.utn.edu.ar/> |
| **FRMDP** · Mar del Plata | Mar del Plata | <https://mdp.utn.edu.ar/> |

Para sus cátedras, la app tiene un modo **«Aula UTN»**: ejercicios con corrección, laboratorios
guiados sobre la app y un aula con cursos, tareas y notas ({doc}`38_docentes`).

Las tres están sobre puertos pesqueros: Mar del Plata, sobre la plataforma bonaerense; Puerto
Madryn, sobre el golfo Nuevo; Ushuaia, sobre el Canal Beagle. Este libro, el motor y sus datos
son abiertos (MIT y CC BY 4.0) para que se usen en sus cátedras, prácticas y proyectos finales.

```{note}
El emblema es un dibujo propio del proyecto: la costa atlántica con las tres sedes y la silueta de
una red de arrastre. No es un logo oficial de la UTN ni de sus Facultades.
```
