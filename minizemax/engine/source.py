"""PupilSampler: сетки зрачка + генерация пучка для (field, wl)."""
from __future__ import annotations
import numpy as np
from minizemax.core.bundle import RayBundle
from minizemax.system.paraxial import paraxial_trace


def pupil_grid(kind: str, rings: int = 3):
    if kind == "hexapolar":
        px_l, py_l = [0.0], [0.0]
        for i in range(1, rings + 1):
            r = i / rings
            for k in range(6 * i):
                a = 2 * np.pi * k / (6 * i)
                px_l.append(r * np.cos(a)); py_l.append(r * np.sin(a))
        px, py = np.array(px_l), np.array(py_l)
    else:
        n = rings * 2 + 1
        g = np.linspace(-1, 1, n)
        X, Y = np.meshgrid(g, g)
        m = X ** 2 + Y ** 2 <= 1
        px, py = X[m].astype(float), Y[m].astype(float)
    return px, py, np.ones(len(px)) / len(px)


def make_bundle(built, field_idx: int, wl_idx: int, px=None, py=None, w=None) -> RayBundle:
    sd = built.sysdata
    wl = sd.wavelengths[wl_idx].um
    f = sd.fields[field_idx]
    pd = paraxial_trace(built, wl, f.y)
    if px is None:
        px, py, w = pupil_grid(sd.sampling.kind, sd.sampling.rings)
    th = np.deg2rad(f.y)
    d = np.tile([0.0, np.sin(th), np.cos(th)], (len(px), 1))
    o = np.stack([px * pd.ep_r, py * pd.ep_r, np.full(len(px), pd.ep_z)], axis=1)
    z_start = built.surfaces[0].z - 1.0          # старт до 1-й поверхности
    o = o + ((z_start - pd.ep_z) / d[:, 2])[:, None] * d
    inten = w * f.weight * sd.wavelengths[wl_idx].weight
    b = RayBundle(o, d, np.full(len(px), wl), inten, np.zeros(len(px)), np.ones(len(px), bool))
    b.meta = {"chief_idx": 0, "px": px, "py": py}
    return b
