"""MFE: таблица operand'ов, панель оптимизации, лог."""
from __future__ import annotations
from minizemax.ui.qt import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QComboBox, QPushButton, QSpinBox, QLabel, QPlainTextEdit, Signal,
                             RESIZE_CONTENTS)
from minizemax.optim.merit import Operand

KINDS = ["RMS", "EFFL", "TOTR", "DIST"]


class MFEWidget(QWidget):
    optimize_requested = Signal(int)

    def __init__(self, pres):
        super().__init__()
        self.pres = pres
        lay = QVBoxLayout(self)
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Kind", "Field", "Wl", "Target", "Weight"])
        self.table.horizontalHeader().setSectionResizeMode(RESIZE_CONTENTS)
        lay.addWidget(self.table)

        row = QHBoxLayout()
        self.btn_default = QPushButton("Default MF")
        self.btn_add = QPushButton("+")
        self.btn_del = QPushButton("-")
        self.spin_iters = QSpinBox(); self.spin_iters.setRange(1, 500); self.spin_iters.setValue(30)
        self.btn_opt = QPushButton("Optimize")
        self.lbl_progress = QLabel("idle")
        row.addWidget(self.btn_default); row.addWidget(self.btn_add); row.addWidget(self.btn_del)
        row.addStretch(1)
        row.addWidget(QLabel("iters:")); row.addWidget(self.spin_iters)
        row.addWidget(self.btn_opt); row.addWidget(self.lbl_progress)
        lay.addLayout(row)

        self.log = QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMaximumHeight(110)
        lay.addWidget(self.log)

        self.btn_default.clicked.connect(self.default_mf)
        self.btn_add.clicked.connect(lambda: self._add_row())
        self.btn_del.clicked.connect(self._del_row)
        self.btn_opt.clicked.connect(lambda: self.optimize_requested.emit(self.spin_iters.value()))
        self.default_mf()

    def default_mf(self):
        sd = self.pres.sysdata
        self.table.setRowCount(0)
        for fi in range(len(sd.fields)):
            for wi in range(len(sd.wavelengths)):
                self._add_row(Operand("RMS", fi, wi,
                                      weight=sd.fields[fi].weight * sd.wavelengths[wi].weight))

    def _add_row(self, op=None):
        r = self.table.rowCount(); self.table.insertRow(r)
        combo = QComboBox(); combo.addItems(KINDS)
        if op:
            combo.setCurrentText(op.kind)
        self.table.setCellWidget(r, 0, combo)
        vals = ([str(op.field), str(op.wl), f"{op.target:.6g}", f"{op.weight:.4g}"]
                if op else ["0", "0", "0", "1"])
        for c, v in enumerate(vals, start=1):
            self.table.setItem(r, c, QTableWidgetItem(v))

    def _del_row(self):
        r = self.table.currentRow()
        if r >= 0:
            self.table.removeRow(r)

    def operands(self):
        ops = []
        for r in range(self.table.rowCount()):
            combo = self.table.cellWidget(r, 0)
            def g(c):
                return float(self.table.item(r, c).text() or 0) if self.table.item(r, c) else 0.0
            ops.append(Operand(combo.currentText(), int(g(1)), int(g(2)),
                               target=g(3), weight=g(4)))
        return ops

    def append_log(self, msg):
        self.log.appendPlainText(msg)

    def set_progress(self, msg):
        self.lbl_progress.setText(msg)

    def set_busy(self, busy):
        self.btn_opt.setEnabled(not busy)
        self.btn_default.setEnabled(not busy)
        self.table.setEnabled(not busy)
