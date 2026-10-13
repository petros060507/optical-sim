"""Векторные Снеллиус, отражение, Френель."""
from __future__ import annotations
import numpy as np


def orient_normal(d, n):
    """Нормаль против направления луча (n·d < 0)."""
    flip = np.einsum("ij,ij->i", d, n) > 0
    return np.where(flip[:, None], -n, n)


def reflect_vector(d, n):
    return d - 2.0 * np.einsum("ij,ij->i", d, n)[:, None] * n


def snell_vector(d, n, n1, n2):
    """(d_refracted, tir_mask)."""
    n = orient_normal(d, n)
    eta = n1 / n2
    cos_i = -np.einsum("ij,ij->i", d, n)
    sin2_t = eta ** 2 * (1.0 - cos_i ** 2)
    tir = sin2_t > 1.0
    cos_t = np.sqrt(np.clip(1.0 - sin2_t, 0.0, None))
    return eta[:, None] * d + (eta * cos_i - cos_t)[:, None] * n, tir


def fresnel(d, n, n1, n2):
    """Rs, Rp по интенсивности; TIR -> 1."""
    n = orient_normal(d, n)
    cos_i = -np.einsum("ij,ij->i", d, n)
    ratio = n1 / n2
    sin2_t = ratio ** 2 * (1.0 - cos_i ** 2)
    tir = sin2_t > 1.0
    cos_t = np.sqrt(np.clip(1.0 - sin2_t, 0.0, None))
    rs = ((n1 * cos_i - n2 * cos_t) / (n1 * cos_i + n2 * cos_t)) ** 2
    rp = ((n1 * cos_t - n2 * cos_i) / (n1 * cos_t + n2 * cos_i)) ** 2
    return np.where(tir, 1.0, rs), np.where(tir, 1.0, rp)
