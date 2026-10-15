"""Prescription: YAML load/save (аналог .ZMX)."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import yaml
from minizemax.system.system_data import SystemData, Wavelength, Field, ApertureDef, Sampling
from minizemax.system.lens_data import LensData, SurfaceRow, build_system

def _to_float(v, default=np.inf):
    """Безопасный float: понимает числа и строки 'inf'/'.inf'/'-inf'/'nan'
    (PyYAML safe_load парсит 'inf' без точки как строку)."""
    if v is None or isinstance(v, bool):
        return default
    if isinstance(v, (int, float)):
        return float(v)
    t = str(v).strip().lower()
    if t in ("inf", ".inf", "+inf", "+.inf"):
        return float("inf")
    if t in ("-inf", "-.inf"):
        return float("-inf")
    if t in ("nan", ".nan"):
        return float("nan")
    try:
        return float(t)
    except ValueError:
        return default



@dataclass
class Prescription:
    sysdata: SystemData
    lens: LensData

    @classmethod
    def from_yaml(cls, text):
        d = yaml.safe_load(text)
        s = d["system"]
        wls = [Wavelength(_to_float(w["l"]), _to_float(w.get("w", 1.0), 1.0),
                          bool(w.get("primary", i == 0)))
               for i, w in enumerate(s["wavelengths_um"])]
        flds = [Field(_to_float(f["y"]), _to_float(f.get("w", 1.0), 1.0))
                for f in s["fields_deg"]]
        ap = ApertureDef(str(s["aperture"]["type"]), _to_float(s["aperture"]["value"]))
        sam = Sampling(**s.get("sampling", {}))
        rows = [SurfaceRow(str(r["surf"]), _to_float(r.get("radius"), np.inf),
                           _to_float(r.get("thickness"), 0.0), r.get("glass"),
                           _to_float(r.get("semi_dia"), 10.0), _to_float(r.get("conic"), 0.0),
                           bool(r.get("stop", False)), bool(r.get("reflective", False)),
                           r.get("variables", []), r.get("comment", ""))
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
                 **({"variables": r.variables} if r.variables else {}),
                 **({"comment": r.comment} if r.comment else {})}
                for r in self.lens.rows],
        }
        with open(path, "w") as f:
            yaml.dump(d, f, default_flow_style=False, allow_unicode=True)

    def build(self):
        return build_system(self.sysdata, self.lens)
