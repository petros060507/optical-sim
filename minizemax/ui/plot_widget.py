"""Вкладки анализа: Layout / Spot / Ray Fan / MTF / 3D (GPU OpenGL, fallback matplotlib)."""
from __future__ import annotations
import numpy as np
from minizemax.ui.qt import QTabWidget, QVBoxLayout, QWidget
try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
except ImportError:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

from minizemax.engine.tracer import trace_field
from minizemax.system.paraxial import paraxial_trace
from minizemax.analysis.spot import image_points, ray_fan
from minizemax.analysis.mtf import mtf_geometric
from minizemax.analysis.layout import layout as draw_layout
from minizemax.analysis.layout3d import layout_3d as draw_layout3d
from minizemax.analysis.scene3d import build_scene


class _Tab(QWidget):
    def __init__(self, projection=None):
        super().__init__()
        self.fig = Figure(figsize=(6, 4.5), dpi=100)
        self.ax = self.fig.add_subplot(111, projection=projection)
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        lay = QVBoxLayout(self); lay.setContentsMargins(2, 2, 2, 2)
        lay.addWidget(self.toolbar)
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
        self._gl = None
        self.tab_3d = None
        try:
            from minizemax.ui.view3d_qt import GLView3D, gl_available
            if gl_available():
                self._gl = GLView3D()
                self.addTab(self._gl, "3D (GPU)")
        except Exception:
            self._gl = None
        if self._gl is None:
            self.tab_3d = _Tab(projection="3d")
            self.addTab(self.tab_3d, "3D")

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

        if self._gl is not None:
            try:
                self._gl.set_scene(build_scene(built, 0, 0, n_rays=24))
            except Exception:  # noqa: BLE001
                import traceback
                traceback.print_exc()
        elif self.tab_3d is not None:
            t = self.tab_3d; t.begin()
            try:
                draw_layout3d(built, 0, 0, n_rays=12, ax=t.ax)
            except Exception as e:  # noqa: BLE001
                t.ax.text2D(0.5, 0.5, f"3D failed: {e}", transform=t.ax.transAxes)
            t.end()

        t = self.tab_spot
        t.fig.clear()
        clouds = {}
        for fi in range(len(sd.fields)):
            for wi in range(len(sd.wavelengths)):
                res = trace_field(built, fi, wi, cache)
                pd = paraxial_trace(built, sd.wavelengths[wi].um, sd.fields[fi].y)
                pts, _ = image_points(res, pd.img_z)
                if len(pts):
                    clouds.setdefault(fi, []).append((pts, wi, pd.img_h))
        if not clouds:
            ax0 = t.fig.add_subplot(111)
            ax0.text(0.5, 0.5, "no rays reached image", ha="center", transform=ax0.transAxes)
        for k, (fi, lst) in enumerate(sorted(clouds.items())):
            ax = t.fig.add_subplot(1, len(clouds), k + 1)
            P = np.concatenate([p for p, _, _ in lst], 0) * 1e3
            c = np.median(P, axis=0)
            d = np.hypot(*(P - c).T)
            half = max(3.0 * float(np.percentile(d, 95)), 1.0)
            for pts, wi, _h in lst:
                ax.plot(pts[:, 0] * 1e3, pts[:, 1] * 1e3, ".", ms=1.5,
                        color=f"C{wi}", label=f"λ{wi}" if k == 0 else None)
            ax.set_xlim(c[0] - half, c[0] + half)
            ax.set_ylim(c[1] - half, c[1] + half)
            ax.set_aspect("equal")
            ax.set_title(f"field {sd.fields[fi].y:.1f} deg  h={lst[0][2]:.2f} mm", fontsize=8)
            ax.set_xlabel("x, um", fontsize=8)
            ax.set_ylabel("y, um", fontsize=8)
            ax.tick_params(labelsize=7)
            if k == 0:
                ax.legend(fontsize=7, loc="upper right", framealpha=0.9)
        t.end()

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
