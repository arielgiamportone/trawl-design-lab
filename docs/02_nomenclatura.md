# Nomenclatura y unidades

Símbolos usados en todo el libro. Entre corchetes, la unidad con la que trabaja el modelo original y
`trawlkit`; las conversiones están en `trawlkit.units`.

## Velocidad, fuerza y potencia

| Símbolo | Significado | Unidad |
|---|---|---|
| $v$ | Velocidad de arrastre | kn (1 kn = 0,5144 m/s) |
| $P$, BHP | Potencia al freno en la hélice | HP |
| NHP | Potencia nominal ("150 HP" en el libro original se toma como BHP) | HP |
| $F_T$ | Tiro (fuerza de arrastre) disponible | kgf |
| $R_N$ | Resistencia de la red | kgf o t |
| $R_B$ | Resistencia de las boyas | kgf |
| $R_W$ | Resistencia de los cables de remolque | kgf |
| $R_{OB}$ | Resistencia de los portones | kgf |
| $R_T$ | Resistencia total del sistema: $R_N + R_B + R_W\,(+R_{OB})$ | kgf |
| $\rho$, $g$ | Densidad del agua de mar (1024 kg/m³) y gravedad (9,81 m/s²) | — |

## Paño y red

| Símbolo | Significado | Unidad |
|---|---|---|
| $m_L$ | Mallero: tamaño de malla estirada | mm |
| $d$ | Diámetro del hilo | mm |
| Rtex, runnage | Título del hilo y su inversa (m/kg = 10⁶/Rtex) | g/km, m/kg |
| $T_1$, $T_2$ | Mallas en el borde mayor y menor del paño (convención del Excel) | mallas |
| $N$ | Mallas de alto del paño | mallas |
| $U_1$, $U_2$ | Coeficientes de armado horizontal y vertical, $U_2 = \sqrt{1-U_1^2}$ | — |
| $d/l$ | Índice de filtración: $\sum d / \sum m_L$ | — |
| $S_s$ | Superficie sólida del hilo | m² |
| $S_t$ | Superficie de trabajo (paño armado) | m² |
| $a$ | Circunferencia de la boca a malla estirada | m |
| $L$, $b$ | Largo de la red sin y con bolsa | m |
| $\alpha$ | Ángulo de ataque de los cortes | ° |

## Aparejo y geometría

| Símbolo | Significado | Unidad |
|---|---|---|
| Lima, burlón | Relinga superior e inferior | m |
| $L_s$, $L_{sh}$ | Cable filado y su proyección horizontal | m |
| $D_s$ | Distancia entre portones | m |
| DPA | Distancia entre puntas de ala (abertura horizontal de la red) | m |
| AH, AV | Abertura horizontal y vertical | m |
| $C_L$, $C_D$ | Coeficientes de sustentación y arrastre del portón | — |
| $E_{dx}$, $E_{dy}$ | Coeficientes de expansión de Fridman | — |
| $\delta$ | Ángulo de ataque de bridas y patentes | ° |
| $f_L$ | Flecha de la lima (catenaria) | m |

## Modos de cálculo

| Modo | Significado |
|---|---|
| `excel` | Reproduce los números del libro Excel original, erratas incluidas. Se usa para validar. |
| `corrected` | Aplica las fórmulas correctas; es el modo por defecto para diseñar. Ver {doc}`erratas`. |
