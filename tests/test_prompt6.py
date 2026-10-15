"""Prompt 6 'What must work': test systems A/B/C + acceptance criteria."""
import numpy as np
import pytest
from minizemax.components import (SphericalLens, SphericalMirror, ApertureStop,
                                  DetectorScreen, assemble)
from minizemax.components.plate import PlaneParallelPlate
from minizemax.core.bundle import (RayBundle, STATUS_ALIVE, STATUS_BLOCKED,
                                   STATUS_TIR, STATUS_MISS)
from minizemax.core.materials import glass, ConstantMaterial, n_at
from minizemax.engine.tracer import SequentialTracer, Detector
from minizemax.system.paraxial import paraxial_trace
from minizemax.system.validation import check_prescription
from minizemax.system.system_data import SystemData, ApertureDef, Wavelength, Field


def _sd(epd=10.0):
    return SystemData(ApertureDef("EPD", epd),
                      [Wavelength(0.5876, primary=True)], [Field(0.0)])


def _beam(radius, n=400, z0=-30.0, angle_deg=0.0, wl=0.5876):
    th = np.deg2rad(angle_deg)
    o = np.stack([np.linspace(-radius, radius, n), np.zeros(n), np.full(n, z0)], 1)
    d = np.tile([0.0, np.sin(th), np.cos(th)], (n, 1))
    return RayBundle(o, d, np.full(n, wl), np.ones(n), np.zeros(n), np.ones(n, bool))


# ── Test system A: plane-parallel plate ──────────────────────────────────────
def test_A_plate_direction_and_lateral_shift():
    g = ConstantMaterial("glass", 1.5)
    plate = PlaneParallelPlate(d=10.0, D=40.0, material=g)
    pres = assemble([(plate, 20.0), (DetectorScreen(20.0), 0.0)], _sd())
    th = np.deg2rad(30.0)
    o = np.array([[0.0, 0.0, -5.0]])
    d = np.array([[0.0, np.sin(th), np.cos(th)]])
    b = RayBundle(o, d, np.array([0.5876]), np.ones(1), np.zeros(1), np.ones(1, bool))
    res = SequentialTracer(pres.build().surfaces).trace(b)
    assert res.bundle.alive.all()
    assert np.allclose(res.bundle.direction[0], d[0], atol=1e-12)   # направление сохранено
    bb = res.bundle
    t = (10.0 - bb.origin[:, 2]) / bb.direction[:, 2]
    y_with = bb.origin[0, 1] + t[0] * bb.direction[0, 1]
    y_without = 15.0 * np.tan(th)
    assert np.isclose(y_without - y_with, plate.lateral_shift(th, 0.5876), rtol=1e-6)


def test_A_plate_edge_blocked_not_deleted():
    plate = PlaneParallelPlate(10.0, 2.0, ConstantMaterial("g", 1.5))   # semi=1
    pres = assemble([(plate, 5.0), (DetectorScreen(20.0), 0.0)], _sd())
    b = _beam(5.0)
    n0 = len(b.alive)
    res = SequentialTracer(pres.build().surfaces).trace(b)
    assert len(res.bundle.status) == n0                      # ничего не удалено
    assert (res.bundle.status == STATUS_BLOCKED).sum() > 0   # апертура -> BLOCKED
    assert (res.bundle.status == STATUS_ALIVE).sum() > 0


# ── Test system B: plano-convex lens ─────────────────────────────────────────
def test_B_plano_convex_focus():
    R, n = 50.0, n_at(glass("N-BK7"), 0.5876)
    lens = SphericalLens(R1=R, R2=np.inf, d=5.0, D=20.0, material=glass("N-BK7"))
    pres = assemble([(lens, 60.0), (DetectorScreen(10.0), 0.0)], _sd())
    pd = paraxial_trace(pres.build(), 0.5876, 0.0)
    assert np.isclose(pd.efl, 1.0 / ((n - 1.0) / R), rtol=1e-9)
    pres2 = assemble([(lens, pd.bfl), (DetectorScreen(10.0), 0.0)], _sd())
    b2 = pres2.build()
    res = SequentialTracer(b2.surfaces,
                           detector=Detector(z=b2.detector_z, half_size=10.0)
                           ).trace(_beam(1.0))
    r = np.hypot(res.detector.hits.x - res.detector.hits.x.mean(),
                 res.detector.hits.y - res.detector.hits.y.mean())
    assert r.mean() < 0.01


def test_B_plano_convex_edge_sag_undefined():
    lens = SphericalLens(R1=10.0, R2=np.inf, d=3.0, D=40.0, material=glass("N-BK7"))
    pres = assemble([(lens, 10.0), (DetectorScreen(), 0.0)], _sd())
    assert any("sag undefined" in i.msg for i in check_prescription(pres))


