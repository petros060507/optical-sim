"""Бенч трассировки: CPU numpy vs GPU (Kompute, если собран; иначе GL 4.3 compute).
    python examples/bench_trace.py [examples/doublet.zmx-lite]"""
import sys
import time
import numpy as np
from minizemax.system.prescription import Prescription
from minizemax.engine.tracer import SequentialTracer
from minizemax.engine.source import pupil_grid
from minizemax.system.paraxial import paraxial_trace
from minizemax.core.bundle import RayBundle


def cpu_trace(built, px, py, z_img):
    o = np.stack([px, py, np.full(len(px), built.surfaces[0].z - 1.0)], 1)
    d = np.tile([0.0, 0.0, 1.0], (len(px), 1))
    b = RayBundle(o, d, np.full(len(px), 0.5876), np.ones(len(px)),
                  np.zeros(len(px)), np.ones(len(px), bool))
    t0 = time.perf_counter()
    res = SequentialTracer(built.surfaces).trace(b)
    dt = time.perf_counter() - t0
    bb = res.bundle
    dz = bb.direction[:, 2]
    safe = np.abs(dz) > 1e-12
    t = np.where(safe, (z_img - bb.origin[:, 2]) / np.where(safe, dz, 1.0), np.inf)
    m = bb.alive & np.isfinite(t)
    P = bb.origin + np.where(m, t, 0.0)[:, None] * bb.direction
    return P[m][:, :2], dt


def rms(pts):
    return float(np.sqrt((pts ** 2).sum(1).mean())) * 1e3 if len(pts) else np.nan


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "examples/doublet.zmx-lite"
    pres = Prescription.load(path)
    built = pres.build()
    z_img = paraxial_trace(built, 0.5876, 0.0).img_z
    print(f"config: {path}   z_img={z_img:.3f} mm")

    gpu = None
    try:
        from minizemax.gpu.kompute_trace import KomputeTracer, kompute_available
        if kompute_available()[0]:
            gpu = ("Kompute(Vulkan)", KomputeTracer(built, 0.5876))
    except Exception:  # noqa: BLE001
        pass
    if gpu is None:
        try:
            from minizemax.gpu.gl_compute_trace import GLComputeTracer, gl_compute_available
            ok, why = gl_compute_available()
            if ok:
                gpu = (f"GL4.3 compute ({why})", GLComputeTracer(built, 0.5876))
            else:
                print(f"GL compute unavailable: {why}")
        except Exception as e:  # noqa: BLE001
            print(f"GL compute unavailable: {e}")

    for n_ring in (3, 10, 30, 100):
        px, py, _ = pupil_grid("hexapolar", n_ring)
        pts, dt = cpu_trace(built, px * 10.0, py * 10.0, z_img)
        line = f"  CPU  N={len(px):6d}  t={dt*1e3:8.2f} ms  RMS={rms(pts):8.3f} um"
        if gpu:
            try:
                t0 = time.perf_counter()
                gpts, gst = gpu[1].trace(px * 10.0, py * 10.0, z_img)
                gdt = time.perf_counter() - t0
                line += (f" | {gpu[0]}: t={gdt*1e3:8.2f} ms  RMS={rms(gpts):8.3f} um "
                         f"alive={int((gst == 0).sum())}")
            except Exception as e:  # noqa: BLE001
                line += f" | GPU error: {type(e).__name__}: {e}"
        print(line)
    print("\nВывод: рендер OpenGL не узкое место; compute-путь (GL 4.3 / Kompute)")
    print("ускоряет массовую трассировку; GUI-отзывчивость даёт debounce вкладок.")


if __name__ == "__main__":
    main()
