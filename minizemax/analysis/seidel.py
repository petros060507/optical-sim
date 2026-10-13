"""Суммы Зейделя S_I-S_V по параксиальному ходу двух лучей."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from minizemax.system.paraxial import paraxial_trace


@dataclass(frozen=True)
class SeidelSums:
    S1: float; S2: float; S3: float; S4: float; S5: float; H: float


def seidel_sums(built, wl: float, field_deg: float) -> SeidelSums:
    fd = field_deg if field_deg != 0.0 else 1.0
    pd = paraxial_trace(built, wl, fd)
    m, c, cv = pd.marg, pd.chief, pd.curv
    H = m.n1[0] * (c.y[0] * m.u_b[0] - m.y[0] * c.u_b[0])
    S = [0.0] * 5
    for i in range(len(cv)):
        du = m.u_a[i] / m.n2[i] - m.u_b[i] / m.n1[i]
        A = m.n1[i] * (m.y[i] * cv[i] + m.u_b[i])
        Ab = c.n1[i] * (c.y[i] * cv[i] + c.u_b[i])
        P = H * H * cv[i] * (1.0 / m.n2[i] - 1.0 / m.n1[i])
        S[0] += m.y[i] * A * A * du
        S[1] += m.y[i] * A * Ab * du
        S[2] += m.y[i] * Ab * Ab * du
        S[3] += P
        if A != 0.0:
            S[4] += (Ab ** 3 / A) * m.y[i] * du + (Ab / A) * P
    return SeidelSums(*S, H)
