"""Component Properties dialog (v2): groups Component / Position and aperture /
Refractive element with Apply changes / Cancel.

Semantics of Axial position (matches build_system in system/lens_data.py):
  * built coordinate system: first real surface is z = 0;
  * z(row) = sum of thicknesses of REAL rows above it; IMA z = detector_z;
  * editing z adjusts the previous row's 'thickness' (the gap above);
  * OBJ shows -object_distance (read-only); infinite gap -> special text,
    never clamped to a fake numeric value.
Before commit the whole system is validated (build + check_prescription)
on a deepcopy - invalid changes are NOT committed."""
from __future__ import annotations

import copy

import numpy as np

from minizemax.ui.qt import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
                             QLabel, QLineEdit, QComboBox, QDoubleSpinBox, QCheckBox,
                             QPushButton, QMessageBox)
from minizemax.core.materials import CATALOG
from minizemax.system.validation import check_prescription
from minizemax.ui.object_actions import _btn

BIG = 1e9


class SurfacePropertiesDialog(QDialog):
    def __init__(self, pres, idx: int, parent=None):
        super().__init__(parent)
        self.pres = pres
        self.idx = idx
        self._sync = False
        row = pres.lens.rows[idx]
        self._is_real = row.surf not in ("OBJ", "IMA")
        self._z0 = self._z_of(idx)          # float | None (None = infinite gap)

        self.setWindowTitle(f"Component Properties \u2014 {self._title(row)}")
        self.setModal(True)
        self.setMinimumWidth(440)

        outer = QVBoxLayout(self)
        outer.addWidget(QLabel("Edit parameters, then click Apply. The entire optical "
                               "system is checked before any change is committed."))

        # ---- Component ---------------------------------------------------
        g = QGroupBox("Component")
        f = QFormLayout(g)
        self.ed_id = QLineEdit(row.comment or self._title(row))
        f.addRow("Component ID", self.ed_id)
        f.addRow("Type", QLabel(self._type_text(row)))
        outer.addWidget(g)

        # ---- Position and aperture ----------------------------------------
        g = QGroupBox("Position and aperture")
        f = QFormLayout(g)
        self.sp_z = self._spin(-BIG, BIG, 4, 0.0)
        if idx == 0:
            if self._z0 is None:
                self.sp_z.setSpecialValueText("-inf (object at infinity)")
                self.sp_z.setValue(-BIG)
            else:
                self.sp_z.setValue(self._z0)
            self.sp_z.setEnabled(False)
            self.sp_z.setToolTip("Object plane. Object distance lives in the OBJ row "
                                 "'Thickness' of the Lens Data Editor.")
        elif idx == 1:
            self.sp_z.setValue(0.0)
            self.sp_z.setEnabled(False)
            self.sp_z.setToolTip("First real surface = coordinate origin (z = 0).")
        elif self._z0 is None:
            self.sp_z.setSpecialValueText("n/a (infinite gap above)")
            self.sp_z.setValue(-BIG)
            self.sp_z.setEnabled(False)
        else:
            self.sp_z.setValue(self._z0)
            self.sp_z.setToolTip("Absolute z in the built system. Changing it edits the "
                                 "previous surface's 'Thickness to next'.")
        f.addRow("Axial position (mm)", self.sp_z)

        self.sp_clear = self._spin(0.01, 1e5, 4, row.semi_dia)
        f.addRow("Clear radius (mm)", self.sp_clear)
        self.sp_mech = self._spin(0.02, 2e5, 4, 2.0 * row.semi_dia)
        f.addRow("Mechanical diameter (mm)", self.sp_mech)
        self.sp_tilt = self._spin(-90.0, 90.0, 3, 0.0)
        self.sp_tilt.setEnabled(False)
        self.sp_tilt.setToolTip("Tilts/decenters are not supported by the sequential model yet")
        f.addRow("Y-axis tilt (degrees)", self.sp_tilt)
        self.sp_clear.valueChanged.connect(lambda v: self._mirror(self.sp_mech, 2.0 * v))
        self.sp_mech.valueChanged.connect(lambda v: self._mirror(self.sp_clear, v / 2.0))
        self.sp_clear.setEnabled(self._is_real)
        self.sp_mech.setEnabled(self._is_real)
        outer.addWidget(g)

        # ---- Refractive element --------------------------------------------
        g = QGroupBox("Refractive element")
        f = QFormLayout(g)
        plane = not np.isfinite(row.radius)
        self.sp_r = self._spin(-BIG, BIG, 6, row.radius if np.isfinite(row.radius) else 0.0)
        f.addRow("Radius R (mm); 0=plane", self.sp_r)
        self.chk_plane = QCheckBox("plane (R = inf)")
        self.chk_plane.setChecked(plane)
        self.chk_plane.toggled.connect(self._on_plane)
        self.sp_r.setEnabled(not plane)
        f.addRow("", self.chk_plane)
        self.sp_conic = self._spin(-BIG, BIG, 6, row.conic)
        f.addRow("Conic", self.sp_conic)
        self.sp_t = self._spin(-BIG, BIG, 6, row.thickness)
        self.sp_t.setEnabled(self._is_real)
        f.addRow("Thickness to next (mm)", self.sp_t)
        self.cb_glass = QComboBox()
        self.cb_glass.setEditable(True)
        self.cb_glass.addItems(list(CATALOG))
        self.cb_glass.setCurrentText(row.glass or "")
        f.addRow("Glass", self.cb_glass)
        self.chk_mirror = QCheckBox("reflective (mirror)")
        self.chk_mirror.setChecked(bool(row.reflective))
        f.addRow("", self.chk_mirror)
        self.chk_stop = QCheckBox("aperture stop")
        self.chk_stop.setChecked(bool(row.stop))
        f.addRow("", self.chk_stop)
        self.chk_vr = QCheckBox("variable (Var R)")
        self.chk_vr.setChecked("radius" in row.variables)
        f.addRow("", self.chk_vr)
        self.chk_vt = QCheckBox("variable (Var T)")
        self.chk_vt.setChecked("thickness" in row.variables)
        f.addRow("", self.chk_vt)
        g.setEnabled(self._is_real)
        outer.addWidget(g)

        # ---- buttons ---------------------------------------------------------
        bb = QHBoxLayout()
        bb.addStretch(1)
        b_ok = QPushButton("Apply changes")
        b_ok.setDefault(True)
        b_ok.clicked.connect(self._apply)
        b_no = QPushButton("Cancel")
        b_no.clicked.connect(self.reject)
        bb.addWidget(b_ok)
        bb.addWidget(b_no)
        outer.addLayout(bb)

    # -- helpers ---------------------------------------------------------------
    @staticmethod
    def _spin(lo, hi, dec, val):
        s = QDoubleSpinBox()
        s.setRange(lo, hi)
        s.setDecimals(dec)
        s.setValue(float(val))
        return s

    def _on_plane(self, on):
        self.sp_r.setEnabled(not on)
        if on:
            self.sp_r.setValue(0.0)

    def _mirror(self, target, value):
        if self._sync:
            return
        self._sync = True
        target.setValue(value)
        self._sync = False

    def _title(self, row):
        return row.comment or f"Surface {row.surf}"

    @staticmethod
    def _type_text(row):
        if row.surf == "OBJ":
            t = "Object plane"
        elif row.surf == "IMA":
            t = "Image / detector"
        elif row.reflective:
            t = "Mirror"
        else:
            t = "Lens surface"
        return t + (" (STOP)" if row.stop else "")

    def _z_of(self, idx):
        """Built-system z: first real surface = 0, IMA = detector_z.
        None if any gap above is infinite (e.g. object at infinity)."""
        rows = self.pres.lens.rows
        if idx == 0:
            t = rows[0].thickness
            return -float(t) if np.isfinite(t) else None
        z = 0.0
        for r in rows[1:idx]:
            if not np.isfinite(r.thickness):
                return None
            z += float(r.thickness)
        return z

    # -- commit with validation ---------------------------------------------------
    def _write_to(self, pres, idx):
        rows = pres.lens.rows
        row = rows[idx]
        row.comment = self.ed_id.text().strip()
        if idx >= 2 and self._z0 is not None and self.sp_z.isEnabled():
            rows[idx - 1].thickness += self.sp_z.value() - self._z0
        if self._is_real:
            row.semi_dia = self.sp_clear.value()
            plane = self.chk_plane.isChecked() or self.sp_r.value() == 0.0
            row.radius = np.inf if plane else self.sp_r.value()
            row.conic = self.sp_conic.value()
            row.thickness = self.sp_t.value()
            row.glass = self.cb_glass.currentText().strip() or None
            row.reflective = self.chk_mirror.isChecked()
            want_stop = self.chk_stop.isChecked()
            if want_stop:
                for r in rows:
                    r.stop = False
            row.stop = want_stop
            row.variables = ([v for v in row.variables if v not in ("radius", "thickness")]
                             + (["radius"] if self.chk_vr.isChecked() else [])
                             + (["thickness"] if self.chk_vt.isChecked() else []))
        return pres

    def _apply(self):
        trial = self._write_to(copy.deepcopy(self.pres), self.idx)
        try:
            trial.build()
            issues = check_prescription(trial)
        except Exception as ex:  # noqa: BLE001
            QMessageBox.critical(self, "Validation failed", f"Change NOT committed:\n{ex}")
            return
        if any(getattr(i, "hard", False) for i in issues):
            txt = "\n".join(f"  row {i.row + 1}: {i.msg}" for i in issues)
            QMessageBox.critical(self, "Invalid geometry",
                                 f"Change NOT committed:\n{txt}")
            return
        if issues:
            txt = "\n".join(f"  row {i.row + 1}: {i.msg}" for i in issues)
            ans = QMessageBox.question(self, "Validation warnings",
                                       f"check_prescription reported:\n{txt}\n\nCommit anyway?",
                                       _btn("Yes") | _btn("No"), _btn("No"))
            if ans != _btn("Yes"):
                return
        self._write_to(self.pres, self.idx)
        self.accept()
