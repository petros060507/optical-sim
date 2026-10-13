"""Один луч — DTO (слайд Stage 1) и отладка."""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np


@dataclass(slots=True)
class Ray:
    origin: np.ndarray
    direction: np.ndarray
    wavelength: float
    intensity: float = 1.0
    opl: float = 0.0
    alive: bool = True
    history: list = field(default_factory=list)

    def at(self, t: float) -> np.ndarray:
        return self.origin + t * self.direction

    def propagate(self, t: float) -> None:
        self.origin = self.at(t)

    def normalize(self) -> None:
        self.direction = self.direction / np.linalg.norm(self.direction)

    def add_opl(self, n: float, t: float) -> None:
        self.opl += n * t

    def attenuate(self, k: float) -> None:
        self.intensity *= k
