"""Prescription: YAML load/save (аналог .ZMX)."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import yaml
from minizemax.system.system_data import SystemData, Wavelength, Field, ApertureDef, Sampling
from minizemax.system.lens_data import LensData, SurfaceRow, build_system


@dataclass
class Prescription:
    sysdata: SystemData
    lens: LensData

    @classmethod
    def from_yaml(cls, text):
        d = yaml.safe_load(text)
        s = d["system"]
        wls = [Wavelength(w["l"], w.get("w", 1.0), w.get("primary", i == 0))
               for i, w in enumerate(s["wavelengths_um"])]
        flds = [Field(f["y"], f.get("w", 1.0)) for f in s["fields_deg"]]
        ap = ApertureDef(s["aperture"]["type"], s["aperture"]["value"])
        sam = Sampling(**s.get("sampling", {}))
        rows = [SurfaceRow(str(r["surf"]), r.get("radius", np.inf), r.get("thickness", 0.0),
                           r.get("glass"), r.get("semi_dia", 10.0), r.get("conic", 0.0),
                           r.get("stop", False), r.get("reflective", False),
                           r.get("variables", []))
                for r in d["lens_data"]]
        return cls(SystemData(ap, wls, flds, sam), LensData(rows))

    @classmethod
    def load(cls, path):
        with open(path) as f:
            return cls.from_yaml(f.read())

    def save(self, path):
        d = {
            "system": {
                "aperture": {"type": self.sysdata.aperture.type,
                             "value": self.sysdata.aperture.value},
                "wavelengths_um": [{"l": w.um, "w": w.weight, "primary": w.primary}
                                   for w in self.sysdata.wavelengths],
                "fields_deg": [{"y": f.y, "w": f.weight} for f in self.sysdata.fields],
                "sampling": {"kind": self.sysdata.sampling.kind,
                             "rings": self.sysdata.sampling.rings},
            },
            "lens_data": [
                {**{"surf": r.surf},
                 **({"radius": r.radius} if np.isfinite(r.radius) else {}),
                 "thickness": r.thickness,
                 **({"glass": r.glass} if r.glass else {}),
                 "semi_dia": r.semi_dia,
                 **({"conic": r.conic} if r.conic != 0 else {}),
                 **({"stop": True} if r.stop else {}),
                 **({"reflective": True} if r.reflective else {}),
                 **({"variables": r.variables} if r.variables else {})}
                for r in self.lens.rows],
        }
        with open(path, "w") as f:
            yaml.dump(d, f, default_flow_style=False, allow_unicode=True)

    def build(self):
        return build_system(self.sysdata, self.lens)
