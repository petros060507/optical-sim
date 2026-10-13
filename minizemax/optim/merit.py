"""MeritFunction: operand'ы + переменные из строк LDE."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from minizemax.engine.tracer import trace_field
from minizemax.analysis.spot import spot_stats, image_points
from minizemax.system.paraxial import paraxial_trace
from minizemax.analysis.distortion import distortion_pct


@dataclass(frozen=True)
class Operand:
    kind: str                 # "RMS" | "EFFL" | "TOTR" | "DIST"
    field: int = 0
    wl: int = 0
    target: float = 0.0
    weight: float = 1.0


_BOUNDS = {"radius": (-5000.0, 5000.0), "thickness": (0.2, 300.0),
           "conic": (-10.0, 10.0), "semi_dia": (0.5, 100.0)}


class MeritFunction:
    def __init__(self, pres, ops):
        self.pres = pres
        self.ops = ops
        self.vars = [(ri, p) for ri, row in enumerate(pres.lens.rows) for p in row.variables]

    def x0(self) -> np.ndarray:
        return np.array([getattr(self.pres.lens.rows[ri], p) for ri, p in self.vars], float)

    def bounds(self):
        return (np.array([_BOUNDS[p][0] for _, p in self.vars]),
                np.array([_BOUNDS[p][1] for _, p in self.vars]))

    def set_x(self, x) -> None:
        for (ri, p), v in zip(self.vars, x):
            setattr(self.pres.lens.rows[ri], p, float(v))

    def _value(self, built, cache, op) -> float:
        nf, nw = len(built.sysdata.fields), len(built.sysdata.wavelengths)
        if not (0 <= op.field < nf and 0 <= op.wl < nw):
            raise ValueError(f"Operand {op.kind}: field={op.field}, wl={op.wl} out of range "
                             f"(fields 0..{nf-1}, wl 0..{nw-1}). Press Default MF.")
        if op.kind == "RMS":
            res = trace_field(built, op.field, op.wl, cache)
            pd = paraxial_trace(built, built.sysdata.wavelengths[op.wl].um,
                                built.sysdata.fields[op.field].y)
            pts, w = image_points(res, pd.img_z)
            return spot_stats(pts, w)["rms"] if len(pts) else 1e6
        if op.kind == "EFFL":
            return paraxial_trace(built, built.sysdata.primary_wl, 0.0).efl
        if op.kind == "TOTR":
            return built.detector_z - built.surfaces[0].z
        if op.kind == "DIST":
            return distortion_pct(built, op.field, op.wl)
        raise ValueError(f"Unknown operand kind: {op.kind!r}")

    def residuals(self, x) -> np.ndarray:
        self.set_x(x)
        built = self.pres.build()
        cache = {}
        return np.array([np.sqrt(op.weight) * (self._value(built, cache, op) - op.target)
                         for op in self.ops])

    @classmethod
    def default_rms_spot(cls, pres) -> "MeritFunction":
        ops = [Operand("RMS", fi, wi, weight=f.weight * w.weight)
               for fi, f in enumerate(pres.sysdata.fields)
               for wi, w in enumerate(pres.sysdata.wavelengths)]
        return cls(pres, ops)
