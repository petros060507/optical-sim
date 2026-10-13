"""Transform: локальная <-> глобальная СК."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True, slots=True)
class Transform:
    R: np.ndarray   # (3,3) столбцы — локальные оси в глобальной СК
    t: np.ndarray   # (3,)

    @classmethod
    def identity(cls) -> "Transform":
        return cls(np.eye(3), np.zeros(3))

    @classmethod
    def translation(cls, z: float) -> "Transform":
        return cls(np.eye(3), np.array([0.0, 0.0, z]))

    def to_local(self, p): return (p - self.t) @ self.R
    def to_local_dir(self, d): return d @ self.R
    def to_global(self, p): return p @ self.R.T + self.t
    def to_global_dir(self, d): return d @ self.R.T
