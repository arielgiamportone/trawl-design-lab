"""trawlkit: motor de cálculo para el diseño de redes de arrastre.

Reimplementación en Python del modelo FAO A-3 desarrollado originalmente en Excel
(Giamportone, 2014-2024), generalizado a cualquier red parametrizable.

Uso básico::

    from trawlkit import DesignCase, run
    from trawlkit.io import load_doors, load_net, load_vessels

    case = DesignCase(load_net("fao_a3_standard"), load_vessels().vessels[0], load_doors().doors[0])
    result = run(case)
    result.summary()
"""

from trawlkit import (
    dimensions,
    drag,
    io,
    materials,
    model,
    net,
    netting,
    performance,
    power,
    rigging,
    units,
    vessel,
)
from trawlkit.compat import Compat
from trawlkit.model import DesignCase, DesignResult, run
from trawlkit.units import Q_, ureg

__all__ = [
    "Compat",
    "DesignCase",
    "DesignResult",
    "Q_",
    "__version__",
    "dimensions",
    "drag",
    "io",
    "materials",
    "model",
    "net",
    "netting",
    "performance",
    "power",
    "rigging",
    "run",
    "units",
    "ureg",
    "vessel",
]
__version__ = "0.1.0"
