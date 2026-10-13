import numpy as np
from minizemax.core.bundle import RayBundle
from minizemax.core.surfaces import PlaneSurface, SphericalSurface
from minizemax.core.transform import Transform
from minizemax.core.materials import AIR, ConstantMaterial
from minizemax.engine.tracer import SequentialTracer, Detector
from minizemax.system.paraxial import paraxial_trace
from minizemax.system.lens_data import LensData, SurfaceRow, build_system
from minizemax.system.system_data import SystemData, ApertureDef, Wavelength, Field


def _singlet():
    sd = SystemData(ApertureDef("EPD", 2.0), [Wavelength(0.5876, primary=True)], [Field(0.0)])
    lens = LensData([SurfaceRow("OBJ", thickness=np.inf),
                     SurfaceRow("1", 61.467, 12.0, "N-BK7", 12.5),
                     SurfaceRow("2", -44.644, 0.0, None, 12.5),
                     SurfaceRow("IMA")])
    return build_system(sd, lens)


def test_tir_kills():
    s = PlaneSurface(Transform.identity(), ConstantMaterial("g", 1.5), AIR, 10.0)
    th = np.deg2rad(60.0)
    b = RayBundle(np.tile([0.0, 0.0, -5.0], (8, 1)),
                  np.tile([np.sin(th), 0.0, np.cos(th)], (8, 1)),
                  np.full(8, 0.55), np.ones(8), np.zeros(8), np.ones(8, bool))
    SequentialTracer([s]).trace(b)
    assert b.n_alive == 0


def test_mirror_R_over_2():
    R = -200.0
    m = SphericalSurface(Transform.identity(), AIR, AIR, 5.0, R, reflective=True)
    N = 2000
    o = np.stack([np.linspace(-1, 1, N), np.zeros(N), np.full(N, -50.0)], 1)
    b = RayBundle(o, np.tile([0.0, 0.0, 1.0], (N, 1)), np.full(N, 0.55),
                  np.ones(N), np.zeros(N), np.ones(N, bool))
    SequentialTracer([m]).trace(b)
    t = (R / 2 - b.origin[:, 2]) / b.direction[:, 2]
    p = b.origin + t[:, None] * b.direction
    assert np.hypot(p[:, 0], p[:, 1]).max() < 1e-3


def test_singlet_paraxial():
    built = _singlet()
    pd = paraxial_trace(built, 0.5876, 0.0)
    assert 40 < pd.efl < 60
    det = Detector(z=pd.img_z, half_size=1.0)
    N = 3000
    b = RayBundle(np.stack([np.linspace(-1, 1, N), np.zeros(N), np.full(N, -20.0)], 1),
                  np.tile([0.0, 0.0, 1.0], (N, 1)), np.full(N, 0.5876),
                  np.ones(N), np.zeros(N), np.ones(N, bool))
    SequentialTracer(built.surfaces, detector=det).trace(b)
    r = np.hypot(det.hits.x - det.hits.x.mean(), det.hits.y - det.hits.y.mean())
    assert r.mean() < 0.01
