#!/usr/bin/env python3
"""Убирает вредный _gauge (портил back gap при drag первой группы) и добавляет
Auto-focus detector в ПКМ по IMA. Идемпотентно. Не меняет файлы-данные."""
import ast
import sys
from pathlib import Path

UI = Path("minizemax/ui")
OA = UI / "object_actions.py"
L2 = UI / "layout2d_view.py"

# ---------------------------------------------------------------- layout2d (без _gauge)
LAYOUT2D = '''"""Interactive 2D optical layout (QGraphicsView, no matplotlib): dark CAD style,
draggable CEMENTED GROUPS (z-shift), hover glow, wheel zoom, middle-button pan,
RMB context menu, dblclick properties. Geometry via surface.sag() (sphere+plane).

Drag semantics (no stretching, no silent data corruption):
  * component = maximal run of real surfaces joined by glass;
  * drag by dz changes rows[f-1].thickness (+dz) and rows[b].thickness (-dz);
    inner glass thicknesses are never touched;
  * FIRST component with object at infinity: z(first surface)=0 is fixed by the
    sequential model, so dragging it is a physical no-op -> rejected with a hint
    (use Auto-focus detector on IMA, or drag later components / the detector)."""
from __future__ import annotations

import numpy as np

from minizemax.ui.qt import (QGraphicsView, QGraphicsScene, QGraphicsPathItem, QPen,
                             QBrush, QColor, QPainterPath, QPainter, QLineF,
                             QTransform, Qt, Signal)
from minizemax.ui import theme as T
from minizemax.core.bundle import STATUS_ALIVE, STATUS_BLOCKED, STATUS_TIR, STATUS_MISS
from minizemax.engine.source import make_bundle
from minizemax.engine.tracer import SequentialTracer

_N = 48
_LEFT = getattr(Qt, "LeftButton", None) or Qt.MouseButton.LeftButton
_MID = getattr(Qt, "MiddleButton", None) or Qt.MouseButton.MiddleButton
_KEEP_AR = getattr(Qt, "KeepAspectRatio", None) or Qt.AspectRatioMode.KeepAspectRatio


def _qcol(rgba):
    return QColor(*[int(v) for v in rgba])


def _sag0(s, r):
    r = np.asarray(r, float)
    try:
        sg = np.asarray(s.sag(np.abs(r)), float)
    except Exception:
        return np.zeros_like(r)
    return np.where(np.isfinite(sg), sg, 0.0)


def _path(zs, ys):
    p = QPainterPath()
    p.moveTo(float(zs[0]), -float(ys[0]))
    for z, y in zip(zs[1:], ys[1:]):
        p.lineTo(float(z), -float(y))
    return p


class _CompItem(QGraphicsPathItem):
    def __init__(self, view, path, row_front, f, b, kind, pen, brush=None, movable=True):
        super().__init__(path)
        self.view = view
        self.row_front = row_front
        self.f = f
        self.b = b
        self.kind = kind
        self.base_pen = pen
        c = QColor(pen.color()); c.setAlpha(255)
        self.glow_pen = QPen(c); self.glow_pen.setWidthF(pen.widthF() + 1.6)
        self.glow_pen.setCosmetic(True)
        self.setPen(pen)
        if brush is not None:
            self.setBrush(brush)
        self.setAcceptHoverEvents(True)
        self._movable = movable
        self._drag_x0 = None
        self.setZValue(3 if kind != "lens" else 2)

    def hoverEnterEvent(self, e):
        self.setPen(self.glow_pen); super().hoverEnterEvent(e)

    def hoverLeaveEvent(self, e):
        self.setPen(self.base_pen); super().hoverLeaveEvent(e)

    def mousePressEvent(self, e):
        if self._movable and e.button() == _LEFT:
            self._drag_x0 = e.scenePos().x(); e.accept()
        else:
            super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._drag_x0 is not None:
            self.setPos(e.scenePos().x() - self._drag_x0, 0); e.accept()
        else:
            super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self._drag_x0 is not None:
            dz = e.scenePos().x() - self._drag_x0
            self._drag_x0 = None; self.setPos(0, 0)
            if abs(dz) > 1e-9:
                self.view._commit_move(self, dz)
            e.accept()
        else:
            super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e):
        self.view.editRequested.emit(self.row_front)

    def contextMenuEvent(self, e):
        self.view.objectMenuRequested.emit(self.row_front, e.screenPos())


class Layout2DView(QGraphicsView):
    structureChanged = Signal()
    objectMenuRequested = Signal(int, object)
    editRequested = Signal(int)
    hintMessage = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pres = None
        self._first_fit = True
        self._pan_last = None
        self._sc = QGraphicsScene(self)
        self.setScene(self._sc)
        self.setBackgroundBrush(QBrush(QColor(T.BG)))
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        va = getattr(QGraphicsView, "ViewportAnchor", QGraphicsView)
        self.setTransformationAnchor(va.AnchorUnderMouse)
        self.setResizeAnchor(va.AnchorUnderMouse)

    def set_system(self, pres):
        self.pres = pres
        self._sc.clear()
        try:
            built = pres.build()
        except Exception:
            return
        surf = built.surfaces
        h = max(s.semi_dia for s in surf) * 1.25
        self._add_rays(built)
        self._add_components(built, h)
        if self._first_fit and self._sc.items():
            r = self._sc.itemsBoundingRect().adjusted(-30, -30, 30, 30)
            self.fitInView(r, _KEEP_AR)
            self._first_fit = False

    def _add_components(self, built, h):
        surf = built.surfaces
        n = len(surf)
        rows = self.pres.lens.rows

        def cemented(i):
            if i + 1 >= n:
                return False
            m = surf[i].mat_after
            return getattr(m, "name", "air") != "air" and m is surf[i + 1].mat_before

        groups, cur = [], [0]
        for i in range(n - 1):
            if cemented(i):
                cur.append(i + 1)
            else:
                groups.append(cur); cur = [i + 1]
        groups.append(cur)

        self._group_items = {}
        for gr in groups:
            fr, br = gr[0], gr[-1]
            f_row, b_row = fr + 1, br + 1
            s_f, s_b = surf[fr], surf[br]
            if fr == br:
                r = np.linspace(-s_f.semi_dia, s_f.semi_dia, _N)
                z = s_f.z + _sag0(s_f, r)
                pen = QPen(QColor(T.MIRROR if s_f.reflective else T.GLASS_EDGE))
                pen.setWidthF(1.4); pen.setCosmetic(True)
                it = _CompItem(self, _path(z, r), f_row, f_row, b_row, "surf", pen)
            else:
                r1 = np.linspace(-s_f.semi_dia, s_f.semi_dia, _N)
                z1 = s_f.z + _sag0(s_f, r1)
                r2 = np.linspace(s_b.semi_dia, -s_b.semi_dia, _N)
                z2 = s_b.z + _sag0(s_b, r2)
                p = _path(z1, r1)
                p.lineTo(float(z2[0]), -float(r2[0]))
                for zz, yy in zip(z2, r2):
                    p.lineTo(float(zz), -float(yy))
                p.lineTo(float(z1[0]), -float(r1[0]))
                p.closeSubpath()
                pen = QPen(QColor(T.GLASS_EDGE)); pen.setWidthF(1.4); pen.setCosmetic(True)
                it = _CompItem(self, p, f_row, f_row, b_row, "lens", pen,
                               QBrush(_qcol(T.GLASS_FILL)))
                for m in gr[1:-1]:
                    sm = surf[m]
                    rr = np.linspace(-sm.semi_dia, sm.semi_dia, _N)
                    zz = sm.z + _sag0(sm, rr)
                    child = QGraphicsPathItem(_path(zz, rr), it)
                    cpen = QPen(_qcol((110, 179, 255, 90))); cpen.setWidthF(1.0)
                    cpen.setCosmetic(True); child.setPen(cpen)
            self._sc.addItem(it)
            for m in gr:
                self._group_items[m] = it

        si = built.stop_idx
        if 0 <= si < n and not surf[si].reflective:
            s = surf[si]
            p = QPainterPath()
            for sgn in (1, -1):
                p.moveTo(float(s.z), -sgn * s.semi_dia)
                p.lineTo(float(s.z), -sgn * 1.6 * s.semi_dia)
            pen = QPen(QColor(T.STOP)); pen.setWidthF(2.2); pen.setCosmetic(True)
            it = _CompItem(self, p, si + 1, si + 1, si + 1, "stop", pen, movable=False)
            parent = self._group_items.get(si)
            if parent is not None:
                it.setParentItem(parent)
            else:
                self._sc.addItem(it)

        p = QPainterPath()
        p.moveTo(float(built.detector_z), -h)
        p.lineTo(float(built.detector_z), h)
        pen = QPen(QColor(T.DETECTOR)); pen.setWidthF(2.0); pen.setCosmetic(True)
        last = len(rows) - 1
        self._sc.addItem(_CompItem(self, p, last, last, last, "detector", pen))

    def _add_rays(self, built):
        ang = np.linspace(0, 2 * np.pi, 12, endpoint=False)
        px = np.concatenate([[0.0], 0.85 * np.cos(ang)])
        py = np.concatenate([[0.0], 0.85 * np.sin(ang)])
        try:
            b = make_bundle(built, 0, 0, px=px, py=py, w=np.ones(len(px)) / len(px))
            res = SequentialTracer(built.surfaces, record_history=True).trace(b)
        except Exception:
            return
        bb = res.bundle
        dz = bb.direction[:, 2]
        safe = np.abs(dz) > 1e-12
        tz = np.where(safe, (built.detector_z - bb.origin[:, 2]) / np.where(safe, dz, 1.0), np.nan)
        pz = bb.origin + np.where(np.isfinite(tz), tz, 0.0)[:, None] * bb.direction
        pts_all = res.history + [pz]
        COLORS = {STATUS_ALIVE: T.RAY, STATUS_BLOCKED: T.RAY_BLOCKED,
                  STATUS_TIR: T.RAY_TIR, STATUS_MISS: T.RAY_MISS}
        stop_surf = getattr(res, "stop_surf", None)
        stop_point = getattr(res, "stop_point", None)
        for j in range(len(px)):
            k = int(stop_surf[j]) if stop_surf is not None else -1
            if k < 0:
                P = np.array([hh[j] for hh in pts_all])
            else:
                P = np.array([hh[j] for hh in pts_all[:k + 1]])
                if bb.status[j] in (STATUS_BLOCKED, STATUS_TIR) and stop_point is not None:
                    sp = stop_point[j]
                    if np.isfinite(sp).all():
                        P = np.concatenate([P, sp[None, :]], 0)
            P = P[np.isfinite(P[:, 2])]
            if len(P) < 2:
                continue
            pen = QPen(_qcol(COLORS[int(bb.status[j])]))
            pen.setWidthF(1.0); pen.setCosmetic(True)
            it = QGraphicsPathItem(_path(P[:, 2], P[:, 1]))
            it.setPen(pen); it.setZValue(1)
            self._sc.addItem(it)

    def _commit_move(self, item, dz):
        rows = self.pres.lens.rows
        if item.kind == "detector":
            rows[item.b - 1].thickness += dz
            self.structureChanged.emit()
            return
        f, b = item.f, item.b
        prev = rows[f - 1].thickness
        if f == 1 and not np.isfinite(prev):
            self.hintMessage.emit(
                "Object at infinity: first surface is fixed at z=0 in the sequential "
                "model - drag it is a no-op. Use Auto-focus detector (RMB on IMA) or "
                "drag later components / the detector.")
            return
        rows[f - 1].thickness = prev + dz
        rows[b].thickness -= dz
        self.structureChanged.emit()

    def wheelEvent(self, e):
        f = 1.15 if e.angleDelta().y() > 0 else 1.0 / 1.15
        self.scale(f, f)

    def mousePressEvent(self, e):
        empty = self.scene().itemAt(self.mapToScene(e.pos()), QTransform()) is None
        if e.button() == _MID or (e.button() == _LEFT and empty):
            self._pan_last = e.pos(); e.accept()
        else:
            super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._pan_last is not None:
            d = e.pos() - self._pan_last; self._pan_last = e.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - d.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - d.y())
            e.accept()
        else:
            super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._pan_last = None; super().mouseReleaseEvent(e)

    def drawBackground(self, p, rect):
        super().drawBackground(p, rect)
        scale = self.transform().m11() or 1.0
        target = 80.0 / max(scale, 1e-9)
        step = 10.0 ** np.floor(np.log10(max(target, 1e-9)))
        for m in (1, 2, 5, 10):
            if step * m >= target:
                step *= m; break
        p.setPen(QPen(QColor(T.GRID), 0))
        x = np.floor(rect.left() / step) * step
        while x <= rect.right():
            p.drawLine(QLineF(float(x), rect.top(), float(x), rect.bottom())); x += step
        y = np.floor(rect.top() / step) * step
        while y <= rect.bottom():
            p.drawLine(QLineF(rect.left(), float(y), rect.right(), float(y))); y += step
'''

