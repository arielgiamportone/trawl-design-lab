# Mapa de fórmulas: Excel → trawlkit

Inventario bloque a bloque de `legacy/Calculos_Red_FAO_A3.xlsx` (13 hojas). Para cada bloque se
indica el rango de celdas, la fórmula representativa (tal como está en el libro, con referencias
abreviadas), el método o autor citado en la hoja, el módulo/función destino en `trawlkit` y, si
aplica, la clave de errata registrada en `src/trawlkit/compat.py` (`ERRATA`).

Los valores cacheados de todos estos bloques están en `tests/golden/*.json`, generados por
`tools/extract/golden.py` (un JSON por hoja; las claves `snake_case` en inglés son estables y las
referencian los tests del motor). Las tablas de velocidad usan siempre el vector
`1.0, 1.5, …, 5.0 kn` (9 valores).

Convenciones: `Std` = red FAO A-3 estándar; `Mod` = variante modificada para crustáceos (bolsa de
30 mm); `RN` = resistencia de la red; `FT` = tiro disponible; `Ss` = superficie sólida; `St` =
superficie de trabajo; `d/l` = índice de filtración (Ø hilo / mallero); `DPA` = distancia entre
puntas de alas; `AV`/`AH` = abertura vertical/horizontal; `Ls` = cable filado.

Abreviaturas de hojas en las fórmulas: `Pot!` = Potenc disponible para arrastre, `PotOK!` = Potencia
Disponible Arrastre OK, `P!` = Paños de red y cortes, `Cab!` = Cables Y Cabulleria, `Mec!` = Mecánica
de la Red, `Dim!` = Dimensiones de la Red, `Res!` = Resistencia de la RED, `Port!` = Portones y
aparejamiento, `Flot!` = Flotación y Lastre, `Rem!` = Cables de Remolque, `Tab!` = Tablas de
Referencias. `{…}` marca fórmulas matriciales.

## Resumen hoja → módulo

| Hoja | Módulo destino | Golden JSON |
|---|---|---|
| Especie Blanco, Tipo de buques | `trawlkit.io` (spec YAML: `species`, `vessel`) | `especie_blanco`, `tipo_de_buques` |
| Potenc disponible para arrastre, Potencia Disponible Arrastre OK | `trawlkit.vessel`, `trawlkit.power` | `potenc_disponible_para_arrastre`, `potencia_disponible_arrastre_ok` |
| Paños de red y cortes | `trawlkit.netting` | `panos_de_red_y_cortes` |
| Cables Y Cabulleria | `src/trawlkit/data/ropes.yaml`, `trawlkit.rigging.warps` | `cables_y_cabulleria` |
| Mecánica de la Red | `trawlkit.net`, `trawlkit.rigging.spread` | `mecanica_de_la_red` |
| Dimensiones de la Red | `trawlkit.dimensions` | `dimensiones_de_la_red` |
| Resistencia de la RED | `trawlkit.drag` | `resistencia_de_la_red` |
| Portones y aparejamiento | `trawlkit.rigging.doors`, `trawlkit.rigging.bridles` | `portones_y_aparejamiento` |
| Flotación y Lastre | `trawlkit.rigging.floats`, `trawlkit.rigging.ballast` | `flotacion_y_lastre` |
| Cables de Remolque | `trawlkit.rigging.warps` | `cables_de_remolque` |
| Tablas de Referencias | `src/trawlkit/data/reference/*.csv`, `trawlkit.materials` | `tablas_de_referencias` |

## Grafo de dependencias entre hojas

```
Especie Blanco ──► Mecánica (profundidad) ──► Portones (Ls) ──► Cables de Remolque
Tipo de buques ──► Portones (distancia pastecas) ──► Cables de Remolque
Potenc disponible ──► Potencia OK ──► Portones (ROB), Flotación (F1), Cables de Remolque (Rw %)
Paños ──► Mecánica (d/l, Ss, St, pesos) ──► Dimensiones ──► Resistencia ──► Potencia OK (RN)
Tablas ──► Paños (cortes), Cables Y Cabulleria, Portones (portón), Mecánica (Ls/d)
Resistencia (Aberdeen demersal, cols N/O) ──► Potencia OK, Mecánica, Portones, Flotación, Remolque
```

El libro es circular en un punto: `Res!C282:D290` (Dickson) usa `Mec!P164:P172` (DPA Fridman) y
`Mec!O272:O280` (AV Fridman), que a su vez usan `Res!N302:N310` (Aberdeen demersal). Como Dickson
no alimenta la columna Aberdeen, Excel lo resuelve sin iteración.

---

## 1. Especie Blanco → `trawlkit.io`

| Bloque | Celdas | Fórmula / contenido | Método | Destino | Errata |
|---|---|---|---|---|---|
| Especie objetivo | C3, H3 | `Langostilla`, `Munida gregaria / M. subrugosa` | — | `io.load_spec` → `species.name`, `species.scientific_name` | — |
| Profundidad de trabajo | E5 | `40` m (entrada; alimenta `Mec!D193`, `Port!D8`, `Rem!E33`, `Dim!F62`) | — | `species.depth_m` | — |
| Tipo de fondo | E6 | `Intermedio` (alimenta `Flot!F227`) | — | `species.bottom_type` | — |

## 2. Tipo de buques → `trawlkit.io`

| Bloque | Celdas | Fórmula / contenido | Método | Destino | Errata |
|---|---|---|---|---|---|
| Clase de buque | A1, A3, B4 | `Pesqueros De 150 a 180 BHP`, tipo 1 de rada/ría, eslora hasta 9 m | — | `vessel.class`, `vessel.loa_m` | — |
| Manga | B5 | `2.5` m (→ distancia entre pastecas `Port!D6`) | — | `vessel.beam_m` | — |
| Puntal | B6 | `1.8` m (→ `Rem!E33`) | — | `vessel.depth_m` | — |
| Desplazamiento | A7:A8 | etiquetas sin valor | — | `vessel.displacement_t` (opcional) | — |

## 3. Potenc disponible para arrastre → `trawlkit.vessel`, `trawlkit.power`

Dos bloques idénticos (150 BHP en filas 23-31, 180 BHP en filas 35-43).

| Bloque | Celdas | Fórmula representativa | Método | Destino | Errata |
|---|---|---|---|---|---|
| Reparto de energía (Fridman) | B4 | `Ptotal = RN + 2·RW + 2·ROB + RH` (texto) | Fridman | `power.total_towing_demand` | — |
| BHP en hélice | C25 / C37 | `150` / `180` (entrada) | — | `vessel.bhp` | — |
| HP nominales | C24 / C36 | `=C25+(C25*0.33)` | Fridman (1/3 se pierde antes de la hélice) | `vessel.nominal_hp` | — |
| HP para tiro de red | C26 / C38 | `=(C25*0.33)` | Fridman | `power.towing_hp` | — |
| Pérdidas | C27:C31 / C39:C43 | `=C25*{0.35, 0.27, 0.18, 0.17, 0.03}` (hélice, oleaje, rozamiento, estela, aire) | Fridman | `power.power_budget` | — |
| kW disponibles | E24:E31 / E36:E43 | `=C24*0.745` | — | `units.hp_to_kw` (0.745 en vez de 0.7457) | — |
| Velocidad de Almirantazgo | H27 / H38 | `=((C24*285)/(10^(2/3)))^(1/3)` (150) / `…/(12^(2/3))…` (180; el desplazamiento 10 t / 12 t está incrustado) | Fórmula del Almirantazgo | `vessel.admiralty_speed` | — |

## 4. Potencia Disponible Arrastre OK → `trawlkit.power`

