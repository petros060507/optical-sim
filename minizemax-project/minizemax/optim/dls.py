"""DLS (Левенберг-Марквардт) вручную: прогресс по итерациям через callback."""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np


@dataclass
class OptResult:
    x: np.ndarray
    merit0: float
    merit1: float
    niters: int
    history: list = field(default_factory=list)


class DLSOptimizer:
    def __init__(self, pres, mf):
        self.pres, self.mf = pres, mf

    def _jacobian(self, mf, x, f):
        J = np.zeros((len(f), len(x)))
        for j in range(len(x)):
            h = 1e-6 * max(1.0, abs(x[j]))
            xp = x.copy(); xp[j] += h
            J[:, j] = (mf.residuals(xp) - f) / h
        return J

    def run(self, max_iters: int = 25, callback=None, lam0: float = 1e-3) -> OptResult:
        mf = self.mf
        x = mf.x0().astype(float)
        if x.size == 0:
            f = mf.residuals(x)
            m = float(f @ f)
            return OptResult(x, m, m, 0, [m])
        lo, hi = mf.bounds()
        f = mf.residuals(x)
        merit = float(f @ f)
        merit0, history = merit, [merit]
        lam = lam0
        it = -1
        for it in range(max_iters):
            J = self._jacobian(mf, x, f)
            A = J.T @ J
            g = J.T @ f
            d = np.maximum(np.diag(A), 1e-12)
            improved = False
            for _ in range(12):
                try:
                    dx = np.linalg.solve(A + lam * np.diag(d), -g)
                except np.linalg.LinAlgError:
                    lam *= 4.0
                    continue
                xn = np.clip(x + dx, lo, hi)
                fn = mf.residuals(xn)
                mn = float(fn @ fn)
                if mn < merit:
                    x, f, merit = xn, fn, mn
                    lam = max(lam * 0.3, 1e-9)
                    improved = True
                    break
                lam *= 4.0
            history.append(merit)
            if callback:
                callback(it, merit)
            if not improved:
                break
            if abs(history[-2] - history[-1]) < 1e-12 * max(1.0, history[-1]):
                break
        mf.set_x(x)
        return OptResult(x, merit0, merit, it + 1, history)
