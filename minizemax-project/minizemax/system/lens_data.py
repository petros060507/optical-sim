"""LDE: строки поверхностей + сборка BuiltSystem."""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
from minizemax.core.transform import Transform
from minizemax.core.materials import AIR, glass
from minizemax.core.surfaces import OpticalSurface, PlaneSurface, SphericalSurface


@dataclass
class SurfaceRow:
    surf: str
    radius: float = np.inf
    thickness: float = 0.0
    glass: str | None = None
    semi_dia: float = 10.0
    conic: float = 0.0
    stop: bool = False
    reflective: bool = False
    variables: list = field(default_factory=list)   # ["radius", "thickness"]


@dataclass
class LensData:
    rows: list

    def real_rows(self):
        return [r for r in self.rows if r.surf not in ("OBJ", "IMA")]


@dataclass
class BuiltSystem:
    surfaces: list
    detector_z: float
    stop_idx: int
    sysdata: object
    lens: "LensData"


def build_system(sysdata, lens) -> BuiltSystem:
    surfaces = []
    mat_prev = AIR
    z = 0.0
    stop_idx = None
    for i, row in enumerate(lens.real_rows()):
        mat_after = mat_prev if row.reflective else (glass(row.glass) if row.glass else AIR)
        tr = Transform.translation(z)
        if np.isfinite(row.radius):
            s = SphericalSurface(tr, mat_prev, mat_after, row.semi_dia, row.radius,
                                 row.conic, row.reflective, str(row.surf))
        else:
            s = PlaneSurface(tr, mat_prev, mat_after, row.semi_dia, row.reflective, str(row.surf))
        surfaces.append(s)
        if row.stop:
            stop_idx = i
        if not row.reflective:
            mat_prev = mat_after
        z += row.thickness
    if stop_idx is None:
        stop_idx = int(np.argmin([s.semi_dia for s in surfaces]))
    return BuiltSystem(surfaces, z, stop_idx, sysdata, lens)
