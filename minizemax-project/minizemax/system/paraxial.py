"""Параксиал y-nu: EFL, BFL, f/#, зрачки, маргинальный/chief, данные для Зейделя."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from minizemax.core.materials import n_at


@dataclass
class ParaxRay:
    y: np.ndarray; u_b: np.ndarray; u_a: np.ndarray; n1: np.ndarray; n2: np.ndarray


@dataclass
class ParaxialData:
    wl: float; efl: float; bfl: float; fno: float
    ep_z: float; ep_r: float; xp_z: float; xp_r: float
    img_z: float; img_h: float
    curv: np.ndarray; z: np.ndarray
    marg: ParaxRay; chief: ParaxRay


def _trace_ray(built, wl, y1, u1):
    ys, ub, ua, n1s, n2s = [], [], [], [], []
    y, u = y1, u1
    ns = len(built.surfaces)
    for i, s in enumerate(built.surfaces):
        n1 = n_at(s.mat_before, wl)
        n2 = -n1 if s.reflective else n_at(s.mat_after, wl)
        R = getattr(s, "radius", np.inf)
        c = 1.0 / R if np.isfinite(R) else 0.0
        ys.append(y); ub.append(u); n1s.append(n1); n2s.append(n2)
        u = (n1 * u - y * (n2 - n1) * c) / n2
        ua.append(u)
        gap = (built.surfaces[i + 1].z - s.z) if i + 1 < ns else 0.0
        y += gap * u
    return ParaxRay(np.array(ys), np.array(ub), np.array(ua),
                    np.array(n1s), np.array(n2s)), y, u


def paraxial_trace(built, wl, field_deg=0.0):
    sd = built.sysdata
    A, _, _ = _trace_ray(built, wl, 1.0, 0.0)
    B, _, _ = _trace_ray(built, wl, 0.0, 1.0)
    efl = -1.0 / A.u_a[-1]
    y1m = sd.aperture.value / 2.0 if sd.aperture.type == "EPD" else efl / (2 * sd.aperture.value)
    marg, y_mL, u_mL = _trace_ray(built, wl, y1m, 0.0)
    bfl = -y_mL / u_mL
    th = np.deg2rad(field_deg if field_deg != 0.0 else 1.0)
    si = built.stop_idx
    a_c = -th * B.y[si] / A.y[si] if A.y[si] != 0.0 else 0.0
    chief, y_cL, u_cL = _trace_ray(built, wl, a_c, th)
    z1, zL = built.surfaces[0].z, built.surfaces[-1].z
    ep_z = z1 - chief.y[0] / chief.u_b[0]
    ep_r = y1m
    s_xp = -y_cL / u_cL
    xp_z, xp_r = zL + s_xp, y_mL + u_mL * s_xp
    img_z, img_h = zL + bfl, y_cL + bfl * u_cL
    curv = np.array([1.0 / getattr(s, "radius", np.inf)
                     if np.isfinite(getattr(s, "radius", np.inf)) else 0.0
                     for s in built.surfaces])
    zs = np.array([s.z for s in built.surfaces])
    return ParaxialData(wl, efl, bfl, efl / (2 * y1m), ep_z, ep_r, xp_z, xp_r,
                        img_z, img_h, curv, zs, marg, chief)
