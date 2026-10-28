"""Геометрическая валидация рецепта: перекрытия поверхностей, краевые толщины."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

MIN_T = 0.1  # мм, минимальная осевая/краевая толщина


@dataclass
class Issue:
    row: int      # индекс строки в pres.lens.rows
    msg: str


def _sag(radius, conic, r):
    if not np.isfinite(radius):
        return 0.0
    q = 1.0 - (1.0 + conic) * r * r / (radius * radius)
    if q <= 0.0:
        return None
    return r * r / (radius * (1.0 + np.sqrt(q)))


def check_prescription(pres, min_t: float = MIN_T):
    issues = []
    rows = pres.lens.real_rows()
    idx = [i for i, r in enumerate(pres.lens.rows) if r.surf not in ("OBJ", "IMA")]
    for a, r in enumerate(rows):
        if np.isfinite(r.radius) and _sag(r.radius, r.conic, r.semi_dia) is None:
            issues.append(Issue(idx[a],
                f"surf {r.surf}: semi-dia {r.semi_dia:.2f} too large for R={r.radius:.3f} "
                f"(sag undefined)"))
    for a in range(len(rows) - 1):
        r1, r2 = rows[a], rows[a + 1]
        t = r1.thickness
        if not np.isfinite(t):
            continue
        if t < min_t:
            issues.append(Issue(idx[a], f"surf {r1.surf}: thickness {t:.3f} < {min_t} mm"))
            continue
        rr = min(r1.semi_dia, r2.semi_dia)
        s1, s2 = _sag(r1.radius, r1.conic, rr), _sag(r2.radius, r2.conic, rr)
        if s1 is None or s2 is None:
            continue
        edge = t + s2 - s1
        if edge < min_t:
            issues.append(Issue(idx[a],
                f"surf {r1.surf}->{r2.surf}: edge thickness {edge:.3f} < {min_t} mm "
                f"(surfaces overlap at edge)"))
    return issues


# --- extended geometry checks (auto-added by fix_validation.py) ------------
from minizemax.system.geometry_checks import check_geometry_extended as _ext_geo_checks

_orig_check_prescription = check_prescription


def check_prescription(pres):  # noqa: F811  (wrapper: base checks + extended geometry)
    issues = list(_orig_check_prescription(pres))
    try:
        issues.extend(_ext_geo_checks(pres))
    except Exception:  # auxiliary checks must never break the UI
        pass
    return issues
