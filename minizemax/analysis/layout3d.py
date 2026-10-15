"""3D-раскладка (matplotlib fallback): поверхности вращения, ободья линз,
диафрагма, детектор, лучи. GPU-версия — в analysis/scene3d.py + ui/view3d_gl.py."""
from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  (регистрирует projection="3d")

from minizemax.engine.source import make_bundle
from minizemax.engine.tracer import SequentialTracer


def _mesh(s, n_theta=40, n_r=8):
    r = np.linspace(0.0, s.semi_dia, n_r)
    th = np.linspace(0.0, 2 * np.pi, n_theta)
    R, T = np.meshgrid(r, th)
    Z = s.z + s.sag(R)
    return R * np.cos(T), R * np.sin(T), Z


def _rim(s1, s2, n_theta=40):
    re = min(s1.semi_dia, s2.semi_dia)
    th = np.linspace(0.0, 2 * np.pi, n_theta)
    z1 = s1.z + float(s1.sag(np.array([re]))[0])
    z2 = s2.z + float(s2.sag(np.array([re]))[0])
    Z = np.stack([np.full(n_theta, z1), np.full(n_theta, z2)])
    X = np.stack([re * np.cos(th), re * np.cos(th)])
    Y = np.stack([re * np.sin(th), re * np.sin(th)])
    return X, Y, Z


def _is_glass(mat) -> bool:
    return getattr(mat, "name", "air") != "air"


def layout_3d(built, fi=0, wi=0, n_rays=16, n_theta=40, ax=None, show_rays=True):
    if ax is None:
        fig = plt.figure(figsize=(10, 7))
        ax = fig.add_subplot(111, projection="3d")

    for i, s in enumerate(built.surfaces):
        X, Y, Z = _mesh(s, n_theta=n_theta)
        if s.reflective:
            ax.plot_surface(Z, X, Y, color="silver", alpha=0.9, linewidth=0, antialiased=True)
        elif i == built.stop_idx and not _is_glass(s.mat_after):
            ax.plot_surface(Z, X, Y, color="lightgray", alpha=0.35, linewidth=0, antialiased=True)
        else:
            ax.plot_surface(Z, X, Y, color="lightblue", alpha=0.5, linewidth=0, antialiased=True)
        if i == built.stop_idx and not s.reflective:
            r0, r1 = s.semi_dia, 1.6 * s.semi_dia
            r = np.linspace(r0, r1, 4)
            th = np.linspace(0, 2 * np.pi, n_theta)
            R, T = np.meshgrid(r, th)
            Zs = np.full_like(R, s.z)
            ax.plot_surface(Zs, R * np.cos(T), R * np.sin(T),
                            color="0.3", alpha=0.95, linewidth=0, antialiased=True)
        if i + 1 < len(built.surfaces) and _is_glass(s.mat_after) \
                and s.mat_after is built.surfaces[i + 1].mat_before:
            X, Y, Z = _rim(s, built.surfaces[i + 1], n_theta)
            ax.plot_surface(Z, X, Y, color="steelblue", alpha=0.35, linewidth=0, antialiased=True)

    h = max(s.semi_dia for s in built.surfaces) * 1.2
    g = np.linspace(-h, h, 2)
    GX, GY = np.meshgrid(g, g)
    ax.plot_surface(np.full_like(GX, built.detector_z), GX, GY,
                    color="0.85", alpha=0.6, linewidth=0, antialiased=True)

    z0 = built.surfaces[0].z
    ax.plot([z0 - 5, built.detector_z], [0, 0], [0, 0], "k--", lw=0.7)

    if show_rays:
        ang = np.linspace(0, 2 * np.pi, n_rays, endpoint=False)
        px = np.concatenate([[0.0], 0.85 * np.cos(ang)])
        py = np.concatenate([[0.0], 0.85 * np.sin(ang)])
        b = make_bundle(built, fi, wi, px=px, py=py, w=np.ones(len(px)) / len(px))
        res = SequentialTracer(built.surfaces, record_history=True).trace(b)
        bb = res.bundle
        dz = bb.direction[:, 2]
        safe = np.abs(dz) > 1e-12
        tz = np.where(safe, (built.detector_z - bb.origin[:, 2]) / np.where(safe, dz, 1.0), np.nan)
        pz = bb.origin + np.where(np.isfinite(tz), tz, 0.0)[:, None] * bb.direction
        pts_all = res.history + [pz]
        for j in range(len(px)):
            P = np.array([h_[j] for h_ in pts_all])
            ok = np.isfinite(P[:, 2])
            ax.plot(pts[ok, 2], pts[ok, 1], "-", lw=0.7,

                    color={0: "C0", 1: "tab:orange", 2: "m", 3: "0.5"}[int(bb.status[j])],

                    alpha=0.85)

    d = 2.2 * max(s.semi_dia for s in built.surfaces)
    ax.set_box_aspect((built.detector_z - z0 + 10.0, d, d))
    ax.set_xlabel("z, mm"); ax.set_ylabel("x, mm"); ax.set_zlabel("y, mm")
    ax.set_title("3D layout")
    return ax
