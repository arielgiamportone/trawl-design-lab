# Fuentes del catálogo de redes FAO

Registro de la búsqueda y digitalización del catálogo de redes (Fase 12): qué documentos públicos
de la FAO traen planos de redes de arrastre, qué se transcribió de cada uno, qué se supuso y por
qué. Cada valor de cada red lleva además su propia procedencia (documento, página y figura) en el
archivo de la red (`src/trawlkit/data/nets/<id>.yaml`).

## Alcance de la búsqueda

Los dos catálogos clásicos de la FAO no se encontraron en línea como texto completo:
el *FAO Catalogue of Fishing Gear Designs* {cite:p}`faocatalogue` y el *FAO Catalogue of
Small-Scale Fishing Gear* {cite:p}`faosmallscale1987`. Tampoco el *Fisheries Technical Paper 189*,
*Bottom trawls for small-scale fishing* (Brabant y Nédélec, 1979), del que sólo hay registros de
biblioteca. La búsqueda se hizo en fao.org (`fao.org/4/…`, `fao.org/docrep/…`) y en el
repositorio abierto de la FAO, entre octubre de 2026 y la fecha de este registro, con consultas
sobre planos de arrastre de fondo, de gran abertura, de pareja y pelágicos.

Los documentos con planos legibles que sí están publicados son los de la tabla. Todos usan la
notación de la FAO para planos de red: mallas de cada borde, alto en mallas, mallero estirado,
material y Rtex del hilo, cortes (`AB`, `1N2B`…) y largos de relingas en metros.

## Documentos

| Documento | Clave | URL | Planos de red | Otros |
|---|---|---|---|---|
| Prado y Dremière (1990), *Fisherman's Workbook*, FAO/Fishing News Books | `prado1990` | https://www.fao.org/4/ah827e/AH827E04.htm | Arrastre de fondo de 2 paneles para 50–70 hp (fig. AH827E132); arrastre pelágico de 4 paneles para 120–150 hp (fig. AH827E133) | Aparejo de ambos |
| Pajot y Crockett (1980), *Fishing trials with high-opening bottom trawls in Palk Bay, Tamil Nadu*, BOBP/WP/10 | `bobpwp10` | https://www.fao.org/4/ad950e/ad950e00.pdf | Ap. 3: gran abertura, un barco, 360 mallas de 160 mm; ap. 5: pareja, 480 × 160 mm; ap. 6: pareja, 680 × 60 mm | Ap. 4: portón de 1,30 × 0,65 m, 50 kg |
| Pajot y Crockett (1981), *Trials of two-boat bottom trawling in Bangladesh*, BOBP/WP/13 | `bobpwp13` | https://www.fao.org/4/ad953e/ad953e00.pdf | Ap. 3: pareja, 464 × 80 mm; ap. 4: pareja, 368 × 120 mm | Aparejo de pareja |
| Pajot, Crockett, Pandurangan y Ramamoorthy (1982), *Further trials of mechanised trawling for food fish in Tamil Nadu*, BOBP/WP/20 | `bobpwp20` | https://www.fao.org/4/ad960e/ad960e00.pdf | Ap. 1: pescado y camarón, un barco; ap. 2: gran abertura, un barco; ap. 3: gran abertura, pareja | Portones y aparejo de los aps. 1 y 2 |
| Schärfe (1983), *Midwater trawling trials for lantern fish… Gulf of Oman*, FI:DP/GLO/82/001 | `scharfe1983` | https://www.fao.org/4/x6567e/x6567e00.htm | Aps. 5 a 8: arrastres pelágicos de 4 paneles (krill 1420 × 200 mm; Harstad 1436 × 200 mm; krill con boca de 800 y 1600 mm) | Aparejo |

Documentos revisados que **no** traen planos de red completos:
- BOBP/WP/21 (cubierta y maquinaria);
- BOBP/REP/37 (sólo una tabla de especificaciones generales);
- BOBP/MIS/04 (selectividad del copo, sin plano);
- el *Fisheries Technical Paper 506* (descripción general de artes).

## Criterios de digitalización

- **Transcripto**: valor leído en la figura (mallas, alto, mallero, Rtex, cortes, relingas).
- **Derivado**: calculado de valores transcriptos, con la fórmula en la nota; por ejemplo, el
  diámetro del hilo a partir del Rtex y el material, o el U1 a partir del largo de relinga y las
  mallas del borde.
- **Supuesto**: valor que el plano no da y el motor necesita, por ejemplo el U1 del cuerpo. Va
  marcado y con la razón; nunca sin marca.
- Las redes cuyas lecturas no cierran con el validador quedan en estado `draft` y no se publican
  en la aplicación hasta resolverse.
- **Derechos**: los documentos son © FAO. El catálogo guarda sólo los datos técnicos transcriptos
  con su cita y enlace; no reproduce las figuras.

## Registro por red

Estado al cerrar la Fase 12 (detalle valor por valor en la procedencia de cada red y en el
capítulo {doc}`33_catalogo_fao`):

