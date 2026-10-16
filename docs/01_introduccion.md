# Introducción

## La red de arrastre de fondo

Una red de arrastre de fondo es un embudo de paño remolcado por un buque sobre el fondo marino. Su
boca se mantiene abierta horizontalmente por dos **portones** que, por efecto hidrodinámico, se
separan al avanzar, y verticalmente por la **flotación** de la relinga superior (lima) y el
**lastre** de la relinga inferior (burlón). El buque debe entregar tiro suficiente para vencer la
resistencia de la red, del aparejo y de los cables a la velocidad de pesca.

Diseñar la red es, por lo tanto, un problema de equilibrio: la red más grande que el buque puede
remolcar a la velocidad que la especie objetivo exige, con aberturas suficientes y un aparejo que
la mantenga en su geometría de trabajo.

## La red FAO A-3

La FAO publicó una serie de diseños de redes de arrastre para embarcaciones pequeñas y medianas
{cite:p}`faocatalogue`. La A-3 es una red de fondo de dos caras para buques de alrededor de
150–180 HP. El modelo de este libro la dimensiona panel por panel (alas, cuadro, cuerpo y bolsa) y
compara dos variantes:

- **estándar**, con bolsa de malla de 40 mm;
- **modificada**, con bolsa de malla de 30 mm para pequeños crustáceos.

## El caso del Canal Beagle

El caso de estudio apunta a la **langostilla** (*Munida gregaria* / *M. subrugosa*), a unos 40 m de
profundidad sobre fondo intermedio, con pesqueros de rada o ría de hasta 9 m de eslora y
150–180 BHP {cite:p}`giamportone2024`.

## La cadena de cálculo

El diseño se resuelve en etapas, cada una con su capítulo:

1. Potencia y tiro disponible del buque ({doc}`10_potencia`).
2. Paños, armado y cortes ({doc}`11_panos_y_cortes`).
3. Mecánica de la red: superficies, solidez y peso ({doc}`12_mecanica_red`).
4. Dimensiones principales y relingas ({doc}`13_dimensiones`).
5. Resistencia de la red por 13 métodos ({doc}`14_resistencia`).
6. Portones y aparejo ({doc}`15_portones_aparejo`).
7. Aberturas horizontal y vertical ({doc}`16_aberturas`).
8. Flotación y lastre ({doc}`17_flotacion_lastre`).
9. Cables de remolque ({doc}`18_cables`).
10. Ventana de velocidad remolcable ({doc}`19_ventana_velocidad`).

## Del Excel al software

El modelo nació como un libro de Excel de 13 hojas y unas 5 500 fórmulas. `trawlkit` lo traduce a
funciones documentadas y verificadas: cada función cita la celda del Excel que reproduce y los tests
comparan los resultados con los valores del libro original con una tolerancia relativa de 10⁻⁶
({doc}`31_validacion_excel`).
