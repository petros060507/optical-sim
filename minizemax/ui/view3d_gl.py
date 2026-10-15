"""GPU-виджет 3D (pyqtgraph.opengl <=0.13.x — стабильная GL-линейка).
При pyqtgraph>=0.14 GUI автоматически падает на matplotlib-3D (см. gl_available).
Форсировать GPU на 0.14+: MZ_GL_FORCE=1. Отключить GL: MZ_NO_GL=1."""
from __future__ import annotations
import os
import numpy as np
from minizemax.ui.qt import QWidget, QVBoxLayout


def gl_available() -> bool:
    if os.environ.get("MZ_NO_GL"):
        return False
    try:
        import pyqtgraph
        import pyqtgraph.opengl  # noqa: F401
        v = tuple(int(x) for x in pyqtgraph.__version__.split(".")[:2])
        if v >= (0, 14) and not os.environ.get("MZ_GL_FORCE"):
            return False
        return True
    except Exception:
        return False


class GLView3D(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        import pyqtgraph.opengl as gl
        self._gl = gl
        self.view = gl.GLViewWidget()
        self.view.setBackgroundColor(18, 18, 24)
        self.view.opts["distance"] = 300.0
        self.view.opts["elevation"] = 20.0
        self.view.opts["azimuth"] = -60.0
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.view)
        self._items = []

    def set_scene(self, scene) -> None:
        from minizemax.analysis.scene3d import to_gl
        import pyqtgraph as pg
        gl = self._gl
        for it in self._items:
            self.view.removeItem(it)
        self._items.clear()

        for m in scene.meshes:
            item = gl.GLMeshItem(vertexes=to_gl(m.verts), faces=m.faces,
                                 color=m.color, smooth=False,
                                 glOptions=m.gl_options)
            self.view.addItem(item)
            self._items.append(item)

        # лучи: по одной полилинии (line_strip есть во всех версиях pyqtgraph)
        for P, color in (getattr(scene, "polylines", None) or []):
            item = gl.GLLinePlotItem(pos=to_gl(P),
                                     color=tuple(float(c) for c in color),
                                     mode="line_strip", width=1.0, antialias=False)
            self.view.addItem(item)
            self._items.append(item)

        c = to_gl(scene.center[None, :])[0]
        self.view.opts["center"] = pg.Vector(float(c[0]), float(c[1]), float(c[2]))
        self.view.opts["distance"] = float(scene.scale) * 1.35
        self.view.update()
