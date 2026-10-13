"""OptimizeWorker: DLS в QThread, прогресс -> сигналы."""
from __future__ import annotations
from minizemax.ui.qt import QThread, Signal
from minizemax.optim.dls import DLSOptimizer


class OptimizeWorker(QThread):
    progress = Signal(int, float)
    done = Signal(object)
    error = Signal(str)

    def __init__(self, pres, mf, iters, parent=None):
        super().__init__(parent)
        self.pres, self.mf, self.iters = pres, mf, iters

    def run(self):
        try:
            opt = DLSOptimizer(self.pres, self.mf)
            res = opt.run(max_iters=self.iters,
                          callback=lambda i, m: self.progress.emit(i, m))
            self.done.emit(res)
        except Exception as e:  # noqa: BLE001
            self.error.emit(f"{type(e).__name__}: {e}")
