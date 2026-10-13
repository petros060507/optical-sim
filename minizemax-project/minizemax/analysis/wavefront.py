"""OPD относительно опорной сферы (центр = гауссова точка, R = до exit pupil)."""
from __future__ import annotations
import numpy as np
from minizemax.system.paraxial import paraxial_trace


def opd_waves(built, res, fi: int, wi: int) -> np.ndarray:
    b = res.bundle
    pd = paraxial_trace(built, b.wavelength[0], built.sysdata.fields[fi].y)
    C = np.array([0.0, pd.img_h, pd.img_z])
    R = abs(pd.img_z - pd.xp_z)
    t = (pd.img_z - b.origin[:, 2]) / b.direction[:, 2]
    P = b.origin + t[:, None] * b.direction
    opd = b.opl + (np.linalg.norm(P - C, axis=1) - R)
    ci = b.meta.get("chief_idx", 0)
    opd = opd - opd[ci]
    return opd[b.alive] / b.wavelength[b.alive]


def wavefront_stats(opd: np.ndarray) -> dict:
    return {"pv": float(opd.max() - opd.min()),
            "rms": float(np.sqrt(((opd - opd.mean()) ** 2).mean()))}
