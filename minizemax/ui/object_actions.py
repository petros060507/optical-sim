"""Context menu actions for optical objects."""
from __future__ import annotations
import copy
from minizemax.ui.qt import QMenu, QMessageBox, Qt
from minizemax.system.lens_data import SurfaceRow


def custom_ctx_policy():
    cp = getattr(Qt, "ContextMenuPolicy", None)
    return cp.CustomContextMenu if cp is not None else Qt.CustomContextMenu

def menu_exec(menu, gpos):
    return menu.exec(gpos) if hasattr(menu, "exec") else menu.exec_(gpos)

def dialog_exec(dlg):
    return dlg.exec() if hasattr(dlg, "exec") else dlg.exec_()

def _btn(name):
    for scope in (QMessageBox, getattr(QMessageBox, "StandardButton", None),
                  getattr(QMessageBox, "Button", None)):
        if scope is not None and hasattr(scope, name):
            return getattr(scope, name)
    raise AttributeError(f"QMessageBox.{name}")

def renumber(lens):
    for k, r in enumerate(lens.real_rows()):
        r.surf = str(k + 1)

def delete_row(pres, idx):
    rows = pres.lens.rows
    if not 0 <= idx < len(rows):
        return "Row out of range"
    row = rows[idx]
    if row.surf in ("OBJ", "IMA"):
        return f"'{row.surf}' is a system surface and cannot be deleted"
    if len(rows) <= 3:
        return "At least one optical surface is required"
    if idx > 0:
        rows[idx - 1].thickness += row.thickness
    was_stop = row.stop
    del rows[idx]
    if was_stop:
        real = pres.lens.real_rows()
        if real:
            real[max(0, min(idx - 1, len(real) - 1))].stop = True
    renumber(pres.lens)
    return None

def insert_row_after(pres, idx):
    new = SurfaceRow(surf="new", radius=100.0, thickness=50.0,
                     glass=None, semi_dia=10.0, comment="")
    pres.lens.rows.insert(idx + 1, new)
    renumber(pres.lens)
    return idx + 1

def duplicate_row(pres, idx):
    dup = copy.deepcopy(pres.lens.rows[idx])
    dup.comment = (dup.comment or f"surf{idx}") + "_copy"
    pres.lens.rows.insert(idx + 1, dup)
    renumber(pres.lens)
    return idx + 1

def build_object_menu(parent, pres, idx, on_edit, on_change):
    row = pres.lens.rows[idx]
    name = row.comment or f"Surface {row.surf}"
    locked = row.surf in ("OBJ", "IMA")
    menu = QMenu(parent)
    menu.setTitle("Object")
    a_edit = menu.addAction(f"Properties of '{name}'...")
    a_edit.triggered.connect(lambda: on_edit(idx))
    menu.addSeparator()
    a_ins = menu.addAction("Insert surface after")
    a_ins.triggered.connect(lambda: (insert_row_after(pres, idx), on_change()))
    a_dup = menu.addAction("Duplicate surface")
    a_dup.triggered.connect(lambda: (duplicate_row(pres, idx), on_change()))
    a_dup.setEnabled(not locked)
    menu.addSeparator()
    if row.surf == "IMA":
        a_focus = menu.addAction("Auto-focus detector to paraxial image")
        a_focus.triggered.connect(lambda: _focus(parent, pres, on_change))
        menu.addSeparator()

    a_del = menu.addAction(f"Delete '{name}'")
    a_del.setEnabled(not locked)
    a_del.triggered.connect(lambda: _delete(parent, pres, idx, name, on_change))
    return menu

def _delete(parent, pres, idx, name, on_change):
    ans = QMessageBox.question(
        parent, "Delete surface",
        f"Delete surface '{name}'?\nIts axial gap will be merged into the previous surface.",
        _btn("Yes") | _btn("No"), _btn("No"))
    if ans != _btn("Yes"):
        return
    err = delete_row(pres, idx)
    if err:
        QMessageBox.warning(parent, "Cannot delete", err)
        return
    on_change()


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
