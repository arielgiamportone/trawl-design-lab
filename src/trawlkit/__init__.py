"""trawlkit: motor de cálculo para el diseño de redes de arrastre.

Reimplementación en Python del modelo FAO A-3 desarrollado originalmente en Excel
(Giamportone, 2014-2024), generalizado a cualquier red parametrizable.
"""

from trawlkit.compat import Compat
from trawlkit.units import Q_, ureg

__all__ = ["Compat", "Q_", "__version__", "ureg"]
__version__ = "0.1.0"
