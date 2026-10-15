"""Геометрическая проверка формы линз: саги, центральные/краевые толщины, тип."""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np


@dataclass
class ElementCheck:
    name: str
    R1: float; R2: float
    d_center: float; d_edge: float
    D: float
    glass: str
    sag1: float; sag2: float
    shape: str
    ok: bool
    notes: list = field(default_factory=list)


def _sag(R, k, r):
    if not np.isfinite(R):
        return 0.0
    q = 1.0 - (1.0 + k) * r * r / (R * R)
    if q <= 0:
        return None
    return r * r / (R * (1.0 + np.sqrt(q)))


def _shape(R1, R2):
    p1 = np.sign(R1) if np.isfinite(R1) else 0
    p2 = np.sign(R2) if np.isfinite(R2) else 0
    if p1 > 0 and p2 < 0: return "biconvex"
    if p1 < 0 and p2 > 0: return "biconcave"
    if p1 == 0 or p2 == 0: return "plano"
    if p1 > 0 and p2 > 0: return "meniscus convex-concave"
    return "meniscus concave-convex"


def check_elements(pres, min_t=0.1):
    """Элемент = пара соседних поверхностей, между которыми стекло."""
    rows = pres.lens.real_rows()
    out = []
    for i in range(len(rows) - 1):
        r1 = rows[i]
        if not r1.glass:
            continue
        r2 = rows[i + 1]
        D = 2 * min(r1.semi_dia, r2.semi_dia)
        rr = D / 2
        s1 = _sag(r1.radius, r1.conic, rr)
        s2 = _sag(r2.radius, r2.conic, rr)
        notes = []; ok = True
        if s1 is None or s2 is None:
            notes.append("sag undefined: semi-dia too large for radius")
            ok = False
        s1 = 0.0 if s1 is None else s1
        s2 = 0.0 if s2 is None else s2
        d_edge = r1.thickness + s2 - s1
        if r1.thickness < min_t:
            notes.append(f"center thickness {r1.thickness:.3f} < {min_t}")
            ok = False
        if d_edge < min_t:
            notes.append(f"edge thickness {d_edge:.3f} < {min_t} (overlap)")
            ok = False
        out.append(ElementCheck(f"{r1.surf}-{r2.surf}", r1.radius, r2.radius,
                                r1.thickness, d_edge, D, r1.glass, s1, s2,
                                _shape(r1.radius, r2.radius), ok, notes))
    return out


def print_lens_check(pres) -> str:
    L = ["=== LENS SHAPE CHECK ==="]
    for e in check_elements(pres):
        L.append(f"[{e.name}] {e.glass}  {e.shape}  D={e.D:.2f} mm")
        L.append(f"   R1={e.R1:10.3f} R2={e.R2:10.3f}  sag1={e.sag1:+.3f} sag2={e.sag2:+.3f} mm")
        L.append(f"   d_center={e.d_center:7.3f}  d_edge={e.d_edge:7.3f} mm  -> "
                 + ("OK" if e.ok else "FAIL: " + "; ".join(e.notes)))
    return "\n".join(L)
