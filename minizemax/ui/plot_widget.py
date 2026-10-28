"""Analysis tabs: interactive 2D layout (QGraphicsView) + Spot / Ray Fan / MTF.
Charts use pyqtgraph when available (modern, dark, fast); otherwise a
theme-styled matplotlib fallback. 3D (GPU) tab kept as before.
Every tab update is isolated: one failing chart cannot blank the others."""
from __future__ import annotations

import traceback

import numpy as np

from minizemax.ui.qt import QTabWidget, QVBoxLayout, QWidget, Signal, QColor
from minizemax.ui import theme as T
from minizemax.ui.layout2d_view import Layout2DView

try:
    import pyqtgraph as pg
    T.pg_dark(pg)
    HAVE_PG = True
except Exception:  # pragma: no cover
    pg = None
    HAVE_PG = False

from minizemax.engine.tracer import trace_field
from minizemax.system.paraxial import paraxial_trace
from minizemax.analysis.spot import image_points, ray_fan
from minizemax.analysis.mtf import mtf_geometric
from minizemax.analysis.scene3d import build_scene


def _safe(fn, *args):
    try:
        fn(*args)
    except Exception:  # noqa: BLE001
        traceback.print_exc()


# --------------------------------------------------------------------------- pg tabs
if HAVE_PG:
    def _col(spec, alpha=255):
        c = QColor(spec)
        c.setAlpha(int(alpha))
        return c

    def _style(p, xl, yl):
        if hasattr(p, "setBackground"):        # PlotWidget / GraphicsLayoutWidget
            p.setBackground(T.BG)
        else:                                    # PlotItem -> красим его ViewBox
            try:
                p.getViewBox().setBackgroundColor(_col(T.PANEL, 255))
            except Exception:
                pass
        try:
            p.showGrid(x=True, y=True, alpha=0.18)
        except Exception:
            p.showGrid(x=True, y=True)
        p.setLabel("bottom", xl)
        p.setLabel("left", yl)
        for ax in ("bottom", "left"):
            try:
                p.getAxis(ax).setPen(pg.mkPen(_col(T.AXIS)))
                p.getAxis(ax).setTextPen(pg.mkPen(_col(T.TEXT)))
            except Exception:
                pass

    def _legend(p):
        try:
            p.addLegend(labelTextColor=_col(T.TEXT))
        except Exception:
            try:
                p.addLegend()
            except Exception:
                pass

    def _glow(p, x, y, color, **kw):
        p.plot(x, y, pen=pg.mkPen(_col(color, 45), width=5), **kw)
        p.plot(x, y, pen=pg.mkPen(_col(color, 255), width=1.8), **kw)

    class _SpotTab(QWidget):
        def __init__(self):
            super().__init__()
            lay = QVBoxLayout(self)
            lay.setContentsMargins(2, 2, 2, 2)
            self.gl = pg.GraphicsLayoutWidget()
            self.gl.setBackground(T.BG)
            lay.addWidget(self.gl)

        def update(self, clouds):
            self.gl.clear()
            for k, (title, lst) in enumerate(clouds):
                p = self.gl.addPlot(row=0, col=k, title=title)
                _style(p, "x, um", "y, um")
                p.setAspectLocked(True)
                for pts, wi in lst:
                    if len(pts) == 0:
                        continue
                    c = T.FIELDS[wi % len(T.FIELDS)]
                    p.addItem(pg.ScatterPlotItem(
                        x=pts[:, 0], y=pts[:, 1], size=3,
                        pen=pg.mkPen(_col(c, 200), width=1),
                        brush=pg.mkBrush(_col(c, 40))))

    class _FanTab(QWidget):
        def __init__(self):
            super().__init__()
            lay = QVBoxLayout(self)
            lay.setContentsMargins(2, 2, 2, 2)
            self.pw = pg.PlotWidget()
            _style(self.pw, "Py", "um")
            lay.addWidget(self.pw)

        def update(self, fan):
            self.pw.clear()
            if fan is None:
                return
            s, ey, ex = fan
            _glow(self.pw, s, ey, T.FIELDS[0], name="tangential")
            _glow(self.pw, s, ex, T.FIELDS[1], name="sagittal")
            _legend(self.pw)

    class _MTFTab(QWidget):
        def __init__(self):
            super().__init__()
            lay = QVBoxLayout(self)
            lay.setContentsMargins(2, 2, 2, 2)
            self.pw = pg.PlotWidget()
            _style(self.pw, "cycles/mm", "MTF")
            lay.addWidget(self.pw)

        def update(self, curves):
            self.pw.clear()
            for freqs, m, fi in curves:
                _glow(self.pw, freqs, m, T.FIELDS[fi % len(T.FIELDS)],
                      name=f"field {fi}")
            if curves:
                _legend(self.pw)
