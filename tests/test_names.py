from minizemax.system.lens_data import auto_comments
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


def test_auto_comments_doublet():
    names = auto_comments(Prescription.from_yaml(YAML).lens.real_rows())
    assert names == ["L1.front", "L1.back L2.front", "L2.back STOP"]
