"""MainWindow: LDE в центре, System/Analysis/MFE в доках."""
from __future__ import annotations
import os
from minizemax.ui.qt import (QMainWindow, QDockWidget, QToolBar, QFileDialog, QMessageBox,
                             QAction, QLabel, DOCK_LEFT, DOCK_RIGHT, DOCK_BOTTOM)
from minizemax.system.prescription import Prescription
from minizemax.system.paraxial import paraxial_trace
from minizemax.system.validation import check_prescription
from minizemax.optim.merit import MeritFunction
from minizemax.ui.lde_widget import LDEWidget
from minizemax.ui.system_widget import SystemWidget
from minizemax.ui.mfe_widget import MFEWidget
from minizemax.ui.plot_widget import PlotTabs
from minizemax.ui.workers import OptimizeWorker


class MainWindow(QMainWindow):
    def __init__(self, pres: Prescription, path: str | None = None):
        super().__init__()
        self.pres = pres
        self.worker = None
        self.setWindowTitle("mini-Zemax — sequential optical design")
        self.resize(1500, 900)

        self.lde = LDEWidget(pres)
        self.setCentralWidget(self.lde)

        self.sysw = SystemWidget(pres)
        d = QDockWidget("System Data"); d.setWidget(self.sysw)
        self.addDockWidget(DOCK_LEFT, d)

        self.plots = PlotTabs()
        d = QDockWidget("Analysis"); d.setWidget(self.plots)
        self.addDockWidget(DOCK_RIGHT, d)

        self.mfe = MFEWidget(pres)
        d = QDockWidget("Merit Function / Optimization"); d.setWidget(self.mfe)
        self.addDockWidget(DOCK_BOTTOM, d)

        tb = QToolBar("main"); self.addToolBar(tb)
        self.lbl_cfg = QLabel("")
        self.current_path = None
        self._dirty = False
        act_open = QAction("Open", self); act_open.triggered.connect(self.open_file)
        act_save = QAction("Save", self); act_save.triggered.connect(self.save_file)
        act_trace = QAction("Trace", self); act_trace.triggered.connect(self.refresh)
        tb.addActions([act_open, act_save, act_trace])
        tb.addWidget(self.lbl_cfg)
        self.set_current_path(path)

        self.lde.modelChanged.connect(self.refresh)
        self.sysw.modelChanged.connect(self.refresh)
        self.lde.modelChanged.connect(self._mark_dirty)
        self.sysw.modelChanged.connect(self._mark_dirty)
        self.mfe.optimize_requested.connect(self.start_optimize)
        self.refresh()

    def set_current_path(self, path):
        self.current_path = path
        self._dirty = False
        self._update_title()

    def _mark_dirty(self):
        if not self._dirty:
            self._dirty = True
            self._update_title()

    def _update_title(self):
        name = os.path.basename(self.current_path) if self.current_path else "untitled"
        star = " *" if self._dirty else ""
        self.setWindowTitle(f"mini-Zemax — {name}{star}")
        self.lbl_cfg.setText(f"config: {name}{star}")

    def refresh(self):
        try:
            built = self.pres.build()
            pd = paraxial_trace(built, self.pres.sysdata.primary_wl,
                                max(f.y for f in self.pres.sysdata.fields) or 0.0)
            issues = check_prescription(self.pres)
            self.lde.set_issues(issues)
            if abs(pd.efl) > 1e6:
                base = ("AFOCAL (EFL=inf): parallel in -> parallel out; "
                        "M finite object = -f2/f1 (see examples/fourf_relay.py)")
            else:
                base = (f"EFL={pd.efl:.3f} mm  f/#={pd.fno:.3f}  BFL={pd.bfl:.3f} mm  "
                        f"image z={pd.img_z:.3f} mm")
            from minizemax.engine.tracer import trace_field
            from minizemax.analysis.losses import loss_counts
            wi0 = next((i for i, w in enumerate(self.pres.sysdata.wavelengths)
                        if w.primary), 0)
            lc = loss_counts(trace_field(built, 0, wi0))
            base += (f" | losses: blocked={lc['blocked(aperture)']} "
                     f"tir={lc['tir']} miss={lc['miss(no hit)']}")
            if issues:
                base = f"GEOMETRY WARNING ({len(issues)}): {issues[0].msg} | " + base
            self.statusBar().showMessage(base)
            self.plots.update_plots(self.pres)
        except Exception as e:  # noqa: BLE001
            self.statusBar().showMessage(f"trace error: {e}")

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open prescription", "", "YAML (*.yaml *.yml *.zmx-lite);;All (*)")
        if path:
            try:
                self.pres = Prescription.load(path)
            except Exception as e:  # noqa: BLE001
                QMessageBox.critical(self, "Open error", str(e)); return
            self.lde.set_pres(self.pres)
            self.sysw.set_pres(self.pres)
            self.mfe.default_mf()
            self.set_current_path(path)
            self.refresh()

    def save_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save prescription", "system.yaml",
                                              "YAML (*.yaml)")
        if path:
            self.pres.save(path)
            self.set_current_path(path)
            self.mfe.append_log(f"saved -> {path}")

    def start_optimize(self, iters):
        ops = self.mfe.operands()
        nf, nw = len(self.pres.sysdata.fields), len(self.pres.sysdata.wavelengths)
        bad = [op for op in ops if not (0 <= op.field < nf and 0 <= op.wl < nw)]
        if bad:
            QMessageBox.warning(self, "Bad operands",
                                f"Field/Wl out of range: {[(o.field, o.wl) for o in bad[:4]]} "
                                f"(fields 0..{nf-1}, wl 0..{nw-1}). Press Default MF.")
            return
        mf = MeritFunction(self.pres, ops)
        if not mf.vars:
            QMessageBox.warning(self, "No variables",
                                "Отметьте Var R / Var T в Lens Data Editor.")
            return
        self.mfe.set_busy(True)
        self.mfe.append_log(f"--- optimize: {len(ops)} operands, {len(mf.vars)} variables ---")
        self.worker = OptimizeWorker(self.pres, mf, iters, parent=self)
        self.worker.progress.connect(
            lambda i, m: self.mfe.set_progress(f"iter {i}: merit={m:.6g}"))
        self.worker.progress.connect(
            lambda i, m: self.mfe.append_log(f"  iter {i:3d}  merit={m:.6g}"))
        self.worker.done.connect(self.on_opt_done)
        self.worker.error.connect(self.on_opt_error)
        self.worker.start()

    def on_opt_done(self, res):
        self.mfe.set_busy(False)
        self.mfe.append_log(f"done: merit {res.merit0:.6g} -> {res.merit1:.6g} "
                            f"({res.niters} iters)  x={res.x.round(4).tolist()}")
        self.lde.reload()
        self.refresh()
        self.worker = None

    def on_opt_error(self, msg):
        self.mfe.set_busy(False)
        self.mfe.append_log(f"ERROR: {msg}")
        self.worker = None