| Bloque | Celdas | Fórmula representativa | Método | Destino | Errata |
|---|---|---|---|---|---|
| Constantes KF | D10, F10 | `=MID(E3,38,2)` → `"10"`; `=MID(E4,40,2)` → `"15"` (texto extraído de la nota; Excel lo coacciona a número) | Fridman | `src/trawlkit/data/reference` (`kf_fixed_pitch`, `kf_variable_pitch_nozzle`) | — |
| FT Fridman 150 HP | B10:G18 | `E10 =C10*(D10-(0.7*B10))` (PF), `G10 =C10*(F10-(0.7*B10))` (PV+T); `C10 =Pot!C25` | Fridman `Ft ≈ HP·(KF − 0.7·v)` | `power.fridman_towing_force(hp, speed_kn, kf)` | — |
| FT Fridman 180 HP | B22:G30 | ídem con `C22 =Pot!C37` | Fridman | `power.fridman_towing_force` | — |
| Resumen FT y RN | I8:O19 | `J11 =Res!N302*1000`, `K11 =Res!N317*1000`, `L11 =E10`, `M11 =G10`, `N11 =E22`, `O11 =G22` | — | `power.summary` (lo consumen Portones, Flotación, Remolque) | — |
| Bollard pull Prado 150 HP | A58:C63 | `B60 =(C10*0.9*(1.1/100)*1000)`; factores 1.10/1.20/1.25/1.40 (PF, PF+T, PV, PV+T); `C60 =B60/1000` | Prado & Dremiere (FAO) | `power.bollard_pull(bhp, propeller)` | — |
| Bollard pull Prado 180 HP | D60:E63 | `D60 =C22*0.9*(1.1/100)*1000` | Prado & Dremiere | `power.bollard_pull` | — |
| Factor K según potencia | H51:L55 | tabla estática K52:L55 (11.23/13.35/11.73/13.73 …) | Prado & Dremiere | `src/trawlkit/data/reference/bollard_pull_k.csv` | — |
| BP vía factor K | H57:L62 | `I59 =K52*(C10/1000)` [t], `J59 =(I59*100)/1.36` [HP] | Prado & Dremiere | `power.bollard_pull_k` | — |
| BP promedios | F56:G61, F63:G68 | `G58 =AVERAGE(B60,(I59*1000))` (150), `G65 =AVERAGE(E60,K59)*1000` (180) | — | `power.bollard_pull_avg` | — |
| Potencia nominal aparente (APN) | A71:C76 | `B73 =0.09*G58` | Prado & Dremiere | `power.apparent_nominal_power` | — |
| Potencia disponible para arrastre | I67:L77 | `K68 =0.75*0.2*B73` … `K77 =0.75*0.3*B76` (K = 0.20/0.25/0.28/0.30 según hélice y RPM) | Prado & Dremiere | `power.trawling_power` | — |
| BP when fishing (BPF) | A85:L96, C100:L111 | `C88 =(150*K68)/A88` (150 ≈ 75/0.5144, conversión HP→kgf·kn; no es el BHP: D88 usa 150 para 180 HP) | Prado & Dremiere | `power.bollard_pull_fishing(power_hp, speed_kn)` | — |
| Promedios BPF | B121:F131 | `C123 =AVERAGE(C88,E88,G88,I88,K88,C103)` (PF), `E123 =AVERAGE(E103,G103,I103,K103)` (PV) | — | `power.bollard_pull_fishing_avg` | — |
| Koyama | A160:L179 | `C169 =150*0.6`; `C170 =M165` (K=0.15); `C171 =C170*C169`; `C172 =C171*75`; `K171 =C172/H171` con `H171 =0.514`, `H172 =(G172*H171)/G171` | Koyama (EHP = K·BHP_F) | `power.koyama_pull(bhp, k, speed)` | — |
| Nomura | A201:L224 | `L212 =AVERAGE(MID(L208,1,4),…)`; `E216 =(L213*L205*L206*MID(L208,1,4)*MID(L214,1,2)*MID(E213,1,3))/B216` (0.8·0.85·0.85·0.17·75·150 / v) | Nomura | `power.nomura_pull(nhp, k1, k2, k3, speed)` | — |
| Hamuro | A248:L280 | `F259 =PRODUCT(F256,F257,F258,MID(F254,1,3))` (K1·K2·K3·NHP por configuración de hélice); `G260 =AVERAGE(F259:I259)`; `E272 =MID($C$263,1,2)*$F$259/B272` (75·Ps / v) | Hamuro (Tokyo Univ. Fisheries) | `power.hamuro_pull(nhp, k1, k2, k3, speed)` | — |
| Resumen peor caso 150 HP | A295:I308 | `D300…H308` números pegados (**estáticos**: Fridman, Prado, Koyama, Hamuro); `G300 =E216` (Nomura, fórmula); `I300 =AVERAGE(D300:H300)` | — | `power.summary_table` | — (golden con `"static": true`) |
| Resumen mejor caso 150 HP | A314:I327 | estáticos + `G319 =F272` (**columna "Nomura" enlaza Hamuro PV+T 150**) | — | `power.summary_table` | — (enlace incorrecto; documentar) |
| Resumen peor caso 180 HP | A337:I350 | estáticos + `G342 =G272` (enlaza Hamuro PF 180) | — | `power.summary_table` | — |
| Resumen mejor caso 180 HP | A357:I370 | estáticos + `G362 =H272` (enlaza Hamuro PV+T 180) | — | `power.summary_table` | — |

## 5. Paños de red y cortes → `trawlkit.netting`

