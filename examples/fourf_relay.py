"""4f-релей: измерение бокового увеличения трассировкой КОНЕЧНОГО объекта.

Движок трассирует пучки от входного зрачка для объекта в бесконечности (поля =
углы), поэтому 4f-релей (объект в переднем фокусе L1) моделируется здесь
вручную: конусы лучей из точек объекта -> штатный SequentialTracer -> пересечение
с плоскостью IMA -> y_img / y_obj. Это и есть «смоделировать».

    python3 examples/fourf_relay.py examples/fourf_50_150.yaml
    python3 examples/fourf_relay.py examples/fourf_4x.yaml
"""
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from minizemax.system.prescription import Prescription
from minizemax.engine.tracer import SequentialTracer
from minizemax.core.bundle import RayBundle

R_PUPIL = 5.0                       # радиус диска-зрачка на L1, мм
Y0_LIST = [0.0, 1.0, 2.0, 3.0]      # высоты точек конечного объекта, мм
N_BK7 = 1.5168                      # n(BK7) на 0.5876 мкм


def disk(n_ring=3):
    pts = [(0.0, 0.0)]
    for i in range(1, n_ring + 1):
        r = R_PUPIL * i / n_ring
        for k in range(6 * i):
            a = 2 * np.pi * k / (6 * i)
            pts.append((r * np.cos(a), r * np.sin(a)))
    return np.array(pts)


def trace_object(built, y0, z_src, z_pup, z_img):
    """Конус из точки (0,y0,z_src) через диск в z_pup -> средняя высота на z_img."""
    d = disk()
    o = np.tile([0.0, y0, z_src], (len(d), 1))
    hit = np.stack([d[:, 0], d[:, 1], np.full(len(d), z_pup)], 1)
    dirv = hit - o
    dirv /= np.linalg.norm(dirv, axis=1, keepdims=True)
    b = RayBundle(o, dirv, np.full(len(d), 0.5876), np.ones(len(d)),
                  np.zeros(len(d)), np.ones(len(d), bool))
    res = SequentialTracer(built.surfaces, record_history=True).trace(b)
    bb = res.bundle
    dz = bb.direction[:, 2]
    safe = np.abs(dz) > 1e-12
    t = np.where(safe, (z_img - bb.origin[:, 2]) / np.where(safe, dz, 1.0), np.inf)
    m = bb.alive & np.isfinite(t)
    P = bb.origin + np.where(m, t, 0.0)[:, None] * bb.direction
    y_img = float(P[m, 1].mean()) if m.any() else np.nan
    return res, y_img, int(m.sum())


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "examples/fourf_50_150.yaml"
    pres = Prescription.load(path)
    built = pres.build()
    rows = pres.lens.rows                      # все строки, включая OBJ/IMA

    z_pup = built.surfaces[0].z                # вершина L1
    dist_obj = rows[0].thickness               # OBJ->L1 = расстояние до объекта
    z_src = z_pup - dist_obj
    z_img = built.detector_z                   # IMA
    f1_th = rows[1].radius / (N_BK7 - 1.0)     # f = R/(n-1) для plano-convex
    f2_th = rows[3].radius / (N_BK7 - 1.0)
    M_th = -f2_th / f1_th

    print(f"=== {path} ===")
    d_pp = built.surfaces[2].z - (built.surfaces[1].z - rows[1].thickness / N_BK7)
    print(f"f1={f1_th:.2f} mm  f2={f2_th:.2f} mm  d(H2_L1->H1_L2)={d_pp:.3f} mm "
          f"(= f1+f2 = {f1_th + f2_th:.3f})")
    print(f"объект z={z_src:.1f}  зрачок z={z_pup:.1f}  изображение z={z_img:.1f}  "
          f"(obj->img = {z_img - z_src:.1f} = 2*(f1+f2) = {2 * (f1_th + f2_th):.1f})")
    print(f"теория 4f: M = -f2/f1 = {M_th:.3f}x\n")
    print(f"{'y_obj':>7} {'y_img':>9} {'M=y_img/y_obj':>14} {'n_live':>7}")

    meas = []
    for y0 in Y0_LIST:
        _, y_img, nl = trace_object(built, y0, z_src, z_pup, z_img)
        M = y_img / y0 if y0 != 0 else np.nan
        if y0 != 0:
            meas.append(M)
        print(f"{y0:7.2f} {y_img:9.3f} {M:14.3f} {nl:7d}")

    M_meas = float(np.mean(meas))
    print(f"\nизмеренное M = {M_meas:.3f}x  (теория {M_th:.3f}x, расхождение "
          f"{abs(M_meas - M_th) / abs(M_th) * 100:.2f}% — от толщины/аберраций)")
    verdict = ("4x" if abs(abs(M_meas) - 4) < 0.1
               else "3x" if abs(abs(M_meas) - 3) < 0.1 else "?")
    print(f"ВЕРДИКТ: увеличение {verdict} (перевёрнутое, M<0).")

    # 3D-ход лучей релея
    fig = plt.figure(figsize=(11, 6))
    ax = fig.add_subplot(111, projection="3d")
    for s in built.surfaces:
        r = np.linspace(0, s.semi_dia, 8)
        th = np.linspace(0, 2 * np.pi, 40)
        R, T = np.meshgrid(r, th)
        ax.plot_surface(s.z + s.sag(R), R * np.cos(T), R * np.sin(T),
                        color="lightblue", alpha=0.25, linewidth=0)
    for y0, col in [(0.0, "C0"), (3.0, "C1"), (-3.0, "C3")]:
        res, _, _ = trace_object(built, y0, z_src, z_pup, z_img)
        bb = res.bundle
        dz = bb.direction[:, 2]
        safe = np.abs(dz) > 1e-12
        t = np.where(safe, (z_img - bb.origin[:, 2]) / np.where(safe, dz, 1.0), np.nan)
        pz = bb.origin + np.where(np.isfinite(t), t, 0.0)[:, None] * bb.direction
        pts_all = res.history + [pz]
        for j in range(len(bb.origin)):
            P = np.array([h[j] for h in pts_all])
            ok = np.isfinite(P[:, 2])
            ax.plot(P[ok, 2], P[ok, 1], P[ok, 0], color=col, lw=0.6, alpha=0.8)
    ax.set_xlabel("z, mm"); ax.set_ylabel("y, mm"); ax.set_zlabel("x, mm")
    ax.set_title(f"4f relay  f1={f1_th:.0f}  f2={f2_th:.0f}  M={M_meas:.2f}x")
    fig.tight_layout()
    out = path.replace(".yaml", "_rays.png")
    fig.savefig(out, dpi=130)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
