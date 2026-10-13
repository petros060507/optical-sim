"""Дисторсия: реальная высота chief vs параксиальная."""
from __future__ import annotations
from minizemax.system.paraxial import paraxial_trace
from minizemax.analysis.spot import image_points
from minizemax.engine.tracer import trace_field


def distortion_pct(built, fi: int, wi: int) -> float:
    sd = built.sysdata
    pd = paraxial_trace(built, sd.wavelengths[wi].um, sd.fields[fi].y)
    res = trace_field(built, fi, wi)
    pts, _ = image_points(res, pd.img_z)
    y_real = pts[res.bundle.meta.get("chief_idx", 0)][1]
    y_par = pd.img_h
    return 100.0 * (y_real - y_par) / y_par if abs(y_par) > 1e-12 else 0.0