La hoja tiene un bloque por paño: plan alto en columnas A–L (A punta de ala, C ala, E square, G
dorso D1, H dorso D2, I bolsa, I' bolsa modificada) y plan inferior en columnas M–X (B, D, F, G
vientre V1, H vientre V2, J bolsa, I' bolsa modificada). Todos los bloques comparten las mismas
fórmulas, que se muestran con el paño A/B (filas 52-64).

| Bloque | Celdas | Fórmula representativa | Método | Destino | Errata |
|---|---|---|---|---|---|
| Composturas (materiales) | C3:C7, C13:C17, C24:C28, O3:O7, O19:O23 | entradas: T mallas 500, N mallas 100, Ø hilo 1.37/1.16 mm, mallero 80/60/40/30 mm, Rtex 1280/950 | — | `netting.Twine`, `netting.Netting` (spec YAML `netting`) | — |
| Letras de paño | filas 37, 67, 100, 133, 166, 199, 232 | `A`, `B`, `C`… (contadas con `COUNTIF`) | — | `netting.PanelSpec.count` | — |
| Rendimiento | A55 | `=1000000/K55` [m/kg] | — | `netting.runnage(rtex)` | — |
| Largos estirados | I55:I57 (`I55 =(H55*D55*$B$55)/1000`) | `n_mallas · coef · mallero / 1000` (coef X = 0.5, Y = 1) | — | `netting.stretched_length(meshes, mesh_mm, coef)` | — |
| Densidad del hilo | L55 | `=((3.1416*((J55/2)^2)*(B55/2)/1000))*(A55/((B55/2)/1000))` | — | `materials.twine_density` | `twine_density_units` |
| Superficie de trabajo del paño | A61 | `=D55*(SQRT(1-(D55^2)))*(((H55+H56)/2)*H57)*(B55/1000)^2` (U1·U2·((T1+T2)/2)·N·mL²) | FAO (Prado) | `netting.panel_working_area` | — |
| Nº de mallas | A64 | `=((H55+H56-1)*(H57-0.5))+0.5` | — | `netting.mesh_count` | — |
| Cortes (faltante, RC, código) | F62:I64 | `G63 =((H56-(H55+H57))/H57)*H57`; `H63 =(ABS(G63-H57))/(2*G63)`; `I63 =VLOOKUP(H63,Tab!$A$49:$C$88,3,FALSE)` | FAO (tabla de cortes) | `netting.cut_ratio`, `netting.cut_code` (usa `src/trawlkit/data/reference/cuts.csv`) | — |
| Corte paño F (X1) | T122 | `{=MATCH(MIN(ABS(Tab!A49:B88-U122)),…)}` → `#N/A` (omitida en golden) | — | `netting.cut_code` | — (celda rota) |
| Cantidad de paneles | N62 (`=SUM(COUNTIF(37:37,"A"),COUNTIF(37:37,"B"))`), B97, N97, B127, N122, N163, N196, B229, N229, O262 | `COUNTIF` de letras | — | `netting.PanelSpec.count` | — |
| Superficie sólida total | V61, J96, V96… | `=Mec!N29` (eco de Mecánica) | — | — | — |
| Pegadura bolsa modificada | J240, B243 | `J240 =I256/I190`; `B243 =(I189-I255)/2` | — | `netting.join_ratio` | — |
| Ángulo de ataque de los cortes | B272:K278 | `E273 =Mec!K56` (U1), `F273 =Mec!L56` (U2), `G273 =I63`; `H273 =VLOOKUP($G$273,Tab!$C$49:$F$88,3,FALSE)`; `J273 =(H273*E273)/(I273*F273)`; `K273 =DEGREES(ATAN(J273))`; `K278 =AVERAGE(K273:K277)` | Prado | `netting.cut_angle(cut_code, u1, u2)`, `netting.mean_cut_angle` | `cut_ratio_first_panel` (H274:I277 usan `$G$273`) |
| Resumen de paños (plan alto) | N269:W279 | `Q271 =B55`, `R271 =H57`, `S271 =H56`, `U271 =K55`, `V271 =J55`, `W271 0.38` (U1) | — | `netting.NetPlan.summary` | — |
| Resumen de paños (plan inferior) | N280:W291 | `Q282 80`, `R282 =T56`, `S282 =T55`, `U282 =W54`, `W282 0.38` / `0.23` | — | `netting.NetPlan.summary` | — |

Nota: en el bloque A (filas 55-57) las etiquetas `b (T2)` y `a (T1)` están invertidas respecto a
los demás bloques; los golden conservan el orden de la hoja (`panel_a_stretched_t2_m` = I55).

## 6. Cables Y Cabulleria → `src/trawlkit/data/ropes.yaml`, `trawlkit.rigging.warps`

| Bloque | Celdas | Fórmula representativa | Método | Destino | Errata |
|---|---|---|---|---|---|
| Cabo de lima | A3:J3 | `A3 {=Dim!B45:E45}`; `D3 "COMBINADO 12 Acero6x24+7"` (= nombre `resulmat`); `G3 =LOOKUP(resulmat,cabl,Tab!E293:E296)` [kg/m]; `H3` [t]; `I3 =LOOKUP(resulmat,cabl,diamcab)`; `J3 =Lima` | catálogo Moscuzza | `src/trawlkit/data/ropes.yaml` + `rigging.ropes.select_rope(name)` | — |
| Cabo de burlón | A4:J4 | `D4 "COMBINADO 14 Acero6x24+7"`; `G4 =LOOKUP(D4,cabl,…)`; `J4 =Burlon` | catálogo | `rigging.ropes.select_rope` | — |
| Refuerzo punta de ala | A5, J5 | `=ROUNDUP(4*Dim!C155,1)` | — | `rigging.ropes.wingtip_reinforcement` | — |
| Cable de remolque seleccionado | D11:I11 | `D11 =LOOKUP(Rem!E264,diamremolque,Tab!C338:C343)`; `G11 =LOOKUP(…,diamremolque,diamremolque)`; `H11 … pesoremolque`; `I11 … resisremolque` | catálogo acero 6x19+1 Seale | `rigging.warps.select_warp(min_diameter_mm)` | `warp_undersized` (ver §12) |
| Cantidad de cable | D12 | `=Rem!F255*2+(Rem!F255*0.5)` (2·Ls + 50 %) | — | `rigging.warps.warp_quantity` | — |

## 7. Mecánica de la Red → `trawlkit.net`, `trawlkit.rigging.spread`

| Bloque | Celdas | Fórmula representativa | Método | Destino | Errata |
|---|---|---|---|---|---|
| Índice de filtración por paño | D6:K14 | `K6 =(I6/J6)*H6` (Ø hilo / mallero · nº paneles); `H15 =SUM(H6:H14)`; `K15 =I15/J15` (**Σd / Σl**, no promedio de K6:K14) | FAO | `net.filtration_index(panels)` | — |
| Índice de filtración modificado | D16:K17 | `H17 =SUM(H16,H6:H12)`; `J17 =SUM(J16,J6:J12,J16)`; `K17 =(I17/J17)` | FAO | `net.filtration_index` | `filtration_double_count` |
| Superficie sólida por paño | C29:N37 | `H29 {=P!J55:J57}`, `M29 =(I29*L29)/1000`, `N29 =((M29*H29*(J29+K29))/1000)*F29` (L·d·(T1+T2)/1000 · n) | FAO | `net.solid_surface(panel)` | — |
| Ss total | N38, N40 | `N38 =SUM(N29:N37)`; `N40 =SUM(N29:N35,N39)` | — | `net.solid_surface_total` | — |
| Ss por plan | O30, O32, O35, O37 | `O30 =SUM($N$29/2,$N$34,$N$35,$N$32/2,$N$33/2,N39/2)` (inferior, con bolsa mod. N39); `O32` (superior, N39); `O35 … N37` y `O37 … N36` (bolsa estándar). Las etiquetas O29/O31/O33 no distinguen Std/Mod: el golden asigna por la bolsa que entra en la fórmula | — | `net.solid_surface_by_plan` | — |
| Superficie de trabajo por paño | A54:M64 | `K56 =P!W271` (U1), `L56 =SQRT(1-(K56^2))`, `M56 =(0.5*K56*L56*((G56)^2)*(H56+I56)*J56)*D56` | FAO | `net.working_surface(panel, u1)` | — |
| St total | M65, M67 | `M65 =SUM(M56:M64)`; `M67 =SUM(M56:M62,M66)` | — | `net.working_surface_total` | — |
| Solidez y filtrado | E75:M79 | `E75 =N38/M65`; `M78 =N$75-E75` | L. G. Pérez Águila (2010) | `net.solidity`, `net.filtering_coefficient` | — |
| Peso de la red (A y B) | A95:P109 | `N98 =(((L98*(H98/1000))*(2*M98))*3.1416*(((G98/2)/1000)^2))*F98` (SN); `O98 =(((I98+J98)/2)/L98)*(K98/M98)*N98`; `P98 =O98*(1-(1025/F98))`; `O107 =SUM(O98:O106)`; `O109 =SUM(O98:O104,O108)` | Métodos A y B (FAO) | `net.panel_weight`, `net.net_weight` | — (densidad de agua 1025 incrustada; `F98 {=P!L55:L57}`) |
| Peso por plan | F110:I113 | `I110 =SUM(O98/2,O101/2,O102/2,O103,O104,O106)` | — | `net.weight_by_plan` | — |
| Constantes físicas | L127:P129 | ρmar 1024, ρdulce 1000, g 9.81 | — | `trawlkit.units` / `src/trawlkit/data/reference/constants.yaml` | — |
| Fuerzas del portón y DPA Fridman | B162:Q172 | `H164 =0.5*($O$127/$O$129)*($C164^2)*E164*F164` (Rd), `I164 … *G164` (Fdy), `J164 =Res!N302*1000`, `L164 =H164/(0.5*J164)` (Edx), `N164 =I164/(0.5*J164)` (Edy), `P164 =2*($F$179*$E$185*$O164)/($F$179+$E$186*(1+$L164))` | Fridman (fuerza de expansión Ry y resistencia Tx) | `rigging.spread.door_forces`, `rigging.spread.dpa_fridman` | — (P164 usa `$O164` = Edy **modificada** en la columna estándar) |
| Datos de maniobra | B175:F186 | `E176 =D193` (profundidad), `J178 =LOOKUP(E176,Tab!A354:A383,Tab!C354:C383)`, `E177 =E176*J178` (Ls), `F179 =0.95*E177` (Lsh), `E182 =Res!D86` (LR), `E185 =E182*E184` (LR·U2), `E186 =Dim!F68` | Fridman | `rigging.warps.warp_length_for_depth`, `rigging.spread.towing_geometry` | — |
| Tabla DPA Fridman (2·Yn) | B191:M201 | `I193 =P164/2`, `K193 =2*I193`, `M193 =(L193*($E$211+$E$212+$E$213+$E$214+$E$209))/$E$209` | Fridman | `rigging.spread.dpa_fridman_table` | — |
| DPA geométrica | B209:M214 | `L211 =ROUNDDOWN((E209*E210)/(E211+E212+E213+E214+E209),0)` (Burlón·Ds / Σ aparejo) | triángulos semejantes | `rigging.spread.dpa_geometric` | — |
| DPA con LR trabajando | B221:M229 | `L225 =ROUNDUP((E221*E225)/(E225+E226+E227+E228+E229),0)` | ídem | `rigging.spread.dpa_geometric` | — |
| DPA por ángulo de corte | A233:M235 | `L233 =2*E233*E234*TAN(RADIANS(E235))` (2·b·U2·tan α) | Prado | `rigging.spread.dpa_from_cut_angle` | — |
| AV por porcentaje | B245:H247, J242:L245 | `F245 =F243*0.055` (Prado: 5.5 / 6.5 / 6.5 %); `K242 =F243*0.0435` (Izzo: 4.35 / 5 / 6 / 7 %) | Prado & Dremiere; A. Izzo (INIDEP) | `net.vertical_opening_pct(circumference, pct)` | — |
| AV Suzuki | A251:F255 | `D255 =(4/90)*F253` | N. Suzuki (JICA 1982) | `net.vertical_opening_suzuki` | — |
| AV Martini | A260:E272 | `E269 {=((P!H156+P!T156)*P!N156:N158)/1000}` (DV); `E270 =3*4` (MR); `E272 {=(E269-((E270*P!B156:B158)/1000))*0.05}` | Martini nivel 2 | `net.vertical_opening_martini` | — |
| AV Baranov–Fridman | J250:P282 | `O261 =AVERAGE(Flot!N43,Flot!N55,Flot!F17,Flot!G17)` (Ffz); `O267 =O266*O260` (fL = 0.216·L); `M272 =DEGREES(ATAN((2*$O$261)/K272))`; `O272 =$O$262+($O$267+$O$263)*(SIN(RADIANS(M272)))`; `O282 =AVERAGE(O272:O280)` | Baranov y Fridman | `net.vertical_opening_fridman(flotation, rn, sag, bridle, dan_leno)` | — |
| Resumen AV | S244:Y252, S253:U266 | valores **estáticos** (Prado 2.46/2.9, Izzo 1.94…3.12, Suzuki 1.98, Martini 2.196, Fridman T256:U264 y T266:U266) | — | — (golden con `"static": true`) | — |

## 8. Dimensiones de la Red → `trawlkit.dimensions`

| Bloque | Celdas | Fórmula representativa | Método | Destino | Errata |
|---|---|---|---|---|---|
| Lima | F45 | `=(C143*2)+G143` (2·L ala corregido + L bocana corregido) | Martini nivel 2 | `dimensions.headrope_length` | — |
| Burlón | F46 | `=(2*MID(C151,1,4)+MID(G151,1,3))` (**MID sobre números**: 15.624 → "15.6", 2.1414 → "2.1" ⇒ 33.3; exacto 33.389) | Martini | `dimensions.footrope_length` | — (candidato a errata) |
| Largo total (vientre) con bolsa | F47, G47 | `=SUM((P!Q282*P!R282),(P!Q283*P!R283),(P!Q286*P!R286),(P!Q288*P!R288),(P!Q289*P!R289),(P!Q290*P!R290))/1000`; G47 termina en `Q291*R291` (bolsa mod.) | — | `dimensions.total_length` | — |
| Largo total (dorso) sin bolsa | F48, G48 | `F48 =((P!Q271*P!R271)+(P!Q272*P!R272)+(P!Q275*P!R275)+(P!Q276*P!R276)+(P!Q277*P!R277))/1000`; `G48 =SUM(Q282·R282, Q283·R283, Q286·R286, Q288·R288, Q289·R289)/1000` | — | `dimensions.body_length_no_bag` | `mod_length_wrong_rows` (G48 suma filas del plan inferior, no del dorso; coincide numéricamente con F48 = 32.68) |
| Circunferencia máxima | F49 | `=((P!S276*P!Q276)+(P!S288*P!Q288))/1000` | — | `dimensions.max_circumference` | — |
| Ala superior / inferior, dorso, bolsa, square | F50:F54 | `F50 =((Q271*R271)+(Q272*R272))/1000`; `F51 =(Q282·R282 + Q283·R283 + Q286·R286)/1000`; `F52 =(Q276*R276)/1000`; `F53 =(Q278*R278)/1000`; `F54 =F51-F50` | — | `dimensions.piece_lengths` | — |
| Resumen de dimensiones | F55:G71 | ecos: `F55 =P!K278` (α), `F56 =Mec!K15`, `F57 =Mec!N38`, `F58 =Mec!M65`, `F59 =Mec!O107`, `F60 =Mec!D255` (AV), `F61 =AVERAGE(Mec!L233,Mec!L225,Mec!L211,AVERAGE(Mec!K193:K201))` (AH), `F62 =Especie!E5`, `F63 =Flot!F90`, `F64 0.6`, `F65 25`, `F66 =Port!$E$97`, `F67 =Port!E99`, `F68 =Port!D44`, `F69 =Port!D45`, `F70 =Cab!G11`, `F71 =Rem!F255` | — | `dimensions.NetDimensions` (dataclass de salida) | — |
| Factor largo | C82:E89 | `D89 =(F83+(2*((F85*F86)/1000)))/F84` | A. Fujiishi (Shimonoseki) | `dimensions.length_factor` | — |
| Circunferencia de pesca | C97:E97 | `D97 =((P!S276+P!S288)*P!Q288)/1000` | — | `dimensions.fishing_circle` | — |
| Largo del cuerpo | C103:E103 | `D103 =((P!R276*P!Q276)+(P!R277*P!Q277))/1000` | — | `dimensions.body_length` | — |
| Relación FC/cuerpo | B109:E109 | `D109 =D97/D103` | — | `dimensions.fc_body_ratio` | — |
| Proporciones Nomura | B124:E132 | `C124 =Lima/Burlon`, `C125 =Lima/F47` … `C132 =(F51-F50)/F47`; `E124 =Tab!D16` … | Nomura | `dimensions.nomura_ratios` + `src/trawlkit/data/reference/nomura_ratios.csv` | — |
| Relingas (lima) | B140:G143 | `C140 {=((P!H92+P!H57)*P!B55:B57)/1000}`; `F140 {=(((P!H120*P!B120:B122)-((P!H91*P!B90:B92)*2))/1000)*0.5}`; `C143 =C140*C142` (embando 1.05); `G143 =F140*G142` (0.83) | Martini nivel 2 | `dimensions.rope_pieces(hanging_ratio)` | — |
| Relingas (burlón) | B148:G151 | `C148 {=((P!T56+P!T91)*P!N89:N91+P!T116*P!N114:N116)/1000}`; `F148 {=((P!T156*P!N156:N158)-((2*P!T114)*P!N114:N116))/1000*0.5}`; `C151 =C148*C150`; `G151 =F148*G150` | Martini | `dimensions.rope_pieces` | — |
| Refuerzo punta de ala | B155:C157 | `C155 {=(P!H57*P!B55:B57)/1000}`; embando 1 | — | `dimensions.wingtip_reinforcement` | — |

## 9. Resistencia de la RED → `trawlkit.drag`

Todas las series son de 9 filas (1.0–5.0 kn), columna estándar y columna modificada. `v` en m/s
salvo donde se indica `v_kn`. Resultados en toneladas (÷1000).

| Bloque | Celdas | Fórmula representativa | Método | Destino | Errata |
|---|---|---|---|---|---|
| Entradas | E4:E6, I25:I26 | `E4 =Mec!K15`, `E5 =Mec!K17`, `E6 =Dim!D97`, `I25 =Lima`, `I26 =Burlon` | — | `drag.DragInputs` | — |
| Velocidades | B11:C19 | `B11 =PotOK!B10` (kn), `C11 =PotOK!B272` (m/s, 0.5144·kn) | — | `units.knots_to_ms` | — |
| Tauti–Nomura–Shu (1974) | D11:E19 | `D11 =(27*$E$4*($E$6^2)*(C11^1.45))/1000` | Tauti, Nomura y Shu (redes de dos caras) | `drag.tauti_nomura_shu(dl, a, v)` | — |
| Tauti (lima) | D30:E38 | `D30 =(25*$E$4*$I$25^2*C30^2)/1000` | Tauti | `drag.tauti(dl, rope_length, v)` | — |
| Tauti (burlón) | L30:M38 | `L30 =(25*$E$4*$I$26^2*K30^2)/1000` | Tauti | `drag.tauti` | — |
| Koyama (1974) | D74:E82 | `D74 =(16*$E$4*$E$68*$E$69*(C74^2))/1000` (a = circunferencia, b = largo con bolsa) | Koyama 1974 | `drag.koyama_1974(dl, a, b, v)` | — |
| Koyama (1984) | C91:D99 | `C91 =(8*$E$4*$E$6*$D$86*B91^2)/1000` (**v en nudos**, L = largo sin bolsa) | Koyama 1984 | `drag.koyama_1984(dl, a, l, v_kn)` | — |
| Hamuro | D117:E125 | `D113 =ABS(SIN(DEGREES(D112)))`; `D117 =(191*$E$4*(C117^2)*$D$110*$D$113)/1000`; `E117 =(191*$E$4*(C117^2)*$D$111*$D$113)/1000` | Hamuro (Tokyo Fisheries Univ.) | `drag.hamuro(dl, st, alpha, v)` | `hamuro_sin_degrees` (D113), `hamuro_mod_uses_std_dl` (E117 usa `$E$4`) |
| Nomura (1981) | D132:E140 | `D132 =((7.2*150)/C132)/1000`; `E132 =((7.2*180)/C132)/1000` | Nomura | `drag.nomura(nhp, v)` | — |
| Reid (1977) | C154:D162 | `C154 =(($B154^2)*$F$149)/(54.72*$B$154+115.2)` (v en nudos; denominador fijo en `$B$154`) | A. J. Reid (redes pelágicas) | `drag.reid(ss, v_kn)` | `reid_fixed_denominator` |
| Robertson (1981) | C174:D182 | `C174 =(($B174^2)*$F$169)/((66.18*$B174)+41.5)` | J. H. B. Robertson (semipelágicas) | `drag.robertson(ss, v_kn)` | — |
| MacLennan (1981) | C196:D204 | `C196 =($F$191*(61.2+46.6*($B196^2))/(1+(0.0641*$B196)))/9807` | MacLennan (fondo, PE) | `drag.maclennan(ss, v_kn)` | — |
| Aberdeen demersal | C214:D222 | `C214 =$F$209*(((0.00624+0.00475*($B214^2))/(1+0.0641*$B214)))` | Marine Laboratory Aberdeen (demersal, PE) | `drag.aberdeen_demersal(ss, v_kn)` — **es la RN de diseño que usa el resto del libro** | — |
| Aberdeen pelágica | C237:D245 | `C237 =$F$232*((0.00868*($B237^2))/(1+0.00475*$B237))` | Marine Laboratory Aberdeen (pelágica, nylon) | `drag.aberdeen_pelagic(ss, v_kn)` | — |
| Fridman (1973) | D258:E266 | `D258 =((1.8+(2*$F$254)*($F$250-0.01))*$F$252*($C258^2))/1000` (α en grados, St) | Fridman | `drag.fridman(dl, st, alpha_deg, v)` | — |
| Dickson | E282:F290 | `F276 =F273*$F$275` (m²→ft², 10.76); `C282 =Mec!P164` (AH), `D282 =Mec!O272` (AV); `E282 =(1/125)*$F$276*($F$271*(((1+(6.6*2*$C282*$D282))/$F$273)))` | Dickson | `drag.dickson(st, dl, ah, av)` | — |
| Resumen [t] estándar | A298:S310 | `A302 {=B11:C21}`, `C302 =D11`, `D302 =D30`, `E302 =L30`, `F302 =D74`, `G302 =C91`, `H302 =D117`, `I302 =D132`, `J302 =E132`, `K302 =C154`, `L302 =C174`, `M302 =C196`, `N302 =C214`, `O302 =C237`, `P302 =D258`, `Q302 =E282`; `R302 =AVERAGE(B302:P302)`, `R303 =AVERAGE(C303:Q303)`; `S302 =330.6/1000`, `S303 =0.476`, `S304… 0.7043` (**DynamiT, estático**) | — | `drag.summary_table` | `drag_average_pollution` (R302 incluye B302 = velocidad en m/s; R302:R310 incluyen Nomura I/J, que es tiro disponible, no RN) |
| Resumen [t] modificada | A313:S326 | `C317 =E11` … `Q317 =F282`; `R317 =AVERAGE(C317:Q317)`; `C326 =AVERAGE(C317:C325)` (promedio por método) | — | `drag.summary_table` | ídem |
| Resumen [kgf] | A394:S422 | `C398 =C302*1000` … `S421 =S325*1000`; `C422 =C326*1000` | — | `drag.summary_table(unit="kgf")` | — |

## 10. Portones y aparejamiento → `trawlkit.rigging.doors`, `trawlkit.rigging.bridles`

| Bloque | Celdas | Fórmula representativa | Método | Destino | Errata |
|---|---|---|---|---|---|
| Distancia entre portones | B6:F13 | `D6 =Buques!B5`, `D7 2.65` (apertura por metro de cable), `D9 =Mec!E177`; `E13 =((D7-D6)*D9)+D6` | regla práctica (al metro) | `rigging.doors.door_spread(gallows, spread_per_m, warp)` | — |
| Ángulo de divergencia ½φ | B17:E21 | `D21 =DEGREES(ASIN(0.5*((E17-E18)/E19)))` | geometría | `rigging.warps.divergence_angle` | — |
| Distancia corregida | B26:G30 | `F30 =D28*(2*(E19*SIN(RADIANS(D27))))` (factor 1.15) | — | `rigging.doors.door_spread_corrected` | — |
| Bridas a un punto | A33:G60 | `F37 =Mec!D255` (AV), `F38 =Mec!O267` (fL), `F39 4.8°`; `E52 =ROUND((F37/SIN(RADIANS(F39)))-F38,0)`; `E60 =ROUND((F37-F56)/(SIN(RADIANS(F39))),0)` (con triángulo); `D44 =ROUND(E52,0)`, `D46 =D44*0.095` (cadena de reglaje), `D45 =ROUNDUP(D44-D46,0)` | Martini | `rigging.bridles.bridle_lengths(av, sag, angle, dan_leno)` | — |
| Patentes Dremiere | A63:C71 | `C71 =B69/B68` (Ls / 6) | P. Y. Dremiere | `rigging.bridles.sweeps_dremiere(warp, ratio)` | — |
| Patentes Martini (δ) | E63:H71 | `G71 =((E13/2)-(E78/2)/DEGREES(SIN(H65)))` (**DEGREES(SIN(20))**, mezcla de unidades; resultado no usado aguas abajo) | Martini | — (documentar) | — |
| Patentes sin/con triángulo | A75:C87 | `C83 =(((E77*E80)/E78)-(E79+E80))*1.1` (LPST = (Ds·LR/DPA − (Vs + LR))·1.1); `C87 =(((E77*E80)/E78)-(E81+E80))*1.1` | Martini | `rigging.bridles.sweeps_length(ds, lr, dpa, bridle)` | — |
| Pies de gallo | A90:G99 | `D95 =D120` (largo del portón); `E97 =ROUND(D95+(D95*0.2),1)`; `G98 =E97-0.05`; `E99 0` | Martini | `rigging.bridles.crowfoot(door_length)` | — |
| Ángulo de ataque de bridas δ | A101:E110 | `D110 =DEGREES(ASIN(((E103-E104)/2)/(E105+E106+E107)))` | — | `rigging.bridles.attack_angle(ds, dpa, pg, sweeps, bridle)` | — |
| Selección de portón | B116:F137 | `B117` lista (`listadelistas`); `D120 =IF($B$117=Porton_plano…,LOOKUP($B$117,Porton_plano…,Tab!C247),IF($B$117=porton_del_orto,LOOKUP(…,Morgere_Polivalente_Oval,Tab!C269),0))`; `D122` área 1.805 m²; `C132:F137` polar (ángulo, CL, CD, CL/CD); fila 134 = 32° seleccionada | catálogo FAO / Morgère | `rigging.doors.Door` + `src/trawlkit/data/reference/doors.csv` | — |
| ROB como % del tiro | A141:H168 | `D146 =PotOK!L11` (FT PF 150), `E146 =D146*0.15` … `H146 =D146*0.3`; 180 HP: `D160 =PotOK!N11` | Fridman (ROB = 15–30 % de FT) | `rigging.doors.door_drag_share(ft, pct)` | — |
| ROB y fuerza de abertura | B184:E198 | `D190 =0.5*($E$203/$E$205)*$D$185*$D$184*($C190^2)` (½·ρ/g·CD·S·v²); `E190 … $D$186` (CL) | hidrodinámica básica | `rigging.doors.door_forces(area, cd, cl, v)` | — |
| Superficie requerida del portón | B201:F231 | `E210 =(2*$D210)/(($E$203/$E$205)*$E$206*($C210^2))` con `D210 =F146` (ROB 20 %); `F212 =AVERAGE(E212:E216)` (2–4 kn); `F215 =F212/2`; `F220 =AVERAGE(F215,F229)` | — | `rigging.doors.required_area(rob, cd, v)` | — |
| Ángulo bisagra / fuerza Pφ | A235:D260 | `D252 =0.5*$E$241*($E$237/$E$239)*(C252^2)*$E$244*((2*SIN(RADIANS($E$240)))/(1+(SIN($E$240))^2))` | — | `rigging.doors.door_force(cd, area, angle, v)` | `door_force_mixed_angles` |
| Centro de presión | A264:D270 | `C266 =(3/4)*((COS(RADIANS(E240))/(4+PI()*SIN(RADIANS(E240)))))*E243`; `C269 =(0.8*E243)/4`; `C270 =E243/4` | — | `rigging.doors.centre_of_pressure(length, angle)` | — |
| Equilibrio de fuerzas | A273:H289 | `G281 =F281*($C$266*100)` (momento Pφ·d en kgf·cm); `H281 =0.5*D281*$E$277` (½·RN·d_patente, con `E277 3`) | — | `rigging.doors.moment_balance` | — (H281 queda en kgf·m aunque la cabecera dice kgf·cm) |

## 11. Flotación y Lastre → `trawlkit.rigging.floats`, `trawlkit.rigging.ballast`

| Bloque | Celdas | Fórmula representativa | Método | Destino | Errata |
|---|---|---|---|---|---|
| Flotación Koyama | E2:I6 | `F6 =1.11*H4-6.81` (H4 = Lima) | Koyama | `rigging.floats.flotation_koyama(headrope)` | — |
| Flotación Prado | E10:I17 | `F17 =I14*MID(F16,1,3)` (K·NHP, K = 0.2 para 50–600 NHP) | Prado & Dremiere | `rigging.floats.flotation_prado(nhp, k)` | — |
| Geometría | B22:F27 | `F22 =Port!F39` (α bridas), `F23 =DEGREES(ATAN((F24/2)/F25))` (β), `F24 =Dim!F60`, `F25 =Dim!D103` | — | `rigging.floats.geometry` | — |
| Peso de la lima en el agua | C29:F37 | `F35 =Cab!G3`, `F36 =F31*F35`, `F37 =F36*0.087` | — | `rigging.ropes.rope_weight_in_water` (0.087) | — |
| Flotación Fridman 150 HP | B40:N50 | `E42 =PotOK!L11` (FT), `F42 =(0.8*E42)/4` (F1), `G42 =C42/4` (F2 = RN/4), `I42 =F42*SIN(RADIANS($F$22))`, `J42 =G42*SIN(RADIANS($F$23))`, `L42 =ROUNDDOWN(I42+J42+$F$37,0)`, `M43 =I43+K43+$F$37` (sin redondeo salvo M42); `N43 =AVERAGE(L42:M46)` (1–3 kn) | Fridman | `rigging.floats.flotation_fridman(ft, rn, alpha, beta, rope_weight)` | — |
| Flotación Fridman 180 HP | B53:N63 | ídem con `E55 =PotOK!N11`; `N55 =AVERAGE(L55:M59)` | Fridman | `rigging.floats.flotation_fridman` | — |
| Número de boyas | D69:G82 | `F70 =N43`, `F72 =ROUND($F$70/E72,0)` por diámetro del catálogo D72:E82 | catálogo | `rigging.floats.float_count(flotation, unit_buoyancy)` + `src/trawlkit/data/reference/floats.csv` | — |
| Distribución de boyas | C84:L112 | `F84 12` (elegido), `F92 =LOOKUP(F91,cincuenta,D72:D82)` (200 mm), `F94 =F86/F91`, `F95 =INT(F87/F94)`, `F96 =F91-2*F95`; selectiva: `G103 =EVEN(F91*F103)` (70 % en alas), `G107 =H103*G106`, `H110 =ROUND((F89)/(G107-1),2)`, `H111 =(INT(C111/F111))`, `K112 =F89/3` | — | `rigging.floats.distribute_floats` | — (texto A110:L112 generado con `&`) |
| Resistencia de las boyas | A116:J146 | `H128 =H127/1000`, `H129 0.47` (CD Hoerner), `H132 =AVERAGE(H130:H131)` (ν); `H138 =(PI()*($H$128^2)*$E138)/$H$132` (Re); `I138 =$H$129` (1–2.5 kn) / `0.5` (3–5 kn); `J138 =0.5*$H$123*$I138*($H$124/$H$126)*((PI()*$H$128^2)/4)*$E138^2` (n·½·CD·ρ/g·A·v²) | Hoerner (1975) | `rigging.floats.float_drag(n, d, cd, v)` | `float_reynolds` |
| Lastre Koyama | D153:H159 | `G159 =(1.81*G155)-4.54` | Koyama | `rigging.ballast.ballast_koyama(headrope)` | — |
| Lastre Prado | F162:I180 | `I173 =G168*G171` (K = 0.28 · 150), `I180 =G176*G178` (0.28 · 180) | Prado & Dremiere | `rigging.ballast.ballast_prado(nhp, k)` | — |
| Peso del burlón en el agua | E182:H191 | `G187 =Cab!G4`, `G188 =G184*G187`, `G191 =G188*G190/10` (0.87/10 = 0.087, coherente con la lima) | — | `rigging.ropes.rope_weight_in_water` | — |
| Lastre total Fridman | A193:M218 | `L197 =(I197+J197)-$G$191` (F1' + F2' − W burlón), `M197 … +K197` (mod); 180 HP en L210:M218 | Fridman | `rigging.ballast.ballast_fridman(f1v, f2v, rope_weight)` | — |
| Distribución del lastre | B221:I245 | `F225 =ROUNDDOWN(M197,0)` (mínimo = mod 1 kn), `F226 =ROUNDUP(L201,0)` (máximo = std 3 kn), `H224 =ROUNDUP(F225*F236,0)*F224`, `E233 =(F225-H224)/F223`; selectiva: `G236 =ROUNDDOWN(F236*F225,0)` (20 % reglaje), `G237 =ROUNDUP(F237*F225,0)` (25 % bocana), `G238 =ROUNDUP(F238*F225,0)` (alas), `I238 =G238/H238`; máximo: 30/20/50 % en G243:I245 | — | `rigging.ballast.distribute_ballast` | — |

## 12. Cables de Remolque → `trawlkit.rigging.warps`

| Bloque | Celdas | Fórmula representativa | Método | Destino | Errata |
|---|---|---|---|---|---|
| Datos | A6:F11 | `F6 =Burlon`, `F7 =Port!E13` (Ds), `F8 =SUM(Dim!F65,Dim!F68)` (patentes + brida), `F9 =Port!D9` (Ls), `F10 =Largototal`, `F11 =Port!D6` | — | `rigging.warps.TowingGeometry` | — |
| DPA (A, B) | D15:F19 | `F17 =(F7*F6)/(F8+F6)`; `F19 =(F7*F10)/(F10+F8)` | triángulos semejantes | `rigging.spread.dpa_geometric` | — |
| Ángulos δ1, δ2, δ3 | C23:F33 | `E25 =DEGREES(ASIN((0.5*((F7-F11)/F9))))` (δ2 divergencia del cable); `E29 =DEGREES(ASIN((0.5*((F7-F17)/F8))))` (δ3 bridas); `E33 =DEGREES(ASIN((Especie!E5+Buques!B6)/F9))` (δ1 declinación) | — | `rigging.warps.warp_angles` | — |
| Diámetro del cable (EHP) | B65:G74 | `E70 =PotOK!C171`; `F73 =18+(0.0034*E70)` (fórmula para >500 HP) | regla práctica | `rigging.warps.warp_diameter_ehp(ehp)` | — |
| Diámetro del cable (Águila) | B76:F81 | `E80 =5.6822*LN(MID(E77,1,3))-17.225` | L. G. Pérez Águila | `rigging.warps.warp_diameter_aguila(nhp)` | — |
| CD del cable (α) | A89:B94, B103:E106 | tabla α→CD (0.02…0.30); `E106 {=INDEX(B90:B94,MATCH(MIN(ABS(alfaremolque-anguloremolque)),alfaremolque-anguloremolque,1))}` (α más cercano) | Nomura y Yamazaki | `rigging.warps.warp_cd(angle)` + `src/trawlkit/data/reference/warp_cd.csv` | — |
| Resistencia del cable (Rw) y total | B115:I126 | `G118 =(0.5*$E$106*($E$107/$E$109)*$E$111*$E$112*(C118^2))*2` (½·CD·ρ/g·D·L·v²·2 cables); `H118 =G118+F118+D118` (Rw + RB + RN std); `I118 … +E118` (mod) | Nomura y Yamazaki | `rigging.warps.warp_drag`, `rigging.warps.total_drag` | `warp_total_omits_doors` (H118 no suma ROB) |
| Rw cilindro (Re, CD) | B153:G175 | `D167 =($E$154*$C167)/$F$161` (Re = D·v/ν); `E167 1.1` (1–2.5 kn) / `1.2` (3–5 kn); `F167 =0.5*E167*($E$156/$E$158)*$E$154*$E$155*(C167^2)`; `G167 =2*F167` | cilindro en flujo cruzado | `rigging.warps.warp_drag_cylinder` | — |
| Rw como % del tiro | A178:H199 | tabla de autores (Craig 4 %, Podeur 5–8 %, Hansen 5 %, Gudnasson 5–10 %, Nomura 4–10 %); `E191 =C191*0.05` (5 % FT PF), `G191 =C191*0.1` | Craig, Podeur, Hansen, Gudnasson, Nomura | `rigging.warps.warp_drag_share(ft, pct)` | — |
| Kowalski y Gianotti | C202:G217 | `D204 =E167`, `D205 0.02`; tabla de ecos sin cálculo propio | Kowalski y Gianotti | — | — |
| MacLennan CD | B221:F235 | `D227 =2.11-12.24*C227*$E$154` (CD = 2.11 − 12.24·v·Dw, Dw en m ⇒ 2.03…1.72) | MacLennan | `rigging.warps.warp_cd_maclennan` | — |
| Peso del cable | B241:G257 | `E248 =AVERAGE((0.00368*(F246^2)),(0.00417*(F246^2)))` [kg/m aire]; `F250 =0.00305*(F246^2)`; `F252 =0.87*E248`; `F256 =F255*E248`; `F257 =F255*F252` | catálogo | `rigging.warps.warp_weight(diameter_mm)` | — |
| Selección del cable | A261:F272 | `E264 =F246` (Ø mínimo 12.28 mm), `E267 =H123` (resistencia total a 3.5 kn, 2200 kgf), `D271 4`, `E272 =E267*D271` (8 802 kgf) | — | `rigging.warps.select_warp(min_breaking_load)` | `warp_undersized` (Cab!D11 selecciona 12 mm / 8.55 t por `LOOKUP` del Ø, no por la carga 8.8 t) |

## 13. Tablas de Referencias → `src/trawlkit/data/reference/*.csv`, `trawlkit.materials`

| Bloque | Celdas | Contenido | Fuente citada | Destino | Errata |
|---|---|---|---|---|---|
| Coeficientes KF | A5:B7 | KF(PF) = 10, KF(PV+T) = 15 | Fridman | `src/trawlkit/data/reference/fridman_kf.csv` | — |
| Proporciones Nomura | A15:L25 | 10 tipos de red × 9 relaciones (l/m, l/b, m/b, a/b, c/b, d/b, e/b, f/b, (d−c)/b) | Nomura | `src/trawlkit/data/reference/nomura_ratios.csv` | — (G18 y G21 = 10.6, probable 1.06) |
| Materiales | A33:I37 | PA: densidad 1140 kg/m³, rendimiento 780 / 1050 m/kg, Rtex 1280 / 950, Ø 1.37 / 1.16 mm, coef. agua salada 0.1, dulce 0.12 | — | `src/trawlkit/data/reference/materials.csv`, `materials.Material` | — |
| Cortes de paños | A45:F88 | relación (`A51 =1/3`), código (`1N2B`, `AB`, `1T2B`…), relación no exacta, mallas (a) ancho, (d) alto | FAO | `src/trawlkit/data/reference/cuts.csv`, `netting.cut_code` | — |
| Factor K nudos simples | A94:F113 | mallero × Ø hilo → factor de corrección | — | `src/trawlkit/data/reference/knot_factor.csv` | — |
| Catenaria | A116:I171 | DPA/L (`A119 =B119/C119`), fL/L, fL/DPA, tg β, β, α, fL | — | `src/trawlkit/data/reference/catenary.csv`, `rigging.spread.catenary` | — |
| Ángulos útiles | A175:H216 | δ patentes 10–30°, relación Dremiere 3–8, longitudes permitidas 20–70 m, porcentajes útiles, NHP posibles | Dremiere / Martini | `src/trawlkit/data/reference/sweeps.csv` | — |
| Profundidades / brazos dan leno | A201:B221 | profundidad 10–200 m → altura 0.1–… m | — | `src/trawlkit/data/reference/dan_leno.csv` | — |
| Portón FAO plano de madera | A245:E264 | largo 1.9, alto 0.95, `C249 =C247*C248` (1.805 m²), `C250 =C248/C247`, peso aire 135 kg, `C254 =C252*C253` (80.6 kg); polar 25–45° (CL, CD, `E259 =C259/D259`) | FAO (A3/B3/C3) | `src/trawlkit/data/reference/doors.csv` | — |
| Portón Morgère Polivalente Oval | A267:E286 | `C270 =C272*C269`, `C271 =(C269/2)*(C270/2)*PI()`, polar 281:286 | Morgère | `src/trawlkit/data/reference/doors.csv` | — |
| Cabos y cables | A290:F296 | Moscuzza: PP 14 / combinado 12 / combinado 14 / PP 16; Ø, kg/m (`E293 =27.5/220`), resistencia [t] | catálogos, Fisherman's Workbook | `src/trawlkit/data/ropes.yaml` | — |
| Cadenas | A312:C317 | Trawlex corto 7 mm (1.05 kg/m), largo 19 mm (6.31 kg/m) | catálogo | `src/trawlkit/data/reference/chains.csv` | — |
| Cables de acero para remolque | B337:G343 | 6x19+1 AT Seale compactado: Ø 9.5–18 mm, kg/m, resistencia 5.5–18.46 t, `G338 =C338&B338` | catálogo | `src/trawlkit/data/reference/warps.csv` | — |
| Profundidad / cable filado | A353:C383 | profundidad 20–… m → cable filado (`C354 =B354/A354`, factor 6 → 3.4) | — | `src/trawlkit/data/reference/warp_by_depth.csv`, `rigging.warps.warp_length_for_depth` | — |

---

## Nombres definidos (workbook.defined_names)

| Nombre | Destino | Estado |
|---|---|---|
| `alfaremolque` | `'Cables de Remolque'!$A$90:$A$94` | ok (tabla α de CD del cable) |
| `angulopatentes` | `'Tablas de Referencias'!$A$176:$A$197` | ok — **duplicado** de `δ_Patentes` |
| `anguloremolque` | `'Cables de Remolque'!$E$103` | ok |
| `Burlon` | `'Dimensiones de la Red'!$F$46` | ok (muy usado) |
| `cabl` | `'Tablas de Referencias'!$B$293:$B$296` | ok — **duplicado** de `matcab` |
| `cables` | `'Tablas de Referencias'!$B$293:$D$296` | ok |
| `cincuenta` | `'Flotación y Lastre'!$F$72:$F$82` | ok (boyas 150 HP; nombre engañoso) |
| `cincuentayocho` | `'Flotación y Lastre'!$G$72:$G$82` | ok (boyas 180 HP) |
| `consremolque` | `'Tablas de Referencias'!$C$338:$D$343` | ok |
| `construccioncable` | `'Tablas de Referencias'!$D$293:$D$294` | ok (sin uso) |
| `diaca` | `'Tablas de Referencias'!$C$316:$C$322` | ok (cadenas; sin uso) |
| `diamcab` | `'Tablas de Referencias'!$C$293:$C$296` | ok |
| `diametrocable` | `'Tablas de Referencias'!$C$293:$C$294` | ok — **duplicado parcial** de `diamcab` |
| `diamremolque` | `'Tablas de Referencias'!$B$338:$B$343` | ok |
| `Kgf` | `'Flotación y Lastre'!$F$72:$G$82` | ok (nombre engañoso: son conteos de boyas) |
| `klastre` | `'Flotación y Lastre'!$E$168:$E$172` | ok |
| `Largototal` | `'Dimensiones de la Red'!$F$48` | ok (largo sin bolsa; nombre engañoso) |
| `Lima` | `'Dimensiones de la Red'!$F$45` | ok (muy usado) |
| `listadelistas` | `'Portones y aparejamiento'!$B$117:$F$118` | ok (validación de datos del portón) |
| `Longitudespatentes` | `'Tablas de Referencias'!$C$177:$C$187` | ok — **duplicado** de `longp`, `LP`, `Lpatent` |
| `longp` | `'Tablas de Referencias'!$C$177:$C$187` | duplicado |
| `LP` | `'Tablas de Referencias'!$C$177:$C$187` | duplicado |
| `Lpatent` | `'Tablas de Referencias'!$C$177:$C$187` | duplicado |
| `matcab` | `'Tablas de Referencias'!$B$293:$B$296` | duplicado de `cabl` |
| `materialcable` | `'Tablas de Referencias'!$B$293:$B$294` | duplicado parcial |
| `Morgere_Polivalente_Oval` | `'Tablas de Referencias'!$K$250` | ok (segunda opción de portón) |
| `NIM` | `#REF!` | **roto** |
| `Nombre` | `#REF!` | **roto** |
| `NUM` | `#REF!` | **roto** |
| `numero` | `#REF!` | **roto** |
| `pesoremolque` | `'Tablas de Referencias'!$E$338:$E$343` | ok |
| `porcentajesutiles` | `'Tablas de Referencias'!$F$177:$F$196` | ok |
| `porton_del_orto` | `'Tablas de Referencias'!$K$250` | duplicado de `Morgere_Polivalente_Oval` (nombre informal; usado en `Port!D120:F137`) |
| `Porton_plano_de_madera_con_bastidor_de_hierro_FAO_para_A3_B3_C3` | `'Tablas de Referencias'!$B$245` | ok (usado en `Port!B119:F137`) |
| `portones` | `'Tablas de Referencias'!$A$245:$H$264` | ok |
| `Profundidades` | `'Tablas de Referencias'!$A$202:$A$221` | ok |
| `prueba` | `'Tablas de Referencias'!$B$245` | **de prueba** (duplicado del portón FAO) |
| `prueba2` | `'Tablas de Referencias'!$C$267,'Tablas de Referencias'!$B$245` | **de prueba** |
| `prueba3` | `'Tablas de Referencias'!$C$267` | **de prueba** |
| `prueba4` | `'Tablas de Referencias'!$K$249:$K$250` | **de prueba** |
| `Relacion_Dremiere_patentes` | `'Tablas de Referencias'!$B$177:$B$182` | ok — duplicado de `relaciondremiere` |
| `relaciondremiere` | `'Tablas de Referencias'!$B$177:$B$182` | duplicado |
| `resisremolque` | `'Tablas de Referencias'!$F$338:$F$343` | ok |
| `resulmat` | `'Cables Y Cabulleria'!$D$3` | ok (cabo de lima seleccionado) |
| `triangulo` | `'Tablas de Referencias'!$B$202:$B$240` | ok (alturas de brazo dan leno) |
| `δ_Patentes` | `'Tablas de Referencias'!$A$176:$A$197` | ok (nombre con carácter no ASCII) |

Resumen: 4 nombres rotos (`NIM`, `Nombre`, `NUM`, `numero`), 4 de prueba (`prueba`…`prueba4`),
10 duplicados (`angulopatentes`/`δ_Patentes`; `cabl`/`matcab`; `diametrocable`/`materialcable`
vs `diamcab`/`cabl`; `Longitudespatentes`/`longp`/`LP`/`Lpatent`; `Relacion_Dremiere_patentes`/
`relaciondremiere`; `porton_del_orto`/`Morgere_Polivalente_Oval`). En trawlkit ninguno sobrevive:
los rangos pasan a `src/trawlkit/data/reference/*.csv` y los escalares (`Lima`, `Burlon`, `Largototal`,
`resulmat`, `anguloremolque`) a campos de los dataclasses de salida.

## Erratas referenciadas (claves de `compat.ERRATA`)

| Clave | Hoja / celda | Bloque de este mapa |
|---|---|---|
| `cut_ratio_first_panel` | Paños H274:I277 | §5 Ángulo de ataque de los cortes |
| `twine_density_units` | Paños L55 | §5 Densidad del hilo |
| `filtration_double_count` | Mecánica J17 | §7 Índice de filtración modificado |
| `hamuro_sin_degrees` | Resistencia D113 | §9 Hamuro |
| `hamuro_mod_uses_std_dl` | Resistencia E117 | §9 Hamuro |
| `reid_fixed_denominator` | Resistencia C154:C162 | §9 Reid |
| `drag_average_pollution` | Resistencia R302:R310 | §9 Resumen [t] |
| `door_force_mixed_angles` | Portones D252 | §10 Ángulo bisagra / fuerza Pφ |
| `float_reynolds` | Flotación H138 | §11 Resistencia de las boyas |
| `warp_total_omits_doors` | Cables de Remolque H118 | §12 Resistencia del cable y total |
| `warp_undersized` | Cables de Remolque E267:E272 (+ Cabulleria D11) | §12 Selección del cable |
| `mod_length_wrong_rows` | Dimensiones G48 | §8 Largo total (dorso) sin bolsa |

Hallazgos adicionales sin clave de errata todavía (candidatos a `ERRATA`): `Dim!F46` (`MID` sobre
números trunca el burlón a 33.3 en vez de 33.389); `Mec!P164:P172` (DPA estándar usa Edy
modificada); `PotOK!G319/G342/G362` (columna "Nomura" enlaza Hamuro); `Port!G71`
(`DEGREES(SIN(20))`); `Tab!G18/G21` (10.6 en vez de 1.06); `Paños!T122` (`#N/A`).
