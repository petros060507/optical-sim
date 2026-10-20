"""Регрессия: _xy должен ВЫЗЫВАТЬ position() (метод), а не читать атрибут."""
from minizemax.ui.view3d_qt import GLView3D


class _Pt:
    def __init__(self, x, y):
        self._x, self._y = x, y
    def x(self): return self._x
    def y(self): return self._y


class _EvtPos:           # PyQt6/5.15+: position() — метод -> QPointF
    def __init__(self, x, y): self._p = _Pt(x, y)
    def position(self): return self._p


class _EvtXY:            # старый PyQt5: только x()/y()
    def __init__(self, x, y): self._x, self._y = x, y
    def x(self): return self._x
    def y(self): return self._y


def test_xy_calls_position_method():
    assert GLView3D._xy(_EvtPos(12.7, 33.2)) == (12, 33)


def test_xy_falls_back_to_x_y():
    assert GLView3D._xy(_EvtXY(5, 9)) == (5, 9)
