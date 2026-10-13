"""System Data: апертура, λ, поля, sampling <-> Prescription.sysdata."""
from __future__ import annotations
from minizemax.ui.qt import (QWidget, QVBoxLayout, QGroupBox, QFormLayout, QComboBox,
                             QDoubleSpinBox, QSpinBox, QTableWidget, QTableWidgetItem,
                             Signal, CHECKED, UNCHECKED, ITEM_ENABLED, ITEM_CHECKABLE,
                             RESIZE_CONTENTS)


def _safe_float(item, default=0.0):
    try:
        return float(item.text())
    except (ValueError, AttributeError):
        return default


class SystemWidget(QWidget):
    modelChanged = Signal()

    def __init__(self, pres):
        super().__init__()
        self.pres = pres
        self._loading = False
        lay = QVBoxLayout(self)

        g = QGroupBox("Aperture"); f = QFormLayout(g)
        self.ap_type = QComboBox(); self.ap_type.addItems(["EPD", "FNO"])
        self.ap_val = QDoubleSpinBox(); self.ap_val.setRange(0.01, 1000.0)
        self.ap_val.setDecimals(3)
        f.addRow("type", self.ap_type); f.addRow("value", self.ap_val)
        lay.addWidget(g)

        g = QGroupBox("Wavelengths (um)"); vb = QVBoxLayout(g)
        self.wl_table = QTableWidget(); self.wl_table.setColumnCount(3)
        self.wl_table.setHorizontalHeaderLabels(["um", "weight", "primary"])
        self.wl_table.horizontalHeader().setSectionResizeMode(RESIZE_CONTENTS)
        vb.addWidget(self.wl_table); lay.addWidget(g)

        g = QGroupBox("Fields (deg)"); fb = QVBoxLayout(g)
        self.fl_table = QTableWidget(); self.fl_table.setColumnCount(2)
        self.fl_table.setHorizontalHeaderLabels(["y", "weight"])
        self.fl_table.horizontalHeader().setSectionResizeMode(RESIZE_CONTENTS)
        fb.addWidget(self.fl_table); lay.addWidget(g)

        g = QGroupBox("Sampling"); f = QFormLayout(g)
        self.samp_kind = QComboBox(); self.samp_kind.addItems(["hexapolar", "rect"])
        self.samp_rings = QSpinBox(); self.samp_rings.setRange(1, 12)
        f.addRow("grid", self.samp_kind); f.addRow("rings", self.samp_rings)
        lay.addWidget(g)
        lay.addStretch(1)

        self.ap_type.currentTextChanged.connect(self._push)
        self.ap_val.valueChanged.connect(self._push)
        self.samp_kind.currentTextChanged.connect(self._push)
        self.samp_rings.valueChanged.connect(self._push)
        self.wl_table.cellChanged.connect(self._push_wl)
        self.fl_table.cellChanged.connect(self._push_fl)
        self.set_pres(pres)

    def set_pres(self, pres):
        self.pres = pres
        self.reload()

    def _chk(self, on):
        it = QTableWidgetItem(); it.setFlags(ITEM_ENABLED | ITEM_CHECKABLE)
        it.setCheckState(CHECKED if on else UNCHECKED)
        return it

    def reload(self):
        self._loading = True
        sd = self.pres.sysdata
        self.ap_type.setCurrentText(sd.aperture.type)
        self.ap_val.setValue(sd.aperture.value)
        self.samp_kind.setCurrentText(sd.sampling.kind)
        self.samp_rings.setValue(sd.sampling.rings)
        self.wl_table.setRowCount(len(sd.wavelengths))
        for r, w in enumerate(sd.wavelengths):
            self.wl_table.setItem(r, 0, QTableWidgetItem(f"{w.um:.4f}"))
            self.wl_table.setItem(r, 1, QTableWidgetItem(f"{w.weight:.3f}"))
            self.wl_table.setItem(r, 2, self._chk(w.primary))
        self.fl_table.setRowCount(len(sd.fields))
        for r, fl in enumerate(sd.fields):
            self.fl_table.setItem(r, 0, QTableWidgetItem(f"{fl.y:.4f}"))
            self.fl_table.setItem(r, 1, QTableWidgetItem(f"{fl.weight:.3f}"))
        self._loading = False

    def _push(self, *_):
        if self._loading:
            return
        sd = self.pres.sysdata
        sd.aperture.type = self.ap_type.currentText()
        sd.aperture.value = self.ap_val.value()
        sd.sampling.kind = self.samp_kind.currentText()
        sd.sampling.rings = self.samp_rings.value()
        self.modelChanged.emit()

    def _push_wl(self, r, c):
        if self._loading:
            return
        w = self.pres.sysdata.wavelengths[r]
        if c == 0:
            w.um = _safe_float(self.wl_table.item(r, 0), w.um)
        elif c == 1:
            w.weight = _safe_float(self.wl_table.item(r, 1), w.weight)
        elif c == 2:
            on = self.wl_table.item(r, 2).checkState() == CHECKED
            for i, ww in enumerate(self.pres.sysdata.wavelengths):
                ww.primary = (i == r) if on else (ww.primary and i != r)
        self.modelChanged.emit()

    def _push_fl(self, r, c):
        if self._loading:
            return
        fl = self.pres.sysdata.fields[r]
        if c == 0:
            fl.y = _safe_float(self.fl_table.item(r, 0), fl.y)
        elif c == 1:
            fl.weight = _safe_float(self.fl_table.item(r, 1), fl.weight)
        self.modelChanged.emit()
