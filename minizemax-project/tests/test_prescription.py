from minizemax.system.prescription import Prescription
from minizemax.system.paraxial import paraxial_trace

YAML = """
system:
  aperture: {type: EPD, value: 25.0}
  wavelengths_um: [{l: 0.5876, w: 1.0, primary: true},{l: 0.4861, w: 1.0},{l: 0.6563, w: 1.0}]
  fields_deg: [{y: 0.0},{y: 3.0}]
  sampling: {kind: hexapolar, rings: 3}
lens_data:
  - {surf: OBJ, thickness: .inf}
  - {surf: 1, radius: 122.794, thickness: 12.00, glass: N-SK16, semi_dia: 12.5}
  - {surf: 2, radius: -83.550, thickness: 2.85,  glass: N-F2,   semi_dia: 12.5}
  - {surf: 3, radius: -773.60, thickness: 46.30, semi_dia: 12.0, stop: true}
  - {surf: IMA}
"""


def test_load_build():
    built = Prescription.from_yaml(YAML).build()
    assert len(built.surfaces) == 3 and built.detector_z > 0


def test_doublet_efl():
    pd = paraxial_trace(Prescription.from_yaml(YAML).build(), 0.5876, 0.0)
    assert pd.efl > 0 and pd.bfl > 0 and 2 < pd.fno < 10


def test_roundtrip(tmp_path):
    pres = Prescription.from_yaml(YAML)
    p = tmp_path / "rt.yaml"
    pres.save(str(p))
    p2 = Prescription.load(str(p))
    assert len(p2.lens.rows) == len(pres.lens.rows)
    assert p2.sysdata.aperture.value == pres.sysdata.aperture.value