FOCUS_FN = '''

def focus_detector(pres):
    """Set the last real surface's thickness so the detector lands on the
    paraxial image plane (img_z). Raises on failure (caller shows it)."""
    import numpy as np
    from minizemax.system.paraxial import paraxial_trace
    built = pres.build()
    sd = pres.sysdata
    fy = max((f.y for f in sd.fields), default=0.0)
    pd = paraxial_trace(built, sd.primary_wl, fy)
    if not np.isfinite(pd.img_z):
        raise ValueError("paraxial image is at infinity (afocal system); "
                         "cannot auto-focus the detector")
    z_last = built.surfaces[-1].z
    rows = pres.lens.rows
    last = max(i for i, r in enumerate(rows) if r.surf not in ("OBJ", "IMA"))
    rows[last].thickness = float(pd.img_z - z_last)


def _focus(parent, pres, on_change):
    try:
        focus_detector(pres)
    except Exception as ex:  # noqa: BLE001
        QMessageBox.warning(parent, "Auto-focus failed", str(ex))
        return
    on_change()
'''

FOCUS_MENU = '''    if row.surf == "IMA":
        a_focus = menu.addAction("Auto-focus detector to paraxial image")
        a_focus.triggered.connect(lambda: _focus(parent, pres, on_change))
        menu.addSeparator()

'''


