"""SystemData: апертура, длины волн, поля, семплирование (mutable для UI)."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Wavelength:
    um: float
    weight: float = 1.0
    primary: bool = False


@dataclass
class Field:
    y: float          # градусы (объект в бесконечности)
    weight: float = 1.0


@dataclass
class ApertureDef:
    type: str         # "EPD" | "FNO"
    value: float


@dataclass
class Sampling:
    kind: str = "hexapolar"   # "hexapolar" | "rect"
    rings: int = 3


@dataclass
class SystemData:
    aperture: ApertureDef
    wavelengths: list
    fields: list
    sampling: Sampling = field(default_factory=Sampling)

    @property
    def primary_wl(self):
        for w in self.wavelengths:
            if w.primary:
                return w.um
        return self.wavelengths[0].um
