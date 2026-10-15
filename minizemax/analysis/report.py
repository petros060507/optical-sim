"""Текстовый System Report."""
from __future__ import annotations
import numpy as np
from minizemax.system.paraxial import paraxial_trace
from minizemax.analysis.seidel import seidel_sums


def system_report(built, wl=None, field=None) -> str:
    sd = built.sysdata
    wl = wl or sd.primary_wl
    field = field if field is not None else (max(f.y for f in sd.fields) or 1.0)
    pd = paraxial_trace(built, wl, field)
    L = [f"=== SYSTEM REPORT ===  wl={wl:.4f} um  field={field:.2f} deg",
         f"EFL={pd.efl:.4f} mm  BFL={pd.bfl:.4f} mm  f/#={pd.fno:.4f}",
         f"Entr pupil: z={pd.ep_z:.3f} mm D={2*pd.ep_r:.3f} mm",
         f"Exit pupil: z={pd.xp_z:.3f} mm D={2*pd.xp_r:.3f} mm",
         f"Image: z={pd.img_z:.3f} mm h={pd.img_h:.4f} mm",
         f"Total track={built.detector_z - built.surfaces[0].z:.3f} mm  "
         f"surfaces={len(built.surfaces)}",
         "--- surfaces ---"]
    from minizemax.system.lens_data import auto_comments
    rows = built.lens.real_rows()
    names = [r.comment or a for r, a in zip(rows, auto_comments(rows))]
    for idx, s in enumerate(built.surfaces):
        R = getattr(s, "radius", np.inf)
        k = getattr(s, "conic", 0.0)
        stop = " STOP" if idx == built.stop_idx else ""
        nm = names[idx] if idx < len(names) else ""
        L.append(f"  {idx:>3} {nm:16s} z={s.z:9.4f} R={R:14.4f} k={k:6.2f} "
                 f"sd={s.semi_dia:7.3f}{stop}")
    S = seidel_sums(built, wl, field)
    L += ["--- Seidel ---",
          f"S1={S.S1:+.6f} S2={S.S2:+.6f} S3={S.S3:+.6f} "
          f"S4={S.S4:+.6f} S5={S.S5:+.6f} H={S.H:+.6f}"]
    return "\n".join(L)