def main():
    if not UI.exists():
        print("⚠ minizemax/ui не найдена — запускайте из корня репозитория")
        return 1

    ast.parse(LAYOUT2D)
    L2.write_text(LAYOUT2D, encoding="utf-8")
    print(f"✓ Перезаписан {L2} (_gauge удалён; drag первой группы при inf = no-op + hint)")

    src = OA.read_text(encoding="utf-8")
    if "def focus_detector" not in src:
        src = src.rstrip("\n") + "\n" + FOCUS_FN
        print("✓ object_actions.py: добавлены focus_detector / _focus")
    else:
        print("✓ object_actions.py: focus_detector уже есть")
    if "Auto-focus detector to paraxial image" not in src:
        anchor = '    a_del = menu.addAction(f"Delete \'{name}\'")\n'
        if anchor not in src:
            print("⚠ не найден якорь a_del в build_object_menu — проверьте вручную")
            return 1
        src = src.replace(anchor, FOCUS_MENU + anchor, 1)
        print("✓ object_actions.py: пункт Auto-focus detector в ПКМ по IMA")
    else:
        print("✓ object_actions.py: пункт Auto-focus уже в меню")
    ast.parse(src)
    OA.write_text(src, encoding="utf-8")

    print()
    print("Вернуть doublet к исходному back gap (46.3), если 76.4376 — мусор от гейдж-драга:")
    print("    git checkout -- examples/doublet.zmx-lite")
    print("ИЛИ в GUI: ПКМ по строке IMA -> Auto-focus detector to paraxial image")
    print("    (поставит back gap = BFL, детектор точно в параксиальный фокус).")
    print()
    print("Проверка: minizemax gui examples/doublet.zmx-lite")
    print("  * drag дублета при inf -> подсказка в статус-баре, данные НЕ меняются;")
    print("  * drag детектора / 2-й группы -> едет как раньше, без растягивания;")
    print("  * ПКМ по IMA -> Auto-focus -> лучи в 3D снова сходятся на детекторе.")
    return 0


if __name__ == "__main__":
    sys.exit(main())