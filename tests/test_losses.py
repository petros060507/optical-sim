import numpy as np
from minizemax.core.bundle import (RayBundle, STATUS_ALIVE, STATUS_BLOCKED, STATUS_MISS)
from minizemax.core.surfaces import SphericalSurface
from minizemax.core.transform import Transform
from minizemax.core.materials import AIR, glass
from minizemax.components import SphericalLens, DetectorScreen, assemble
from minizemax.engine.tracer import SequentialTracer
from minizemax.analysis.losses import loss_counts, loss_table
from minizemax.system.prescription import Prescription
from minizemax.system.system_data import SystemData, ApertureDef, Wavelength, Field

YAML = """
system:
  aperture: {type: EPD, value: 25.0}
  wavelengths_um: [{l: 0.5876, w: 1.0, primary: true}]
  fields_deg: [{y: 0.0}]
lens_data:
  - {surf: OBJ, thickness: .inf}
  - {surf: 1, radius: 122.794, thickness: 12.00, glass: N-SK16, semi_dia: 12.5}
  - {surf: 2, radius: -83.550, thickness: 2.85,  glass: N-F2,   semi_dia: 12.5}
  - {surf: 3, radius: -773.60, thickness: 46.30, semi_dia: 12.0, stop: true}
  - {surf: IMA}
"""


def _sd(epd=10.0):
    return SystemData(ApertureDef("EPD", epd),
                      [Wavelength(0.5876, primary=True)], [Field(0.0)])


def _beam(radius, n=400, z0=-30.0):
    o = np.stack([np.linspace(-radius, radius, n), np.zeros(n), np.full(n, z0)], 1)
    d = np.tile([0.0, 0.0, 1.0], (n, 1))
    return RayBundle(o, d, np.full(n, 0.5876), np.ones(n), np.zeros(n), np.ones(n, bool))


def test_blocked_with_stop_point():
    lens = SphericalLens(60.0, -60.0, 6.0, 8.0, glass("N-BK7"))   # semi=4 режет пучок 5
    pres = assemble([(lens, 30.0), (DetectorScreen(), 0.0)], _sd())
    res = SequentialTracer(pres.build().surfaces, record_history=True).trace(_beam(5.0))
    c = loss_counts(res)
    assert c["blocked(aperture)"] > 0 and c["alive"] > 0
    idx = int(np.where(res.bundle.status == STATUS_BLOCKED)[0][0])
    assert np.isfinite(res.stop_point[idx]).all()
    assert res.stop_surf[idx] >= 0


def test_miss_status():
    s = SphericalSurface(Transform.translation(0.0), AIR, AIR, 200.0, 50.0)
    b = _beam(200.0, n=401, z0=-80.0)
    res = SequentialTracer([s]).trace(b)
    c = loss_counts(res)
    assert c["miss(no hit)"] > 0 and c["alive"] > 0


def test_loss_table_totals():
    pres = Prescription.from_yaml(YAML)
    txt = loss_table(pres)
    assert "blocked(aperture)" in txt and "total" in txt
