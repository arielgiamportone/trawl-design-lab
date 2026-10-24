"""Genera ``src/trawlkit/data/examples/sensor_log.csv``: registro de sensores SINTÉTICO.

Simula la red FAO A-3 (fondo mixto, portones acoplados) con la sustentación del portón al 90 %
de la del catálogo ("realidad" oculta que la calibración debe recuperar), en tres tramos de
velocidad con la captura creciendo, y agrega ruido de medición. Encabezados en español, separador
``;`` y coma decimal, tensiones de babor y estribor en toneladas, como exportan muchos equipos.

    uv run python tools/make_sensor_example.py
"""

from __future__ import annotations

import pathlib

import numpy as np

from trawlkit.model import run
from trawlkit.sim import Scenario, simulate
from trawlkit.sim.validation import standard_case

OUT = pathlib.Path(__file__).resolve().parents[1] / "src/trawlkit/data/examples/sensor_log.csv"
TRUE_DOOR_CL_FACTOR = 0.9
SEGMENTS = ((2.5, 100.0), (3.0, 300.0), (3.5, 500.0))  # (kn, kg de captura)


def main() -> None:
    r = run(standard_case())
    rng = np.random.default_rng(42)
    lines = [
        "# Registro de sensores SINTÉTICO (no es una medición real): red FAO A-3, fondo mixto.",
        "# Generado con tools/make_sensor_example.py: sustentación del portón"
        f" × {TRUE_DOOR_CL_FACTOR} más ruido de medición.",
        "Fecha hora;Velocidad (kn);Separacion portones (m);Altura relinga (m);"
        "Tension babor (t);Tension estribor (t);Captura (kg)",
    ]
    t = 0
    for speed, catch in SEGMENTS:
        sim = simulate(
            r,
            speed,
            resolution=3,
            scenario=Scenario(seabed="mixed", catch_kg=catch, door_cl_factor=TRUE_DOOR_CL_FACTOR),
        )
        for _ in range(120):  # 20 minutos cada 10 s
            hh, mm, ss = 6 + t // 3600, (t // 60) % 60, t % 60
            v = speed + rng.normal(0, 0.05)
            dp = sim.door_spread_m * (1 + rng.normal(0, 0.02))
            hr = sim.headrope_height_m * (1 + rng.normal(0, 0.05))
            tp = sim.warp_tension_kgf / 1000 * (1 + rng.normal(0, 0.04))
            ts = sim.warp_tension_kgf / 1000 * (1 + rng.normal(0, 0.04))
            row = [
                f"2026-05-12 {hh:02d}:{mm:02d}:{ss:02d}",
                f"{v:.2f}",
                f"{dp:.1f}",
                f"{hr:.2f}",
                f"{tp:.3f}",
                f"{ts:.3f}",
                f"{catch:.0f}",
            ]
            lines.append(";".join(c.replace(".", ",") if i else c for i, c in enumerate(row)))
            t += 10
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"escrito {OUT}")


if __name__ == "__main__":
    main()
