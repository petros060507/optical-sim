
"""Регрессия рендер-цепочки: Sellmeier/tracer/scene3d не дают ни крэша, ни warnings."""
import warnings
import numpy as np
import pytest
from minizemax.system.prescription import Prescription
from minizemax.core.materials import glass, n_at
from minizemax.analysis.scene3d import build_scene

CONFIGS = ["examples/doublet.zmx-lite", "examples/cooke_triplet.yaml", "examples/fourf_4x.yaml"]


def test_sellmeier_finite_in_visible():
    # защита не должна превращать валидный диапазон в nan
    for name in ("N-BK7", "N-F2", "N-SK16"):
        for wl in (0.4861, 0.5876, 0.6563):
            n = float(n_at(glass(name), wl))
            assert np.isfinite(n) and n > 1.0, (name, wl, n)


@pytest.mark.parametrize("cfg", CONFIGS)
def test_build_scene_no_crash_no_warning(cfg):
    try:
        pres = Prescription.load(cfg)
    except FileNotFoundError:
        pytest.skip(f"нет {cfg}")
    built = pres.build()
    with warnings.catch_warnings():
        warnings.simplefilter("error")          # docs: «no warnings emitted»
        sc = build_scene(built, 0, 0, n_rays=24)
    # инвариант формы (пустые массивы допустимы, рассогласование — нет)
    assert sc.line_verts.ndim == 3 and sc.line_verts.shape[1:] == (2, 3)
    assert sc.line_colors.shape == sc.line_verts.shape[:2] + (4,)
