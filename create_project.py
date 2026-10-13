#!/usr/bin/env python3
"""apply_fixes2.py — геометрический валидатор + подсветка конфликтов в LDE."""
import pathlib

VALIDATION = '''\
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
'''

FIXES = [
    # lde_widget: хранение issues
    ("minizemax/ui/lde_widget.py",
     "        self.pres = pres\n        self._loading = False\n        self.setColumnCount(len(COLS))",
     "        self.pres = pres\n        self._loading = False\n        self._issues = []\n        self.setColumnCount(len(COLS))"),
    # lde_widget: применение подсветки после reload
    ("minizemax/ui/lde_widget.py",
     "            self.setItem(r, 8, self._chk(\"thickness\" in row.variables))\n        self._loading = False",
     "            self.setItem(r, 8, self._chk(\"thickness\" in row.variables))\n        self._loading = False\n        self._apply_issues()"),
    # lde_widget: методы set_issues/_apply_issues
    ("minizemax/ui/lde_widget.py",
     "    def _on_edit(self, r, c):",
     "    def set_issues(self, issues):\n"
     "        self._issues = list(issues)\n"
     "        self._apply_issues()\n"
     "\n"
     "    def _apply_issues(self):\n"
     "        from minizemax.ui.qt import QBrush, QColor\n"
     "        bad = {i.row for i in self._issues}\n"
     "        for r in range(self.rowCount()):\n"
     "            brush = QBrush(QColor(140, 30, 30)) if r in bad else QBrush()\n"
     "            for c in range(self.columnCount()):\n"
     "                it = self.item(r, c)\n"
     "                if it is not None:\n"
     "                    it.setBackground(brush)\n"
     "        self.setToolTip(\"\\n\".join(f\"row {i.row + 1}: {i.msg}\" for i in self._issues)\n"
     "                        if self._issues else \"\")\n"
     "\n"
     "    def _on_edit(self, r, c):"),
    # main_window: импорт валидатора
    ("minizemax/ui/main_window.py",
     "from minizemax.system.paraxial import paraxial_trace",
     "from minizemax.system.paraxial import paraxial_trace\nfrom minizemax.system.validation import check_prescription"),
    # main_window: проверка в refresh + статус
    ("minizemax/ui/main_window.py",
     "            self.statusBar().showMessage(\n"
     "                f\"EFL={pd.efl:.3f} mm  f/#={pd.fno:.3f}  BFL={pd.bfl:.3f} mm  \"\n"
     "                f\"image z={pd.img_z:.3f} mm\")\n"
     "            self.plots.update_plots(self.pres)",
     "            issues = check_prescription(self.pres)\n"
     "            self.lde.set_issues(issues)\n"
     "            base = (f\"EFL={pd.efl:.3f} mm  f/#={pd.fno:.3f}  BFL={pd.bfl:.3f} mm  \"\n"
     "                    f\"image z={pd.img_z:.3f} mm\")\n"
     "            if issues:\n"
     "                base = f\"GEOMETRY WARNING ({len(issues)}): {issues[0].msg} | \" + base\n"
     "            self.statusBar().showMessage(base)\n"
     "            self.plots.update_plots(self.pres)"),
]


def main():
    p = pathlib.Path("minizemax/system/validation.py")
    if not p.exists():
        p.write_text(VALIDATION, encoding="utf-8")
        print("created minizemax/system/validation.py")
    else:
        print("already  minizemax/system/validation.py")
    for rel, old, new in FIXES:
        p = pathlib.Path(rel)
        s = p.read_text(encoding="utf-8")
        if new in s:
            print(f"already  {rel}")
            continue
        if old not in s:
            print(f"NOT FOUND in {rel}")
            continue
        p.write_text(s.replace(old, new, 1), encoding="utf-8")
        print(f"patched  {rel}")


if __name__ == "__main__":
    main()