"""Spot: RMS/GEO/centroid; ray fan с опорой на chief (pupil coord ~ 0)."""
from __future__ import annotations
import numpy as np


def image_points(res, z: float):
    b = res.bundle
    dz = b.direction[:, 2]
    safe = np.abs(dz) > 1e-12
    t = np.where(safe, (z - b.origin[:, 2]) / np.where(safe, dz, 1.0), np.inf)
    m = b.alive & np.isfinite(t)
    p = b.origin + np.where(m, t, 0.0)[:, None] * b.direction
    return p[m][:, :2], b.intensity[m]


def spot_stats(pts, w):
    c = (pts * w[:, None]).sum(0) / w.sum()
    d = np.hypot(*(pts - c).T)
    return {"centroid": c,
            "rms": float(np.sqrt((d ** 2 * w).sum() / w.sum())),
            "geo_max": float(d.max()),
            "n": int(len(pts))}


def airy_radius_um(wl_um: float, fno: float) -> float:
    return 1.22 * wl_um * fno * 1000.0


def ray_fan(built, fi: int, wi: int, n: int = 21, axis: str = "y"):
    from minizemax.engine.source import make_bundle
    from minizemax.engine.tracer import SequentialTracer
    from minizemax.system.paraxial import paraxial_trace
    s = np.linspace(-1, 1, n)
    px = np.zeros(n) if axis == "y" else s
    py = s if axis == "y" else np.zeros(n)
    b = make_bundle(built, fi, wi, px=px, py=py, w=np.ones(n) / n)
    r = SequentialTracer(built.surfaces).trace(b)
    pd = paraxial_trace(built, b.wavelength[0], built.sysdata.fields[fi].y)
    pts, _ = image_points(r, pd.img_z)
    s_alive = s[r.bundle.alive]
    if len(s_alive) == 0:
        return s, np.zeros(n), np.zeros(n)
    i0 = int(np.argmin(np.abs(s_alive)))     # chief = pupil coord ~ 0
    ch = pts[i0]
    return s_alive, pts[:, 0] - ch[0], pts[:, 1] - ch[1]
