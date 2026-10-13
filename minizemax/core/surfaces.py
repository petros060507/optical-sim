"""OpticalSurface ABC, PlaneSurface, SphericalSurface (conic через Ньютон)."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
import numpy as np
from minizemax.core.transform import Transform
from minizemax.core.materials import Material

EPS_T = 1e-9


@dataclass(slots=True)
class Hit:
    t: np.ndarray       # (N,)
    point: np.ndarray   # (N,3) global
    normal: np.ndarray  # (N,3) global
    valid: np.ndarray   # (N,) bool


class OpticalSurface(ABC):
    def __init__(self, transform, mat_before, mat_after, semi_dia,
                 reflective=False, name=""):
        self.transform = transform
        self.mat_before = mat_before
        self.mat_after = mat_after
        self.semi_dia = float(semi_dia)
        self.reflective = reflective
        self.name = name

    @property
    def z(self) -> float:
        return float(self.transform.t[2])

    def intersect(self, o_g, d_g) -> Hit:
        o_l = self.transform.to_local(o_g)
        d_l = self.transform.to_local_dir(d_g)
        t, p_l, n_l, valid = self._intersect_local(o_l, d_l)
        valid &= np.hypot(p_l[:, 0], p_l[:, 1]) <= self.semi_dia
        return Hit(t, self.transform.to_global(p_l),
                   self.transform.to_global_dir(n_l), valid)

    @abstractmethod
    def _intersect_local(self, o, d): ...

    def sag(self, r):
        return np.zeros_like(r)


class PlaneSurface(OpticalSurface):
    def _intersect_local(self, o, d):
        dz = d[:, 2]
        ok = np.abs(dz) > 1e-12
        t = np.where(ok, -o[:, 2] / np.where(ok, dz, 1.0), np.inf)
        p = o + np.where(np.isfinite(t), t, 0.0)[:, None] * d
        n_l = np.tile([0.0, 0.0, 1.0], (len(o), 1))
        return t, p, n_l, np.isfinite(t) & (t > EPS_T)


class SphericalSurface(OpticalSurface):
    def __init__(self, transform, mat_before, mat_after, semi_dia, radius,
                 conic=0.0, reflective=False, name=""):
        super().__init__(transform, mat_before, mat_after, semi_dia, reflective, name)
        self.radius = float(radius)
        self.conic = float(conic)

    def sag(self, r):
        R, k = self.radius, self.conic
        return r * r / (R * (1.0 + np.sqrt(np.clip(1 - (1 + k) * r * r / (R * R), 0, None))))

    def _dsag_dr(self, r):
        R, k = self.radius, self.conic
        return r / (R * np.sqrt(np.clip(1 - (1 + k) * r * r / (R * R), 1e-12, None)))

    def _intersect_local(self, o, d):
        R = self.radius
        C = np.array([0.0, 0.0, R])
        oc = o - C
        b = np.einsum("ij,ij->i", oc, d)
        c = np.einsum("ij,ij->i", oc, oc) - R * R
        disc = b * b - c
        ok = disc >= 0
        sq = np.sqrt(np.where(ok, disc, 0.0))
        t1, t2 = -b - sq, -b + sq
        t = np.where(ok & (t1 > EPS_T), t1, t2)
        t = np.where(ok, t, np.inf)
        p = o + np.where(np.isfinite(t), t, 0.0)[:, None] * d
        on_cap = ((p[:, 2] - R) * R) < 0
        for _ in range(3):  # Ньютон для conic
            r = np.hypot(p[:, 0], p[:, 1])
            f = p[:, 2] - self.sag(r)
            ds = self._dsag_dr(r)
            rr = np.where(r > 0, r, 1.0)
            dr_dt = (p[:, 0] * d[:, 0] + p[:, 1] * d[:, 1]) / rr
            df_dt = d[:, 2] - ds * dr_dt
            t = t - f / np.where(np.abs(df_dt) > 1e-12, df_dt, 1.0)
            p = o + np.where(np.isfinite(t), t, 0.0)[:, None] * d
        r = np.hypot(p[:, 0], p[:, 1])
        ds = self._dsag_dr(r)
        rr = np.where(r > 0, r, 1.0)
        n_l = np.stack([-ds * p[:, 0] / rr, -ds * p[:, 1] / rr, np.ones_like(r)], axis=1)
        n_l /= np.linalg.norm(n_l, axis=1, keepdims=True)
        return t, p, n_l, ok & np.isfinite(t) & (t > EPS_T) & on_cap
