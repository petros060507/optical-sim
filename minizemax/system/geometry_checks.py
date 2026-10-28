"""Extended geometry validation: axial order, detector position, surface overlap.
Pure functions (no Qt). Issues are duck-compatible with validation issues
(.row / .msg) plus a `hard` flag: hard issues must not be committed silently."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class Issue:
    row: int
    msg: str
    hard: bool = True


def _sag(radius, conic, r):
    """Conic sag, same formula as core.surfaces:
    (r^2/R) / (1 + sqrt(1 - (1+k)(r/R)^2)); plane -> 0."""
    r = np.asarray(r, float)
    if not np.isfinite(radius):
        return np.zeros_like(r)
    rho = 1.0 - (1.0 + conic) * (r / radius) ** 2
    out = np.full_like(r, np.nan)
    ok = rho > 0.0
    out[ok] = (r[ok] ** 2 / radius) / (1.0 + np.sqrt(rho[ok]))
    return out


def check_geometry_extended(pres):
    issues = []
    rows = pres.lens.rows
    if not rows:
        return issues

    if rows[0].surf == "OBJ":
        t = rows[0].thickness
        if np.isfinite(t) and t <= 0:
            issues.append(Issue(0, f"object distance must be > 0 or inf (got {t:g})"))

    real = [(i, r) for i, r in enumerate(rows) if r.surf not in ("OBJ", "IMA")]
    z = 0.0
    pos = []
    for i, r in real:
        pos.append((i, r, z))
        z += r.thickness

    for k, (i, r, zv) in enumerate(pos):
        if np.isfinite(r.radius):
            rho_edge = 1.0 - (1.0 + r.conic) * (r.semi_dia / r.radius) ** 2
            if rho_edge <= 0.0:
                issues.append(Issue(i, f"semi-diameter {r.semi_dia:g} is outside the "
                                       f"sphere/conic domain of R={r.radius:g}"))
        if k + 1 < len(pos):
            i2, r2, zv2 = pos[k + 1]
            if r.reflective:
                continue                      # folded path after a mirror
            if r.thickness <= 0:
                issues.append(Issue(i, f"non-positive thickness {r.thickness:g}: surface "
                                       f"{r.surf} overlaps/crosses surface {r2.surf}"))
            else:
                r_ov = min(r.semi_dia, r2.semi_dia)
                if r_ov > 0:
                    rr = np.linspace(0.0, r_ov, 9)
                    gap = ((zv2 - zv) + _sag(r2.radius, r2.conic, rr)
                           - _sag(r.radius, r.conic, rr))
                    gmin = float(np.nanmin(gap))
                    if gmin <= 1e-9:
                        issues.append(Issue(i2, f"surfaces {r.surf} and {r2.surf} intersect "
                                                f"inside clear aperture (min gap {gmin:.4f} mm)"))
        else:
            if not r.reflective and r.thickness <= 0:
                issues.append(Issue(i, f"detector plane is NOT after the last surface "
                                       f"(back focus {r.thickness:g} <= 0): rays will pass "
                                       f"through the screen"))
    return issues
