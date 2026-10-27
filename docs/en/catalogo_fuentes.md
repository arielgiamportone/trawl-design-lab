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
| Roth and Rubio (2022), *Evaluación de la red presentada por la empresa Pesquera Deseado SAU*, INIDEP ITO 043/22 | `roth2022ito043` | https://fisheryprogress.org/sites/default/files/documents_actions/ITO_043_2022_LIB_Roth_Pesquera_Deseado.pdf | Figs. 4 and 5: shrimp outrigger nets exported from DynamiT (top, bottom and side; Phase 19.5) | Outrigger rigging (70 m bridle, 540 kg doors) and DynamiT results |
| SEAFDEC (2016), *The Catalogue Bottom Trawl Net Designs of Thailand*, TD/RES/141 | `seafdec2016thai` | https://repository.seafdec.or.th/handle/20.500.12067/1826 | 102 redrawn plans (embedded 96 dpi image); plan 03: shrimp beam trawl (Phase 19.5); plans 21, 22, 30, 31, 33, 35, 38 and 39 (Phase 19.6) | Vessel length and power; no floats, ballast, doors, outriggers, beam or shoes |
| Bullis (1951), *Gulf of Mexico Shrimp Trawl Designs*, Fishery Leaflet 394 | `bullis1951` | https://spo.nmfs.noaa.gov/sites/default/files/legacy-pdfs/leaflet394.pdf | Figs. 7, 9 and 10: 40 ft and 100 ft flat trawls and 74 ft balloon trawl (not digitized, Phase 19.6) | Doors of 5, 8 and 12 ft (length only) |
| Gutherz, Serra and Klima (1974), *Design and Materials Used in Construction of a 16-Foot Shrimp Trawl*, Fishery Facts 9 | `gutherz1974` | https://spo.nmfs.noaa.gov/sites/default/files/legacy-pdfs/fishfact09.pdf | 16 ft flat try-net (not digitized, Phase 19.6) | 30 × 15 in door, in the component catalogue |
| Arkley (1987), *Fishing gear handling trials of a twin-rig trawling system…*, Seafish IR 1310 | `arkley1987ir1310` | https://www.seafish.org/media/xlcdrq2k/ir1310.pdf | Fig. 5: 380 × 70 mm twin net (scan; not digitized) | 125 kg centre sledge and bridles |

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

Status at the close of Phase 12, with the nets of Phases 19.5 and 19.6 at the end (value-by-value
detail in the provenance of each net and in the chapter {doc}`33_catalogo_fao`):

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
| `inidep_ito043_tangonera_inidep` | INIDEP ITO 043/22 fig. 5 | draft | Dyneema body–codend seam (20 %); cut labels 3N4B, 19N7B and 5N1B that do not give the width change; sides shared out by length; front part of the side not modelled; vessel and door assumed |
| `inidep_ito043_tangonera_empresa` | INIDEP ITO 043/22 fig. 4 | draft | body–codend seam (20 %); top panel cut; overprinted wing label; sides shared out by length |
| `seafdec_03_beam_shrimp` | SEAFDEC 2016 plan 03 | draft | 32 mm codend joined 1:1 to the 51 mm body (37 %); U1 assumed; Rtex from denier |
| 380 × 70 mm twin | Seafish IR 1310 fig. 5 | not digitized | scan in British notation (rows of half meshes, S/SB/SK cuts, half-panel counts) |
| `seafdec_31_outrigger_shrimp` | SEAFDEC 2016 plan 31 | published | wing rope labels (10.00 and 11.20 m) that do not add up to the totals: wing derived from the total; 8/9 joins of 5 and 12 % |
| `seafdec_33_outrigger_shrimp` | SEAFDEC 2016 plan 33 | published | 6/7 join of 12 %; no assumed value |
| `seafdec_38_outrigger_shrimp` | SEAFDEC 2016 plan 38 | published | wings read 1N2B (the widening calls for 1N3B); 1/1 join of 17 % |
| `seafdec_39_outrigger_shrimp` | SEAFDEC 2016 plan 39 | published | 38 mm body read 2N2B (calls for 1N2B); footrope bosom label hidden (0.30 m from the total); 1/1 joins of 12 and 16 % |
| `seafdec_30_beam_shrimp` | SEAFDEC 2016 plan 30 | published | 20 mm codend joined 1:1 to the 25 mm body (20 %, at the threshold); two beams assumed |
| `seafdec_35_outrigger_shrimp` | SEAFDEC 2016 plan 35 | draft | 25 mm codend joined 1:1 to the 38 mm body (34 %); plan 36 is the same |
| `seafdec_21_otter_fish` | SEAFDEC 2016 plan 21 | draft | 19 mm codend joined 4/5 to the 38 mm body (38 %); wing tip drawn as a vertex (1 mesh assumed) |
| `seafdec_22_otter_fish` | SEAFDEC 2016 plan 22 | draft | 1/1 join from 80 to 60 mm and 2/3 from 38 to 19 mm (25 %); 32 mm combination footrope (the engine takes the 24 mm one) |
| three Bullis (1951) nets | NOAA FL 394 figs. 7, 9 and 10 | not digitized | wings sewn along the body taper, dog-ears and jibs: outside the engine's panel model; cotton twine in "thread" numbers with no citable Rtex conversion |
| 16 ft try-net | NOAA Fishery Facts 9 | not digitized | triangular body ending in a point with side wings sewn along it; only the door was loaded |


