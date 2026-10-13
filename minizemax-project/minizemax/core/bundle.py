"""RayBundle — SoA-контейнер N лучей (векторизация NumPy)."""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
from numpy.typing import NDArray

Arr = NDArray[np.float64]


@dataclass(slots=True)
class RayBundle:
    origin: Arr       # (N,3) мм
    direction: Arr    # (N,3) |d|=1
    wavelength: Arr   # (N,) мкм
    intensity: Arr    # (N,)
    opl: Arr          # (N,) мм
    alive: Arr        # (N,) bool
    meta: dict = field(default_factory=dict)

    def at(self, t: Arr) -> Arr:
        return self.origin + t[:, None] * self.direction

    def add_opl(self, n: Arr, t: Arr) -> None:
        self.opl = self.opl + n * t

    def kill(self, mask: Arr) -> None:
        self.alive &= ~mask

    @property
    def n_alive(self) -> int:
        return int(self.alive.sum())