| Red | Fuente | Estado | Lecturas dudosas y supuestos |
|---|---|---|---|
| `fao_wb_bt2p_60hp` | Workbook, AH827E132 | publicada | profundidad supuesta (30 m) |
| `bobp_wp13_pair_ho80` | WP/13 ap. 3 | publicada | F: 80 filas (leído 60); D: 1N4B; corte del ala C dudoso |
| `bobp_wp13_pair_ho120` | WP/13 ap. 4 | publicada | filas del copo del vientre (de las del dorso) |
| `bobp_wp10_ho360x160` | WP/10 ap. 3 y 4 | publicada | filas del ala del dorso (45 por estaciones) |
| `bobp_wp10_pair_480x160` | WP/10 ap. 5 | publicada | Rtex del copo (único rótulo) |
| `bobp_wp10_pair_680x60` | WP/10 ap. 6 | publicada | fruncido de 18 % en el ala del vientre |
| `bobp_wp20_ho` | WP/20 ap. 2 | publicada | cortes de las puntas de ala |
| `bobp_wp20_pair_ho` | WP/20 ap. 3 | publicada | cortes de las alas (de WP/10 ap. 5) |
| `bobp_wp20_fish_shrimp` | WP/20 ap. 1 | borrador | escaneo de 107 ppp: bordes de alas y cielo supuestos |
| `scharfe_krill_1420x200` | Schärfe ap. 5 | publicada | filas con media malla redondeadas; alas de los costados no modeladas |
| `scharfe_harstad_1436x200` | Schärfe ap. 6 | borrador | empalme de 26 % (190 → 140 mm); copo supuesto |
| `scharfe_krill_front800` | Schärfe ap. 7 | publicada | dorso y vientre con alas distintas (mitades del plano) |
| `scharfe_krill_front1600` | Schärfe ap. 8 | borrador | alto del ala del vientre y Rtex del ala |
| pelágica de 4 paneles | Workbook, AH827E133 | no digitalizada | figura de 450 px: el frente de 800 mm no se lee |


## Componentes del arte (Fase 13)

El catálogo de componentes (`trawlkit.components`, `data/components/`) junta paño e hilo, cables
de acero, cabos, portones, boyas y cadenas. Cada ítem trae su fuente y la procedencia de cada
valor, y los de marca dicen a qué **genérico** equivalen.

| Clave | Fuente | Qué se toma | Cómo |
|---|---|---|---|
| `prado1990` | FAO *Fisherman's Workbook* | Hilos de PA, PE, PP y PES; cabos de PA, PE, PES, PP y combinados; cables 6x7, 6x12, 6x19 y 6x24; boyas; cadenas; portones por potencia (plano, oval, V y Süberkrüb) | Genéricos: ley ajustada a cada tabla (potencia o d²), valores *derivados* a tamaños estándar con el error del ajuste; boyas, cadenas y portones *transcriptos* |
| `garware_fisheries` | Garware Technical Fibres (India) | Paño de PE trenzado Sapphire y SNG; cabo X2 (PP/PE) | 6–8 tamaños por línea, *transcriptos* |
| `bridon2023` | Bridon-Bekaert, catálogo de pesca 2023 | Cables Marblue 6x19 y Dyform Starfish 6x26 | 4–5 tamaños por línea |
| `pfeifer_6x19w` | PFEIFER 6x19W-FC | Cables chicos de 6 a 16 mm | 6 tamaños |
| `zuniga2006` | FAO REBYC, flota camaronera del Caribe colombiano | Puertas planas de madera de 6'×28" a 10'×40" usadas en la flota | Medidas *transcriptas*, polar supuesta (la del portón plano) |
| `lange1993` | Lange (ICES 1993) | Sustentación máxima del portón plano (0,95) y en V (0,70–0,85) | Polar del portón en V *supuesta*: la del plano con el CL escalado |
| `giamportone2024` | Libro Excel de la A-3 | Cabos Moscuzza, cadenas Trawlex, cables 6x19 Seale, boyas, hilos PA y los dos portones con su polar | Procedencia *Excel* |

Criterios:

- **Datos puntuales**: de cada línea de producto de un fabricante se toman a lo sumo 10 tamaños,
  con la cita. No se copian tablas ni fichas completas, y ninguna ficha se guarda en el
  repositorio.
- **Genéricos**: lo que se consigue en cualquier ferretería naval. Sus valores salen de leyes
  ajustadas a las tablas de referencia, no de una marca.
- **Validador físico** (`trawlkit.components.check`): peso por metro contra diámetro, carga de
  rotura por mm², tenacidad del hilo, flotación frente al volumen de la esfera y polar del
  portón. Lo usa también la app para revisar los aportes de los usuarios.
- **Buscadas sin datos abiertos**: Hampidjan, Euronete, Vónin, Usha Martin, Cotesi, Morgère,
  Thyborøn, Injector y Ekkó publican rangos o piden la ficha por correo. Los proveedores
  latinoamericanos no publican fichas en línea; para ellos están los genéricos y los aportes.
- **Normas**: ISO 1805 (paño), ISO 2307 (cabos) e ISO 2408 / EN 12385-4 (cables) se citan como
  método de ensayo. Son pagas y sus tablas no se reproducen.