else:  # ---------------------------------------------------------------- mpl fallback
    try:
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
    except ImportError:
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
    from matplotlib.figure import Figure
    T.mpl_dark_style()

    class _MplTab(QWidget):
        def __init__(self):
            super().__init__()
            self.fig = Figure(figsize=(6, 4.5), dpi=100)
            self.canvas = FigureCanvasQTAgg(self.fig)
            lay = QVBoxLayout(self)
            lay.setContentsMargins(2, 2, 2, 2)
            lay.addWidget(self.canvas)

        def begin(self):
            self.fig.clear()

        def end(self):
            self.fig.tight_layout()
            self.canvas.draw()

    class _SpotTab(_MplTab):
        def update(self, clouds):
            self.begin()
            for k, (title, lst) in enumerate(clouds):
                ax = self.fig.add_subplot(1, max(len(clouds), 1), k + 1)
                for pts, wi in lst:
                    ax.plot(pts[:, 0], pts[:, 1], ".", ms=1.6,
                            color=T.FIELDS[wi % len(T.FIELDS)])
                ax.set_title(title)
                ax.set_xlabel("x, um")
                ax.set_ylabel("y, um")
                ax.set_aspect("equal")
            self.end()

    class _FanTab(_MplTab):
        def update(self, fan):
            self.begin()
            if fan is not None:
                s, ey, ex = fan
                ax = self.fig.add_subplot(111)
                ax.plot(s, ey, color=T.FIELDS[0], lw=1.5, label="tangential")
                ax.plot(s, ex, color=T.FIELDS[1], lw=1.0, ls="--", label="sagittal")
                ax.set_xlabel("Py")
                ax.set_ylabel("um")
                ax.legend()
            self.end()

    class _MTFTab(_MplTab):
        def update(self, curves):
            self.begin()
            ax = self.fig.add_subplot(111)
            for freqs, m, fi in curves:
                ax.plot(freqs, m, color=T.FIELDS[fi % len(T.FIELDS)],
                        lw=1.4, label=f"field {fi}")
            ax.set_xlabel("cycles/mm")
            ax.set_ylabel("MTF")
            ax.legend()
            self.end()


# --------------------------------------------------------------------------- tabs
class PlotTabs(QTabWidget):
    surfaceMenuRequested = Signal(int, object)
    editRequested = Signal(int)
    structureChanged = Signal()
    hintMessage = Signal(str)

    def __init__(self):
        super().__init__()
        self.layout2d = Layout2DView()
        self.layout2d.objectMenuRequested.connect(self.surfaceMenuRequested.emit)
        self.layout2d.editRequested.connect(self.editRequested.emit)
        self.layout2d.structureChanged.connect(self.structureChanged.emit)
        self.layout2d.hintMessage.connect(self.hintMessage.emit)
        self.addTab(self.layout2d, "2D Layout")
        self.tab_spot = _SpotTab()
        self.tab_fan = _FanTab()
        self.tab_mtf = _MTFTab()
        self.addTab(self.tab_spot, "Spot")
        self.addTab(self.tab_fan, "Ray Fan")
        self.addTab(self.tab_mtf, "MTF (geo)")
        self._gl = None
        try:
            from minizemax.ui.view3d_qt import GLView3D, gl_available
            if gl_available():
                self._gl = GLView3D()
                self._gl.objectMenuRequested.connect(self.surfaceMenuRequested.emit)
                self.addTab(self._gl, "3D (GPU)")
        except Exception:
            self._gl = None

    def update_plots(self, pres):
        built = pres.build()
        sd = pres.sysdata
        _safe(self.layout2d.set_system, pres)
        if self._gl is not None:
            _safe(self._gl.set_scene, build_scene(built, 0, 0, n_rays=24))

        cache = {}
        clouds = []
        for fi in range(len(sd.fields)):
            lst = []
            for wi in range(len(sd.wavelengths)):
                res = trace_field(built, fi, wi, cache)
                pd = paraxial_trace(built, sd.wavelengths[wi].um, sd.fields[fi].y)
                pts, _ = image_points(res, pd.img_z)
                if len(pts):
                    lst.append((pts * 1e3, wi))
            if lst:
                clouds.append((f"field {sd.fields[fi].y:.1f} deg", lst))
        _safe(self.tab_spot.update, clouds)

        fan = None
        try:
            fi = int(np.argmax([f.y for f in sd.fields]))
            s, ex, ey = ray_fan(built, fi, 0, n=31, axis="y")
            fan = (s, ey * 1e3, ex * 1e3)
        except Exception:
            traceback.print_exc()
        _safe(self.tab_fan.update, fan)

        curves = []
        try:
            pd0 = paraxial_trace(built, sd.primary_wl, 0.0)
            cutoff = 1000.0 / (sd.primary_wl * pd0.fno)
            freqs = np.linspace(0, cutoff, 60)
            for fi in range(len(sd.fields)):
                res = trace_field(built, fi, 0, cache)
                pd = paraxial_trace(built, sd.primary_wl, sd.fields[fi].y)
                pts, w = image_points(res, pd.img_z)
                if len(pts):
                    curves.append((freqs, mtf_geometric(pts, w, freqs, "y"), fi))
        except Exception:
            traceback.print_exc()
        _safe(self.tab_mtf.update, curves)
