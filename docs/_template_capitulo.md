---
jupytext:
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

# Título del capítulo

Plantilla de referencia (no está en el índice). Cada capítulo de teoría sigue este orden:

1. **Propósito** del cálculo y dónde encaja en la cadena (ver {doc}`motor`).
2. **Teoría** con ecuaciones numeradas:

$$
F_T = P\,(K_F - 0{,}7\,v)
$$ (eq-fridman-ft)

   y referencia en el texto con {eq}`eq-fridman-ft`. Cita: {cite:p}`fridman1986`.
3. **Coeficientes** en tabla (valor, unidad, fuente, celda del Excel).
4. **Equivalencia** celda Excel ↔ función `trawlkit` (tabla).
5. **Supuestos y límites** (incluye erratas relevantes, ver {doc}`erratas`).
6. **Ejemplo ejecutable**: celda de código que calcula con `trawlkit`, verifica un valor del
   Excel (`tests/golden`) con `assert` y dibuja un gráfico.

```{code-cell} ipython3
:tags: [hide-input]
from trawlkit import power
power.fridman_towing_force_kgf(150, 3.0, 10.0)
```
