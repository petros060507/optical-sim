"""SequentialTracer, Detector, TraceResult, trace_field с кэшем."""
from __future__ import annotations
from dataclasses import dataclass
from time import perf_counter
import numpy as np
from minizemax.core.bundle import RayBundle
from minizemax.core.physics import snell_vector, reflect_vector


@dataclass(slots=True)
class DetectorHits:
    x: np.ndarray; y: np.ndarray; wl: np.ndarray; intensity: np.ndarray; opl: np.ndarray


@dataclass
class Detector:
    z: float
    half_size: float = 10.0
    nx: int = 256
    ny: int = 256
    hits: DetectorHits | None = None

    def register(self, b: RayBundle) -> None:
        m = b.alive & (b.direction[:, 2] > 1e-12)
        t = np.where(m, (self.z - b.origin[:, 2]) / np.where(m, b.direction[:, 2], 1.0), np.inf)
        ok = m & np.isfinite(t) & (t > 0)
        p = b.origin + np.where(ok, t, 0.0)[:, None] * b.direction
        h = self.half_size
        ok &= (np.abs(p[:, 0]) <= h) & (np.abs(p[:, 1]) <= h)
        self.hits = DetectorHits(p[ok, 0], p[ok, 1], b.wavelength[ok],
                                 b.intensity[ok], b.opl[ok])

    def irradiance_map(self) -> np.ndarray:
        h = self.half_size
        H, _, _ = np.histogram2d(self.hits.x, self.hits.y, bins=[self.nx, self.ny],
                                 range=[[-h, h], [-h, h]], weights=self.hits.intensity)
        return H


@dataclass
class TraceResult:
    bundle: RayBundle
    detector: Detector | None
    history: list
    alive_per_surface: list
    time_s: float


@dataclass
class SequentialTracer:
    surfaces: list
    detector: Detector | None = None
    eps: float = 1e-9
    record_history: bool = False

    def trace(self, b: RayBundle) -> TraceResult:
        t0 = perf_counter()
        log = []
        hist = [b.origin.copy()] if self.record_history else []
        for surf in self.surfaces:
            hit = surf.intersect(b.origin, b.direction)
            valid = hit.valid & b.alive
            n1 = surf.mat_before.n(b.wavelength)
            if surf.reflective:
                d_new = reflect_vector(b.direction, hit.normal)
            else:
                n2 = surf.mat_after.n(b.wavelength)
                d_new, tir = snell_vector(b.direction, hit.normal, n1, n2)
                valid &= ~tir
            p = b.origin + hit.t[:, None] * b.direction
            b.origin = np.where(valid[:, None], p + self.eps * d_new, b.origin)
            b.direction = np.where(valid[:, None], d_new, b.direction)
            b.add_opl(n1, np.where(valid, hit.t, 0.0))
            b.kill(~valid)
            log.append(b.n_alive)
            if self.record_history:
                hist.append(b.origin.copy())
        if self.detector is not None:
            self.detector.register(b)
        return TraceResult(b, self.detector, hist, log, perf_counter() - t0)


def trace_field(built, fi: int, wi: int, cache=None, detector=None, history=False):
    from minizemax.engine.source import make_bundle
    key = (fi, wi)
    if cache is not None and key in cache:
        return cache[key]
    res = SequentialTracer(built.surfaces, detector=detector,
                           record_history=history).trace(make_bundle(built, fi, wi))
    if cache is not None:
        cache[key] = res
    return res
