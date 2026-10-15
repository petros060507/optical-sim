import numpy as np
from minizemax.analysis.lens_shape import check_elements
from minizemax.system.prescription import Prescription

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


def test_doublet_elements_physical():
    els = check_elements(Prescription.from_yaml(YAML))
    assert len(els) == 2
    assert els[0].shape == "biconvex"
    assert els[0].d_center > els[0].d_edge > 0.1      # двояковыпуклая
    assert els[1].d_edge > els[1].d_center > 0.1      # мениск с толстым краем
    assert all(e.ok for e in els)
