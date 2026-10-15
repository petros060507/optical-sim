"""Lens Data Editor: таблица поверхностей <-> Prescription.lens + колонка Name."""
from __future__ import annotations
import numpy as np
from minizemax.ui.qt import (QTableWidget, QTableWidgetItem, Signal, CHECKED, UNCHECKED,
                             ITEM_ENABLED, ITEM_CHECKABLE, RESIZE_CONTENTS)
from minizemax.system.lens_data import auto_comments

COLS = ["Surf", "Name", "Radius", "Thickness", "Glass", "Semi-Dia", "Conic",
        "Stop", "Var R", "Var T"]


def _fmt(v):
    try:
        fv = float(v)
    except (TypeError, ValueError):
        return str(v)
    return "inf" if not np.isfinite(fv) else f"{fv:.6g}"


class LDEWidget(QTableWidget):
    modelChanged = Signal()

    def __init__(self, pres):
        super().__init__()
        self.pres = pres
        self._loading = False
        self._issues = []
        self.setColumnCount(len(COLS))
        self.setHorizontalHeaderLabels(COLS)
        self.horizontalHeader().setSectionResizeMode(RESIZE_CONTENTS)
        self.reload()
        self.cellChanged.connect(self._on_edit)

    def set_pres(self, pres):
        self.pres = pres
        self.reload()

    def _chk(self, on):
        it = QTableWidgetItem()
        it.setFlags(ITEM_ENABLED | ITEM_CHECKABLE)
        it.setCheckState(CHECKED if on else UNCHECKED)
        return it

    def reload(self):
        self._loading = True
        rows = self.pres.lens.rows
        auto = auto_comments(self.pres.lens.real_rows())
        ri = 0
        self.setRowCount(len(rows))
        for r, row in enumerate(rows):
            is_real = row.surf not in ("OBJ", "IMA")
            if is_real:
                name = row.comment or auto[ri]
                ri += 1
            else:
                name = row.comment or ("object" if row.surf == "OBJ" else "image/detector")
            self.setItem(r, 0, QTableWidgetItem(str(row.surf)))
            self.setItem(r, 1, QTableWidgetItem(name))
            self.setItem(r, 2, QTableWidgetItem(_fmt(row.radius)))
            self.setItem(r, 3, QTableWidgetItem(f"{row.thickness:.6g}"))
            self.setItem(r, 4, QTableWidgetItem(row.glass or ""))
            self.setItem(r, 5, QTableWidgetItem(f"{row.semi_dia:.6g}"))
            self.setItem(r, 6, QTableWidgetItem(f"{row.conic:.6g}"))
            self.setItem(r, 7, self._chk(row.stop))
            self.setItem(r, 8, self._chk("radius" in row.variables))
            self.setItem(r, 9, self._chk("thickness" in row.variables))
        self._loading = False
        self._apply_issues()

    def set_issues(self, issues):
        self._issues = list(issues)
        self._apply_issues()

    def _apply_issues(self):
        from minizemax.ui.qt import QBrush, QColor
        bad = {i.row for i in self._issues}
        for r in range(self.rowCount()):
            brush = QBrush(QColor(140, 30, 30)) if r in bad else QBrush()
            for c in range(self.columnCount()):
                it = self.item(r, c)
                if it is not None:
                    it.setBackground(brush)
        self.setToolTip("\n".join(f"row {i.row + 1}: {i.msg}" for i in self._issues)
                        if self._issues else "")

    def _on_edit(self, r, c):
        if self._loading:
            return
        row = self.pres.lens.rows[r]
        txt = (self.item(r, c).text() if self.item(r, c) else "").strip()
        try:
            if c == 0:
                row.surf = txt
            elif c == 1:
                row.comment = txt
                if not txt:
                    self.reload()      # очистили -> вернуть авто-имя
                return
            elif c == 2:
                row.radius = np.inf if txt in ("inf", "") else float(txt)
            elif c == 3:
                row.thickness = float(txt)
            elif c == 4:
                row.glass = txt or None
            elif c == 5:
                row.semi_dia = float(txt)
            elif c == 6:
                row.conic = float(txt)
            elif c == 7:
                row.stop = self.item(r, c).checkState() == CHECKED
            elif c in (8, 9):
                param = "radius" if c == 8 else "thickness"
                on = self.item(r, c).checkState() == CHECKED
                if on and param not in row.variables:
                    row.variables.append(param)
                if not on and param in row.variables:
                    row.variables.remove(param)
            else:
                return
        except ValueError:
            return
        self.modelChanged.emit()
