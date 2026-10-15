import numpy as np
from minizemax.analysis.scene3d import build_scene, to_gl
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


def test_scene_batches():
    sc = build_scene(Prescription.from_yaml(YAML).build(), 0, 0, n_rays=8, n_theta=16, n_r=4)
    assert len(sc.meshes) >= 5                      # 3 поверхности + ободья + стоп + детектор
    for m in sc.meshes:
        assert m.verts.dtype == np.float32 and m.faces.dtype == np.uint32
        assert np.isfinite(m.verts).all()
    assert sc.line_verts.ndim == 3 and sc.line_verts.shape[1:] == (2, 3)
    assert sc.line_colors.shape == sc.line_verts.shape[:2] + (4,)
    assert np.isfinite(sc.line_verts).all()
    assert to_gl(sc.line_verts.reshape(-1, 3)).shape[1] == 3
