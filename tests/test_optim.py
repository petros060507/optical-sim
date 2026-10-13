import numpy as np
from minizemax.system.prescription import Prescription
from minizemax.optim.merit import MeritFunction, Operand
from minizemax.optim.dls import DLSOptimizer
from minizemax.analysis.spot import spot_stats, image_points
from minizemax.engine.tracer import trace_field
from minizemax.system.paraxial import paraxial_trace

YAML = """
system:
  aperture: {type: EPD, value: 20.0}
  wavelengths_um: [{l: 0.5876, primary: true}]
  fields_deg: [{y: 0.0}]
lens_data:
  - {surf: OBJ, thickness: .inf}
  - {surf: 1, radius: 61.467, thickness: 12.0, glass: N-BK7, semi_dia: 10, variables: [radius]}
  - {surf: 2, radius: -44.644, thickness: 0,   semi_dia: 10,              variables: [radius]}
  - {surf: IMA}
"""


def _rms(pres):
    built = pres.build()
    res = trace_field(built, 0, 0)
    pd = paraxial_trace(built, 0.5876, 0.0)
    pts, w = image_points(res, pd.img_z)
    return spot_stats(pts, w)["rms"]


def test_optimizer_improves():
    pres = Prescription.from_yaml(YAML)
    before = _rms(pres)
    mf = MeritFunction(pres, [Operand("RMS", 0, 0, weight=1.0),
                              Operand("EFFL", target=50.0, weight=50.0)])
    DLSOptimizer(pres, mf).run(max_iters=40)
    assert _rms(pres) < before
