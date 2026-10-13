"""CLI: report / spot / optimize / layout-cmd / gui."""
from __future__ import annotations
import typer
import numpy as np

app = typer.Typer(help="mini-Zemax sequential optical design toy")


@app.command()
def report(path: str):
    from minizemax.system.prescription import Prescription
    from minizemax.analysis.report import system_report
    typer.echo(system_report(Prescription.load(path).build()))


@app.command()
def spot(path: str, field: int = 0, wl: int = 0):
    from minizemax.system.prescription import Prescription
    from minizemax.analysis.spot import spot_stats, image_points
    from minizemax.engine.tracer import trace_field
    from minizemax.system.paraxial import paraxial_trace
    pres = Prescription.load(path); built = pres.build()
    pd = paraxial_trace(built, pres.sysdata.wavelengths[wl].um, pres.sysdata.fields[field].y)
    res = trace_field(built, field, wl)
    pts, w = image_points(res, pd.img_z)
    s = spot_stats(pts, w)
    typer.echo(f"field={pres.sysdata.fields[field].y:.1f} deg RMS={s['rms']*1000:.2f} um "
               f"GEO={s['geo_max']*1000:.2f} um n={s['n']}")


@app.command()
def optimize(path: str, iters: int = 40, save: str = ""):
    from minizemax.system.prescription import Prescription
    from minizemax.optim.merit import MeritFunction
    from minizemax.optim.dls import DLSOptimizer
    pres = Prescription.load(path)
    mf = MeritFunction.default_rms_spot(pres)
    r = DLSOptimizer(pres, mf).run(max_iters=iters)
    typer.echo(f"merit: {r.merit0:.6g} -> {r.merit1:.6g}  niters={r.niters}")
    typer.echo(f"x={np.round(r.x, 4)}")
    if save:
        pres.save(save); typer.echo(f"Saved {save}")


@app.command(name="layout-cmd")
def layout_cmd(path: str, out: str = "layout.png", field: int = 0, wl: int = 0):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from minizemax.system.prescription import Prescription
    from minizemax.analysis.layout import layout
    pres = Prescription.load(path)
    fig, ax = plt.subplots(figsize=(10, 4))
    layout(pres.build(), field, wl, ax=ax)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    typer.echo(f"Saved {out}")


@app.command()
def gui(path: str = typer.Argument("", help="prescription YAML (пусто = встроенный дублет)")):
    """Запустить PyQt-интерфейс."""
    from minizemax.ui.app import main
    raise SystemExit(main(["minizemax-gui", path] if path else ["minizemax-gui"]))


if __name__ == "__main__":
    app()
