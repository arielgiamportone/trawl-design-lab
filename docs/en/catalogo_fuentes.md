# Sources of the FAO net catalogue

Record of the search for and digitization of the net catalogue (Phase 12): which public FAO
documents carry trawl plans, what was transcribed from each one, what was assumed and why. Each
value of each net also carries its own provenance (document, page and figure) in the net's file
(`src/trawlkit/data/nets/<id>.yaml`).

## Scope of the search

The two classic FAO catalogues were not found online as full text: the *FAO Catalogue of Fishing
Gear Designs* {cite:p}`faocatalogue` and the *FAO Catalogue of Small-Scale Fishing Gear*
{cite:p}`faosmallscale1987`. Nor was *Fisheries Technical Paper 189*, *Bottom trawls for
small-scale fishing* (Brabant and Nédélec, 1979), of which there are only library records. The
search was made on fao.org (`fao.org/4/…`, `fao.org/docrep/…`) and in the FAO open repository,
between October 2026 and the date of this record, with queries on plans of bottom, high-opening,
pair and pelagic trawls.

The documents with legible plans that are published are those in the table. All of them use the
FAO notation for net plans: meshes of each edge, depth in meshes, stretched mesh size, material
and Rtex of the twine, cuts (`AB`, `1N2B`…) and rope lengths in metres.

## Documents

| Document | Key | URL | Net plans | Other |
|---|---|---|---|---|
| Prado and Dremière (1990), *Fisherman's Workbook*, FAO/Fishing News Books | `prado1990` | https://www.fao.org/4/ah827e/AH827E04.htm | 2-panel bottom trawl for 50–70 hp (fig. AH827E132); 4-panel pelagic trawl for 120–150 hp (fig. AH827E133) | Rigging of both |
| Pajot and Crockett (1980), *Fishing trials with high-opening bottom trawls in Palk Bay, Tamil Nadu*, BOBP/WP/10 | `bobpwp10` | https://www.fao.org/4/ad950e/ad950e00.pdf | App. 3: high-opening, one boat, 360 meshes of 160 mm; app. 5: pair, 480 × 160 mm; app. 6: pair, 680 × 60 mm | App. 4: otter board of 1.30 × 0.65 m, 50 kg |
| Pajot and Crockett (1981), *Trials of two-boat bottom trawling in Bangladesh*, BOBP/WP/13 | `bobpwp13` | https://www.fao.org/4/ad953e/ad953e00.pdf | App. 3: pair, 464 × 80 mm; app. 4: pair, 368 × 120 mm | Pair rigging |
| Pajot, Crockett, Pandurangan and Ramamoorthy (1982), *Further trials of mechanised trawling for food fish in Tamil Nadu*, BOBP/WP/20 | `bobpwp20` | https://www.fao.org/4/ad960e/ad960e00.pdf | App. 1: fish and shrimp, one boat; app. 2: high-opening, one boat; app. 3: high-opening, pair | Otter boards and rigging of apps. 1 and 2 |
| Schärfe (1983), *Midwater trawling trials for lantern fish… Gulf of Oman*, FI:DP/GLO/82/001 | `scharfe1983` | https://www.fao.org/4/x6567e/x6567e00.htm | Apps. 5 to 8: 4-panel pelagic trawls (krill 1420 × 200 mm; Harstad 1436 × 200 mm; krill with 800 and 1600 mm front) | Rigging |

Documents reviewed that do **not** carry complete net plans:
- BOBP/WP/21 (deck and machinery);
- BOBP/REP/37 (only a table of general specifications);
- BOBP/MIS/04 (codend selectivity, no plan);
- *Fisheries Technical Paper 506* (general description of gears).

## Digitization criteria

- **Transcribed**: value read from the figure (meshes, depth, mesh size, Rtex, cuts, ropes).
- **Derived**: computed from transcribed values, with the formula in the note; for example, the
  twine diameter from the Rtex and the material, or the U1 from the rope length and the meshes of
  the edge.
- **Assumed**: value that the plan does not give and the engine needs, for example the U1 of the
  body. It is marked and has its reason; never without a mark.
- Nets whose readings do not close with the validator stay in `draft` status and are not
  published in the application until resolved.
- **Rights**: the documents are © FAO. The catalogue keeps only the transcribed technical data
  with their citation and link; it does not reproduce the figures.

## Record per net

Status at the close of Phase 12 (value-by-value detail in the provenance of each net and in the
chapter {doc}`33_catalogo_fao`):

