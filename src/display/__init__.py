from .base import BaseDisplay
from .simulator import Simulator

DRIVERS = {
    "simulator": Simulator,
}

try:
    from .inky_impression import InkyImpression
    DRIVERS["inky_impression"] = InkyImpression
except ImportError:
    pass


def create_display(driver_name, **kwargs):
    cls = DRIVERS.get(driver_name)
    if cls is None:
        known = ", ".join(sorted(DRIVERS))
        raise ValueError(
            f"Unknown display driver {driver_name!r}. Known: {known}"
        )
    return cls(**kwargs)