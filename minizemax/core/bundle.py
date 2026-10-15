"""RayBundle — SoA-контейнер N лучей (векторизация NumPy)."""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
from numpy.typing import NDArray

Arr = NDArray[np.float64]


STATUS_ALIVE = 0
STATUS_BLOCKED = 1   # срезано апертурой
STATUS_TIR = 2
STATUS_MISS = 3


@dataclass(slots=True)
class RayBundle:
    origin: Arr       # (N,3) мм
    direction: Arr    # (N,3) |d|=1
    wavelength: Arr   # (N,) мкм
    intensity: Arr    # (N,)
    opl: Arr          # (N,) мм
    alive: Arr        # (N,) bool
    meta: dict = field(default_factory=dict)
    status: Arr = None

    def __post_init__(self):
        if self.status is None:
            self.status = np.zeros(len(self.origin), np.int8)

    def at(self, t: Arr) -> Arr:
        return self.origin + t[:, None] * self.direction

    def add_opl(self, n: Arr, t: Arr) -> None:
        self.opl = self.opl + n * t

    def kill(self, mask: Arr) -> None:
        self.status = np.where(mask, STATUS_BLOCKED, self.status).astype(np.int8)
        self.alive = self.status == STATUS_ALIVE

    @property
    def n_alive(self) -> int:
        return int(self.alive.sum())
