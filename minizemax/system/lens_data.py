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
    comment: str = ""                               # имя в LDE (Name column)


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


def auto_comments(real_rows) -> list:
    """Авто-имена поверхностей: L1.front / L1.back / 'L1.back L2.front' (склейка),
    M1 для зеркал, 'stop plate' для отдельной диафрагмы, суффикс STOP."""
    out = []
    el = 0
    mir = 0
    for i, r in enumerate(real_rows):
        g = r.glass
        pg = real_rows[i - 1].glass if i > 0 else None
        if r.reflective:
            mir += 1
            tags = [f"M{mir}"]
        elif g is None and pg is None:
            tags = ["stop plate" if r.stop else "plate"]
        else:
            tags = []
            if pg is not None and g != pg:
                tags.append(f"L{el}.back")
            if g is not None and g != pg:
                el += 1
                tags.append(f"L{el}.front")
            if g is not None and g == pg:
                tags.append(f"L{el}.mid")
        if r.stop and "stop" not in " ".join(tags):
            tags.append("STOP")
        out.append(" ".join(tags))
    return out
