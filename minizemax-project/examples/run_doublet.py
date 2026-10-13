"""Демо: report -> spot/OPD до -> DLS -> spot/fan после -> doublet.png"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from minizemax.system.prescription import Prescription
from minizemax.analysis.report import system_report
from minizemax.analysis.spot import spot_stats, image_points, ray_fan
from minizemax.analysis.wavefront import opd_waves, wavefront_stats
from minizemax.analysis.layout import layout
from minizemax.engine.tracer import trace_field
from minizemax.system.paraxial import paraxial_trace
from minizemax.optim.merit import MeritFunction
from minizemax.optim.dls import DLSOptimizer

pres = Prescription.load("examples/doublet.zmx-lite")
built = pres.build()
print(system_report(built)); print()

print("=== BEFORE ===")
for fi in range(len(pres.sysdata.fields)):
    res = trace_field(built, fi, 0)
    pd = paraxial_trace(built, 0.5876, pres.sysdata.fields[fi].y)
    pts, w = image_points(res, pd.img_z)
    s = spot_stats(pts, w)
    print(f"  field {pres.sysdata.fields[fi].y:4.1f} deg: "
          f"RMS={s['rms']*1000:7.2f} um GEO={s['geo_max']*1000:7.2f} um")
    if fi == 0:
        ws = wavefront_stats(opd_waves(built, res, 0, 0))
        print(f"    OPD PV={ws['pv']:.4f} RMS={ws['rms']:.4f} waves")

mf = MeritFunction.default_rms_spot(pres)
r = DLSOptimizer(pres, mf).run(max_iters=80)
print(f"\nmerit {r.merit0:.6g} -> {r.merit1:.6g}  x={np.round(r.x, 4)}")

bo = pres.build()
print("\n=== AFTER ===")
for fi in range(len(pres.sysdata.fields)):
    res = trace_field(bo, fi, 0)
    pd = paraxial_trace(bo, 0.5876, pres.sysdata.fields[fi].y)
    pts, w = image_points(res, pd.img_z)
    s = spot_stats(pts, w)
    print(f"  field {pres.sysdata.fields[fi].y:4.1f} deg: RMS={s['rms']*1000:7.2f} um")

fig, ax = plt.subplots(1, 3, figsize=(15, 4))
layout(bo, ax=ax[0]); ax[0].set_title("Layout after opt")
for fi, col in enumerate(["C0", "C1"]):
    res = trace_field(bo, fi, 0)
    pd = paraxial_trace(bo, 0.5876, pres.sysdata.fields[fi].y)
    pts, _ = image_points(res, pd.img_z)
    ax[1].plot(pts[:, 0]*1e3, pts[:, 1]*1e3, ".", ms=1, color=col,
               label=f"{pres.sysdata.fields[fi].y:.0f} deg")
ax[1].set_xlabel("x um"); ax[1].set_ylabel("y um")
ax[1].set_title("Spot"); ax[1].legend(); ax[1].set_aspect("equal")
sa, ex, ey = ray_fan(bo, 1, 0, 31)
ax[2].plot(sa, ey*1e3, "C1-", lw=1.5, label="tan ey")
ax[2].plot(sa, ex*1e3, "C0--", label="sag ex")
ax[2].set_xlabel("Py"); ax[2].set_ylabel("um")
ax[2].set_title("Ray fan 3 deg"); ax[2].legend(); ax[2].grid(alpha=0.3)
fig.tight_layout(); fig.savefig("doublet.png", dpi=150)
print("\nSaved doublet.png")
