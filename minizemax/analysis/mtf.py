"""Геометрическая MTF = \характеристической функции пятна."""
from __future__ import annotations
import numpy as np


def mtf_geometric(pts, w, freqs, axis="y"):
    r = pts[:, 1] if axis == "y" else pts[:, 0]
    return np.abs((np.exp(-2j * np.pi * freqs[:, None] * r[None, :]) * w[None, :]).sum(1) / w.sum())
