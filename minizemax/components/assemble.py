"""assemble: компоненты -> Prescription (LDE-строки). Трассировка/параксиал/GUI
остаются прежними — компонент лишь добавляет строки в протестированный конвейер."""
from __future__ import annotations
import numpy as np
from minizemax.system.lens_data import LensData, SurfaceRow
from minizemax.system.prescription import Prescription
from minizemax.system.system_data import SystemData
from minizemax.components.detector import DetectorScreen


def assemble(items, sysdata: SystemData) -> Prescription:
    """items: [(component, gap_after), ...]; gap_after — осевое расстояние от
    последней поверхности компонента до первой поверхности следующего
    (может быть отрицательным для зеркальных/сложенных схем).
    DetectorScreen ставится последним."""
    rows = [SurfaceRow("OBJ", np.inf, np.inf)]
    z = 0.0
    for comp, gap in items:
        comp.place(z)
        if isinstance(comp, DetectorScreen):
            rows.extend(comp.rows())
            continue
        rs = comp.rows()
        if rs:
            rs[-1].thickness = float(gap)
            rows.extend(rs)
        z += comp.length + float(gap)
    return Prescription(sysdata, LensData(rows))
