import numpy as np
from minizemax.core.physics import snell_vector, fresnel


def test_snell_scalar():
    th1 = np.deg2rad(np.linspace(0, 40, 300))
    d = np.stack([np.sin(th1), np.zeros_like(th1), np.cos(th1)], 1)
    n = np.tile([0.0, 0.0, 1.0], (300, 1))
    d_t, tir = snell_vector(d, n, np.ones(300), np.full(300, 1.5168))
    th2 = np.arcsin(np.clip(d_t[:, 0], -1, 1))
    assert np.allclose(np.sin(th1), 1.5168 * np.sin(th2), atol=1e-12)
    assert not tir.any()


def test_fresnel_brewster():
    th = np.deg2rad(np.linspace(0, 80, 200))
    d = np.stack([np.sin(th), np.zeros_like(th), np.cos(th)], 1)
    rs, rp = fresnel(d, np.tile([0.0, 0.0, 1.0], (200, 1)), np.ones(200), np.full(200, 1.5))
    assert np.all((rs >= 0) & (rs <= 1 + 1e-12))
    assert rp[np.argmin(np.abs(th - np.arctan(1.5)))] < 1e-5


def test_tir():
    th = np.deg2rad(60.0)
    d = np.tile([np.sin(th), 0.0, np.cos(th)], (4, 1))
    _, tir = snell_vector(d, np.tile([0.0, 0.0, 1.0], (4, 1)), np.full(4, 1.5), np.ones(4))
    assert tir.all()
