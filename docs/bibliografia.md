# Bibliografía

Las referencias de este libro reconstruyen las fuentes que cita el modelo Excel original
(`legacy/Calculos_Red_FAO_A3.xlsx`). La hoja casi siempre nombra solo al autor del método, a
veces con un año (por ejemplo "Koyama 1974" o "Nomura"). Para cada uno se buscó la obra real
en catálogos de bibliotecas (CiNii Books, catálogos universitarios), en el repositorio de
documentos de la FAO, en Crossref y en las listas de referencias de artículos que aplican esas
mismas fórmulas, sobre todo MacLennan (1981), Kim (1984), Mukundan y Shahul Hameed (1995),
Vijayan y Baiju (2006) y Okello (2014). No se inventó ningún dato. Cada entrada de
`referencias.bib` indica en el campo `note` si está **verificada** (con la URL de la fuente
consultada) o si queda **A VERIFICAR**, y en ese caso explica qué falta. Algunas referencias
verificadas se apoyan en citas secundarias, es decir, en la lista de referencias de otro trabajo,
y así lo indica su nota.

```{bibliography}
:all:
```

## Referencias a verificar

| Clave | Qué falta | Mejor pista |
|---|---|---|
| `fridman1973` | Hay dos obras de Fridman de 1973: el artículo de *Fischereiforschung* 11(2) y el libro *Theory and Design of Commercial Fishing Gear* (IPST). Falta saber cuál usa el Excel. Del artículo faltan las páginas finales. | <https://api.crossref.org/works/10.1016/0165-7836(81)90004-7> · <https://psnz.umt.edu.my/seal/Record/0000004547/Details> |
| `koyama1984` | No se encontró ninguna obra de Koyama de 1984. La fórmula con coeficiente 8 coincide con la que Kim (1984) atribuye a Koyama (1962, 1967 y 1974). | <https://koreascience.or.kr/article/JAKO198422105925357.page> |
| `tauti1974` | No se encontró el trabajo de "Tauti, Nomura y Shu (1974)". Se citó la teoría original de Tauti (1934) como la obra más cercana. | <https://doi.org/10.2331/suisan.3.1> |
| `hamuro` | Se confirmó que Hamuro trabajó sobre redes de arrastre, pero no la obra de la que salen las fórmulas de tiro y resistencia. | <https://doi.org/10.2331/suisan.25.103> |
| `robertson1981` | No se encontró la fórmula para redes semipelágicas. Solo consta que Robertson dirigió ensayos semipelágicos en Aberdeen. | <https://www.bodc.ac.uk/resources/inventories/cruise_inventory/report/7971/> |
| `aberdeen` | El Excel no da autor ni obra. Las candidatas son MacLennan (1979, Working Paper 79/6) y Ferro (1981, Scottish Fisheries Information Pamphlet 5). | <https://epubs.icar.org.in/index.php/FT/article/download/16634/8029/36339> |
| `dickson` | Falta el año que usa el Excel y la versión (ICES C.M. 1979/B:26 o informe técnico de Bergen de 1980). Faltan también las páginas. | <https://imr.brage.unit.no/imr-xmlui/handle/11250/103361> |
| `martini` | Libro confirmado (Okonski y Martini, 1987), pero no el "nivel 2" ni la edición, argentina o mexicana. | <https://sibi.upn.mx/bib/37552> |
| `suzuki1982` | No se encontró la fuente. Es la AV = (4/90)·circunferencia. | <https://ci.nii.ac.jp/books/search?q=Japan+International+Cooperation+Agency+fishing> |
| `izzo` | Es la obra de Izzo (INIDEP) más cercana confirmada. No consta que contenga los porcentajes de abertura vertical. | <https://marineinfo.org/id/publication/228563> |
| `perezaguila2010` | No se encontró la fuente. Son la solidez y el diámetro del cable en función de NHP. | — (buscar tesis o cursos de ingeniería pesquera) |
| `fujiishi` | Se confirmó el autor, pero no que el artículo contenga el "factor de largo". | <https://agris.fao.org/search/en/records/6471238f9dd8810bf64d1141> |
| `nomurayamazaki` | La obra existe, pero falta confirmar la tabla α → CD del cable. | <https://repository.seafdec.org/handle/20.500.12066/7261> |
| `warpshare` | No se encontró la fuente de la tabla Craig/Podeur/Hansen/Gudnasson. Hay un dato del mismo orden en Wileman (1984). | <https://www.grocentre.is/static/gro/publication/274/document/frederik13prf.pdf> |
| `giamportone2024` | ResearchGate bloqueó el acceso (HTTP 403). Faltan la fecha exacta, el tipo de documento y el DOI. | <https://www.researchgate.net/publication/379257264> |
