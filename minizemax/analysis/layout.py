"""2D layout: саг-профили + тангенциальный веер лучей до детектора."""
from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
from minizemax.engine.source import make_bundle
from minizemax.engine.tracer import SequentialTracer


def layout(built, fi=0, wi=0, n_rays=7, ax=None):
    if ax is None:
        _, ax = plt.subplots()
    for s in built.surfaces:
        r = np.linspace(-s.semi_dia, s.semi_dia, 80)
        ax.plot(s.z + s.sag(np.abs(r)), r, "k-", lw=1)
    ax.axvline(built.detector_z, color="gray", ls=":", lw=0.8)
    sa = np.linspace(-0.95, 0.95, n_rays)
    b = make_bundle(built, fi, wi, px=np.zeros(n_rays), py=sa, w=np.ones(n_rays) / n_rays)
    res = SequentialTracer(built.surfaces, record_history=True).trace(b)
    bb = res.bundle
    dz = bb.direction[:, 2]
    safe = np.abs(dz) > 1e-12
    tz = np.where(safe, (built.detector_z - bb.origin[:, 2]) / np.where(safe, dz, 1.0), np.nan)
    pz = bb.origin + np.where(np.isfinite(tz), tz, 0.0)[:, None] * bb.direction
    pts_all = res.history + [pz]
    for j in range(n_rays):
        pts = np.array([h[j] for h in pts_all])
        ok = np.isfinite(pts[:, 2])
        ax.plot(pts[ok, 2], pts[ok, 1], "-", lw=0.7,
                color="C0" if bb.alive[j] else "red", alpha=0.85)
    ax.set_xlabel("z, mm"); ax.set_ylabel("y, mm")
    ax.set_aspect("equal"); ax.set_title("Layout")
    return ax