| Net | Source | Status | Doubtful readings and assumptions |
|---|---|---|---|
| `fao_wb_bt2p_60hp` | Workbook, AH827E132 | published | assumed depth (30 m) |
| `bobp_wp13_pair_ho80` | WP/13 app. 3 | published | F: 80 rows (read 60); D: 1N4B; cut of wing C doubtful |
| `bobp_wp13_pair_ho120` | WP/13 app. 4 | published | rows of the lower codend (from the upper ones) |
| `bobp_wp10_ho360x160` | WP/10 apps. 3 and 4 | published | rows of the upper wing (45 from the stations) |
| `bobp_wp10_pair_480x160` | WP/10 app. 5 | published | Rtex of the codend (single label) |
| `bobp_wp10_pair_680x60` | WP/10 app. 6 | published | 18 % gathering in the lower wing |
| `bobp_wp20_ho` | WP/20 app. 2 | published | cuts of the wing tips |
| `bobp_wp20_pair_ho` | WP/20 app. 3 | published | cuts of the wings (from WP/10 app. 5) |
| `bobp_wp20_fish_shrimp` | WP/20 app. 1 | draft | 107 dpi scan: wing and square edges assumed |
| `scharfe_krill_1420x200` | Schärfe app. 5 | published | rows with half meshes rounded; side wings not modelled |
| `scharfe_harstad_1436x200` | Schärfe app. 6 | draft | 26 % join (190 → 140 mm); codend assumed |
| `scharfe_krill_front800` | Schärfe app. 7 | published | upper and lower panels with different wings (halves of the plan) |
| `scharfe_krill_front1600` | Schärfe app. 8 | draft | depth of the lower wing and Rtex of the wing |
| 4-panel pelagic | Workbook, AH827E133 | not digitized | 450 px figure: the 800 mm front cannot be read |


## Gear components (Phase 13)

The components catalogue (`trawlkit.components`, `data/components/`) brings together netting and
twine, steel wire ropes, ropes, otter boards, floats and chains. Each item carries its source and
the provenance of each value, and the branded ones state which **generic** they are equivalent
to.

| Key | Source | What is taken | How |
|---|---|---|---|
| `prado1990` | FAO *Fisherman's Workbook* | PA, PE, PP and PES twines; PA, PE, PES, PP and combination ropes; 6x7, 6x12, 6x19 and 6x24 wire ropes; floats; chains; otter boards by power (flat, oval, V and Süberkrüb) | Generics: law fitted to each table (power or d²), values *derived* at standard sizes with the error of the fit; floats, chains and otter boards *transcribed* |
| `garware_fisheries` | Garware Technical Fibres (India) | Sapphire and SNG braided PE netting; X2 rope (PP/PE) | 6–8 sizes per line, *transcribed* |
| `bridon2023` | Bridon-Bekaert, fishing catalogue 2023 | Marblue 6x19 and Dyform Starfish 6x26 wire ropes | 4–5 sizes per line |
| `pfeifer_6x19w` | PFEIFER 6x19W-FC | Small wire ropes from 6 to 16 mm | 6 sizes |
| `zuniga2006` | FAO REBYC, shrimp fleet of the Colombian Caribbean | Flat wooden doors from 6'×28" to 10'×40" used in the fleet | Dimensions *transcribed*, polar assumed (that of the flat otter board) |
| `lange1993` | Lange (ICES 1993) | Maximum lift of the flat otter board (0.95) and V-board (0.70–0.85) | Polar of the V-board *assumed*: that of the flat board with the CL scaled |
| `giamportone2024` | Excel workbook of the A-3 | Moscuzza ropes, Trawlex chains, Seale 6x19 wire ropes, floats, PA twines and the two otter boards with their polar | *Excel* provenance |

Criteria:

- **Point data**: from each manufacturer's product line at most 10 sizes are taken, with the
  citation. Complete tables or data sheets are not copied, and no data sheet is stored in the
  repository.
- **Generics**: what can be bought at any ship chandler. Their values come from laws fitted to
  the reference tables, not from a brand.
- **Physical validator** (`trawlkit.components.check`): weight per metre against diameter,
  breaking load per mm², twine tenacity, buoyancy against the volume of the sphere and otter board
  polar. The app also uses it to review user contributions.
- **Searched without open data**: Hampidjan, Euronete, Vónin, Usha Martin, Cotesi, Morgère,
  Thyborøn, Injector and Ekkó publish ranges or ask for the data sheet by e-mail. Latin American
  suppliers do not publish data sheets online; for them there are the generics and the
  contributions.
- **Standards**: ISO 1805 (netting), ISO 2307 (ropes) and ISO 2408 / EN 12385-4 (wire ropes) are
  cited as test methods. They are paid and their tables are not reproduced.