## Nets from public plans (Phase 19.6)

**Spot data** were loaded: representative nets of each rig and vessel size, not whole catalogues.

**What was loaded.** Eight nets from the SEAFDEC Thai catalogue {cite:p}`seafdec2016thai`:

- five shrimp outrigger nets ("otter with boom") for vessels of 13.5 to 20 m and 75 to 150 hp
  (plans 31, 33, 35, 38 and 39); plan 36 is the same as 35, and 34 and 37 repeat the layout with
  1/1 joins down to the codend;
- shrimp beam trawl no. 30 (11 m, 165 hp), added to no. 03 of Phase 19.5;
- two bottom otter trawls for fish (plans 21 and 22, 250 and 365 hp).

Each plan was read from the embedded image (563 × 777 px, 96 dpi), composited on white and
enlarged 2 to 8 times; each number was checked against the cuts (the width change the cut gives
over the panel's rows), the joining ratios printed on the plan and the sum of the ropes
(headrope = 2 × wing + bosom). Derived values are U1 (bosom rope over the stretched bosom netting,
per face), Rtex (n·den/9 from the denier) and the twine diameter; assumed values are the number of
beams of the beam trawl and, in the two fish nets, the mesh size of the wing tip and its vertex
(1 mesh instead of 0, because the simulator needs an edge). Five nets close (published) and three
stay as drafts because the plan joins panels of very different mesh sizes, such as the codend,
1/1 or with a short ratio.

**Door.** The 30 × 15 in door of the NOAA 16 ft try-net {cite:p}`gutherz1974` entered the
component catalogue (`door_noaa_ff9_30x15in`, flat wooden type): *transcribed* dimensions,
*derived* area and the Seafish flat-door polar *assumed*; the document does not give the weight.

**What was not loaded and why.**

- **Bullis (1951)** {cite:p}`bullis1951`: the three Gulf of Mexico nets (40 ft flat, 100 ft
  "Texas" flat and 74 ft balloon) sew the wings along the body taper and have jibs and dog-ears;
  the engine builds the wings on the mouth edge of the first panel (or sides by stations, in
  4-panel nets), so translating them would require inventing an equivalent net. Moreover, the
  cotton twine is given as "thread" numbers (15, 18, 42) and no citable conversion to Rtex was
  found in the sources reviewed.
- **Gutherz, Serra and Klima (1974)**: the 16 ft net has the same topology (a 130-mesh
  triangular body ending in a point, with 30 × 178 mesh wings sewn along it as sides); only its
  door was loaded.
- **SEAFDEC, other beam trawl plans** (01, 02, 04, 05, 06 and 84): multi-panel nets, wings wider
  than the body edge (02, 04 and 05: no bosom left), or bodies with V cuts that do not fit the
  2-panel model.
- **SEAFDEC, other fish trawls**: those reviewed (17 from 2002, 48 and 60 from 2016) join almost
  all body panels 1/1 with decreasing mesh size (20–25 % gathers at each join); they would stay as
  drafts, like 21 and 22.
- **INIDEP ITO 043/2022**: fig. 5 was re-read enlarged twice. The numbers of the rear body and the
  codend are legible beyond doubt (40 meshes of 120 mm in the top, 61 in the bottom, 17 in each
  side and 100 + 100 of 60 mm in the codend) and the plan prints no joining ratio: the perimeter of
  the body at that station (16.9 m stretched) still does not close with the codend (12.0 m). Both
  nets stay as drafts.

**What remains.** The Seafish plates (twin nets of IR 1310 and SR 336), the Panicker et al. (1977)
plan and the REBYC Cuba plans, already identified in Phase 19.5; and a documented conversion of
cotton thread numbers to Rtex, to load the NOAA nets once the engine supports wings sewn along the
body.

## Gear components (Phase 13)

The components catalogue (`trawlkit.components`, `data/components/`) brings together netting and
twine, steel wire ropes, ropes, otter boards, floats and chains. Each item carries its source and
the provenance of each value, and the branded ones state which **generic** they are equivalent
to.

| Key | Source | What is taken | How |
|---|---|---|---|
| `prado1990` | FAO *Fisherman's Workbook* | PA, PE, PP and PES twines; PA, PE, PES, PP and combination ropes; 6x7, 6x12, 6x19 and 6x24 wire ropes; floats; chains; otter boards by power (flat, oval, V and Süberkrüb) | Generics: law fitted to each table (power or d²), values *derived* at standard sizes with the error of the fit; floats, chains and otter boards *transcribed* |
| `garware_fisheries` | Garware Technical Fibres (India) | Sapphire and SNG braided PE netting; 380 D, 500 D, Sapphire twisted and 210 D nylon twisted netting (Phase 19.2); X2, Maxima, PP, PE and Maxibraid ropes | 6–8 sizes per line, *transcribed*; the twisted netting as a *draft* (the data sheet gives no diameter: *assumed* with the *Workbook* fit) |
| `hampidjan_catalogue` | Hampidjan fishing catalogue (iPaper viewer, 2023) | Magnet, Advant, Utzon and Primanet netting; Nylex, Kraft, Danline, DynIce 75 and Prima ropes; Randers Reb and Oliveira wire ropes; Trygg and Trawlex chains; Green Pin shackles; Atlantic Floats floats (Phase 19.2) | 3–8 sizes per line, read on the image of each page; elongation at break and *derived* EA |
| `bridon2023` | Bridon-Bekaert, fishing catalogue 2023 | Marblue 6x19, Dyform Starfish 6x26 and (Phase 19.2) Dyform 6x26, SeaBeam 6x26 and 6x7 wire ropes | 2–6 sizes per line |
| `gunnebo_llz` | Gunnebo Industries / Kito Crosby | LLZ grade 6 galvanised long-link chain (Phase 19.2) | 7 sizes |
| `crosby_g209` | Crosby, general catalogue p. 24 | G-209 shackles (Phase 19.2) | 10 sizes |
| `pfeifer_6x19w` | PFEIFER 6x19W-FC | Small wire ropes from 6 to 16 mm | 6 sizes |
| `zuniga2006` | FAO REBYC, shrimp fleet of the Colombian Caribbean | Flat wooden doors from 6'×28" to 10'×40" used in the fleet | Dimensions *transcribed*, polar assumed (that of the flat otter board) |
| `gutherz1974` | NOAA Fishery Facts 9 (Gutherz, Serra and Klima 1974) | 30 × 15 in flat wooden door of the 16 ft try-net (Phase 19.6) | Dimensions *transcribed*, polar assumed (that of the flat otter board), no published weight |
| `lange1993` | Lange (ICES 1993) | Maximum lift of the flat otter board (0.95) and V-board (0.70–0.85) | Up to Phase 19.2, the *assumed* V-board polar (that of the flat board with the CL scaled); since 19.3 only a reference |
| `sfia1993` | Seafish/IFREMER/DIFTA (1993), *Otterboard Performance and Behaviour* | 26 polar sheets of flume tank models (Phase 19.3); primary source of the flat and oval polars of the Excel workbook | Polars *transcribed* from the image of each page; per type, the sheet as it is or a mean (*derived*) |
| `mellibovsky2018` | Mellibovsky et al. (2018), *Ocean Eng.* 149 | Polars of the Thyborøn 15 VF and the Grilli Fly in the flume tank and the wind tunnel (Phase 19.3) | Tables *transcribed*; the Süberkrüb polar, a *derived* fit |
| `vonin_doors` | Vónin, product pages | Storm 2, Tornado and Twister otter boards (Phase 19.3) | Area and weight *transcribed*, 8–10 sizes per line; dimensions and polar *assumed* |
| `morgere2025` | Morgère, 2025 catalogue | OvalFoil, PolyFoil and PFPE otter boards (Phase 19.3) | Area (and PFPE length) *transcribed*, 10 sizes per line; no weight («sur demande»); dimensions and polar from the Seafish sheet of the same design, *assumed* |
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
- **Searched without open data**: Euronete, Vónin (its catalogue is Hampidjan's), Usha Martin, Cotesi, Morgère,
  Thyborøn, Injector and Ekkó publish ranges or ask for the data sheet by e-mail. Latin American
  suppliers do not publish data sheets online; for them there are the generics and the
  contributions.
- **Standards**: ISO 1805 (netting), ISO 2307 (ropes) and ISO 2408 / EN 12385-4 (wire ropes) are
  cited as test methods. They are paid and their tables are not reproduced.
