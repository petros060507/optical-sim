"""Demo Prompt 6: test systems A (singlet), B (doublet+stop), C (mirror)."""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from minizemax.components import (SphericalLens, SphericalMirror, ApertureStop,
                                  DetectorScreen, assemble)
from minizemax.analysis.report import system_report
from minizemax.analysis.layout import layout
from minizemax.core.materials import glass
from minizemax.system.system_data import SystemData, ApertureDef, Wavelength, Field

sd20 = SystemData(ApertureDef("EPD", 20.0), [Wavelength(0.5876, primary=True)], [Field(0.0)])
sd25 = SystemData(ApertureDef("EPD", 25.0), [Wavelength(0.5876, primary=True)], [Field(0.0)])
det = DetectorScreen(8.0)

lens = SphericalLens(61.467, -44.644, 12.0, 25.0, glass("N-BK7"), name="L1")
presA = assemble([(lens, 47.0), (det, 0.0)], sd20)

l1 = SphericalLens(122.794, -83.550, 12.0, 25.0, glass("N-SK16"), name="A")
l2 = SphericalLens(-83.550, -773.600, 2.85, 24.0, glass("N-F2"), name="B")
sto = ApertureStop(24.0)
presB = assemble([(l1, 0.0), (l2, 0.0), (sto, 46.3), (det, 0.0)], sd25)

mir = SphericalMirror(-200.0, 40.0, name="M1")
presC = assemble([(mir, -100.0), (det, 0.0)], sd20)

fig, axes = plt.subplots(1, 3, figsize=(16, 4))
for ax, pres, title in zip(axes, [presA, presB, presC],
                           ["A: singlet", "B: doublet + stop", "C: mirror"]):
    layout(pres.build(), 0, 0, ax=ax)
    ax.set_title(title)
    print(system_report(pres.build()))
    print()
fig.tight_layout()
fig.savefig("components_demo.png", dpi=150)
print("Saved components_demo.png")
