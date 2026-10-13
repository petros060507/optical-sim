"""Вкладки анализа: Layout / Spot / Ray Fan / MTF (matplotlib в Qt)."""
from __future__ import annotations
import numpy as np
from minizemax.ui.qt import QTabWidget, QVBoxLayout, QWidget
try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
except ImportError:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from minizemax.engine.tracer import trace_field
from minizemax.system.paraxial import paraxial_trace
from minizemax.analysis.spot import image_points, ray_fan
from minizemax.analysis.mtf import mtf_geometric
from minizemax.analysis.layout import layout as draw_layout


class _Tab(QWidget):
    def __init__(self):
        super().__init__()
        self.fig = Figure(figsize=(6, 4.5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasQTAgg(self.fig)
        lay = QVBoxLayout(self); lay.setContentsMargins(2, 2, 2, 2)
        lay.addWidget(self.canvas)

    def begin(self):
        self.ax.clear()

    def end(self):
        self.fig.tight_layout(); self.canvas.draw()


class PlotTabs(QTabWidget):
    def __init__(self):
        super().__init__()
        self.tab_layout, self.tab_spot = _Tab(), _Tab()
        self.tab_fan, self.tab_mtf = _Tab(), _Tab()
        self.addTab(self.tab_layout, "Layout")
        self.addTab(self.tab_spot, "Spot")
        self.addTab(self.tab_fan, "Ray Fan")
        self.addTab(self.tab_mtf, "MTF (geo)")

    def update_plots(self, pres):
        built = pres.build()
        sd = pres.sysdata
        cache = {}
        t = self.tab_layout; t.begin()
        try:
            draw_layout(built, 0, 0, ax=t.ax)
        except Exception as e:  # noqa: BLE001
            t.ax.text(0.5, 0.5, f"layout failed: {e}", ha="center")
        t.end()

        t = self.tab_spot; t.begin()
        for fi in range(len(sd.fields)):
            for wi in range(len(sd.wavelengths)):
                res = trace_field(built, fi, wi, cache)
                pd = paraxial_trace(built, sd.wavelengths[wi].um, sd.fields[fi].y)
                pts, _ = image_points(res, pd.img_z)
                if len(pts):
                    t.ax.plot(pts[:, 0] * 1e3, pts[:, 1] * 1e3, ".", ms=1.5,
                              color=f"C{wi}", label=f"λ{wi}" if fi == 0 else None)
        t.ax.set_xlabel("x, um"); t.ax.set_ylabel("y, um")
        t.ax.set_aspect("equal"); t.ax.set_title("Spot diagram")
        t.ax.legend(fontsize=7); t.end()

        t = self.tab_fan; t.begin()
        fi = int(np.argmax([f.y for f in sd.fields]))
        s, ex, ey = ray_fan(built, fi, 0, n=31, axis="y")
        t.ax.plot(s, ey * 1e3, "C1-", lw=1.5, label="tangential")
        t.ax.plot(s, ex * 1e3, "C0--", lw=1.0, label="sagittal")
        t.ax.set_xlabel("Py"); t.ax.set_ylabel("um")
        t.ax.set_title(f"Ray fan, field {fi}")
        t.ax.legend(fontsize=8); t.ax.grid(alpha=0.3); t.end()

        t = self.tab_mtf; t.begin()
        pd0 = paraxial_trace(built, sd.primary_wl, 0.0)
        cutoff = 1000.0 / (sd.primary_wl * pd0.fno)
        freqs = np.linspace(0, cutoff, 60)
        for fi in range(len(sd.fields)):
            res = trace_field(built, fi, 0, cache)
            pd = paraxial_trace(built, sd.primary_wl, sd.fields[fi].y)
            pts, w = image_points(res, pd.img_z)
            if len(pts):
                t.ax.plot(freqs, mtf_geometric(pts, w, freqs, "y"), lw=1.2,
                          label=f"field {fi}")
        t.ax.set_xlabel("cycles/mm"); t.ax.set_ylabel("MTF")
        t.ax.set_title("Geometric MTF (tangential)")
        t.ax.legend(fontsize=8); t.ax.grid(alpha=0.3); t.end()
