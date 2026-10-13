"""Material Protocol, Sellmeier, каталог стёкол."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
import numpy as np


class Material(Protocol):
    def n(self, wl): ...


def n_at(mat, wl: float) -> float:
    return float(mat.n(np.array([wl]))[0])


@dataclass(frozen=True, slots=True)
class ConstantMaterial:
    name: str
    value: float

    def n(self, wl):
        return np.full(np.shape(wl), float(self.value))


@dataclass(frozen=True, slots=True)
class SellmeierGlass:
    name: str
    B: tuple
    C: tuple

    def n(self, wl):
        w2 = np.asarray(wl, float) ** 2
        return np.sqrt(1.0 + sum(b * w2 / (w2 - c) for b, c in zip(self.B, self.C)))


AIR = ConstantMaterial("air", 1.0)

CATALOG = {
    "N-BK7":  SellmeierGlass("N-BK7",  (1.03961212, 0.231792344, 1.01046945),
                                      (0.00600069867, 0.0200179144, 103.560653)),
    "N-F2":   SellmeierGlass("N-F2",   (1.34533359, 0.209073176, 0.942837246),
                                      (0.00997743871, 0.0470450761, 111.886764)),
    "N-SK16": SellmeierGlass("N-SK16", (1.34321408, 0.240453822, 0.995853298),
                                      (0.00704735403, 0.022900500, 92.7483455)),
}


def glass(name: str):
    if name not in CATALOG:
        raise KeyError(f"Glass {name!r} not found. Available: {list(CATALOG)}")
    return CATALOG[name]