# ── Test system C: biconvex, vary R1,R2,d,D,material ─────────────────────────
@pytest.mark.parametrize("R1,R2,d,D,mat", [
    (60.0, -60.0, 6.0, 25.0, "N-BK7"),
    (40.0, -80.0, 4.0, 20.0, "N-F2"),
    (100.0, -100.0, 8.0, 30.0, "N-SK16"),
])
def test_C_biconvex_variations(R1, R2, d, D, mat):
    lens = SphericalLens(R1, R2, d, D, glass(mat))
    pres = assemble([(lens, 30.0), (DetectorScreen(15.0), 0.0)], _sd(D * 0.8))
    built = pres.build()
    pd = paraxial_trace(built, 0.5876, 0.0)
    assert np.isclose(pd.efl, lens.efl_paraxial(0.5876), rtol=1e-9)
    assert not check_prescription(pres)
    res = SequentialTracer(built.surfaces).trace(_beam(D * 0.35))
    assert res.bundle.alive.sum() > 0


def test_acceptance_tracer_logic_unchanged_by_params():
    lens = SphericalLens(60.0, -60.0, 6.0, 25.0, glass("N-BK7"))
    p1 = assemble([(lens, 30.0), (DetectorScreen(), 0.0)], _sd())
    e1 = paraxial_trace(p1.build(), 0.5876, 0.0).efl
    lens.R1, lens.R2 = 45.0, -45.0          # меняем параметры, трейсер тот же
    p2 = assemble([(lens, 30.0), (DetectorScreen(), 0.0)], _sd())
    e2 = paraxial_trace(p2.build(), 0.5876, 0.0).efl
    assert np.isclose(e1, SphericalLens(60., -60., 6., 25., glass("N-BK7")).efl_paraxial(0.5876))
    assert np.isclose(e2, lens.efl_paraxial(0.5876))
    assert e2 < e1


# ── Mirror / Aperture / Detector: valid + edge ───────────────────────────────
def test_mirror_valid_and_edge():
    m = SphericalMirror(-100.0, 30.0)
    b = _beam(1.0, n=500, z0=-30.0)
    res = SequentialTracer(m.surfaces()).trace(b)
    t = (-50.0 - b.origin[:, 2]) / b.direction[:, 2]
    p = b.origin + t[:, None] * b.direction
    assert np.hypot(p[:, 0], p[:, 1]).max() < 1e-3            # фокус R/2
    m2 = SphericalMirror(-100.0, 4.0)                        # edge: всё срезано
    res2 = SequentialTracer(m2.surfaces()).trace(_beam(5.0))
    assert (res2.bundle.status == STATUS_BLOCKED).sum() == 400


def test_aperture_valid_and_edge():
    sto = ApertureStop(20.0)
    res = SequentialTracer(sto.surfaces()).trace(_beam(5.0))
    assert res.bundle.alive.all()
    sto2 = ApertureStop(2.0)
    res2 = SequentialTracer(sto2.surfaces()).trace(_beam(5.0))
    assert (res2.bundle.status == STATUS_BLOCKED).sum() > 0
    assert len(res2.bundle.status) == 400


def test_detector_valid_and_edge():
    lens = SphericalLens(60.0, -60.0, 6.0, 25.0, glass("N-BK7"))
    pres = assemble([(lens, 30.0), (DetectorScreen(15.0), 0.0)], _sd())
    built = pres.build()
    pd = paraxial_trace(built, 0.5876, 0.0)
    det = Detector(z=pd.img_z, half_size=15.0)
    SequentialTracer(built.surfaces, detector=det).trace(_beam(2.0))
    assert len(det.hits.x) > 0
    det2 = Detector(z=-500.0, half_size=15.0)                 # edge: до оптики
    SequentialTracer(built.surfaces, detector=det2).trace(_beam(2.0))
    assert len(det2.hits.x) == 0


def test_acceptance_tir_status():
    g = ConstantMaterial("g", 1.5)
    plate = PlaneParallelPlate(10.0, 40.0, material=g)
    th = 60.0                                                  # из стекла наружу > крит.
    o = np.array([[0.0, 0.0, 5.0]])
    d = np.array([[0.0, np.sin(np.deg2rad(th)), -np.cos(np.deg2rad(th))]])
    b = RayBundle(o, d, np.array([0.5876]), np.ones(1), np.zeros(1), np.ones(1, bool))
    res = SequentialTracer(plate.surfaces()).trace(b)
    assert (res.bundle.status == STATUS_TIR).any() or (res.bundle.status == STATUS_MISS).any()
