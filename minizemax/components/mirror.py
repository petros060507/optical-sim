"""SphericalMirror: одна отражающая сфера (переиспользует reflective-поверхность)."""
from __future__ import annotations
from minizemax.core.materials import AIR
from minizemax.core.surfaces import SphericalSurface
from minizemax.core.transform import Transform
from minizemax.components.base import OpticalComponent
from minizemax.system.lens_data import SurfaceRow


class SphericalMirror(OpticalComponent):
    def __init__(self, R, D, z=0.0, name="M", conic=0.0):
        super().__init__(z)
        self.R, self.D, self.name, self.conic = float(R), float(D), name, conic

    def surfaces(self):
        return [SphericalSurface(Transform.translation(self.z), AIR, AIR, self.D / 2,
                                 self.R, self.conic, reflective=True, name=f"{self.name}1")]

    def rows(self):
        return [SurfaceRow(f"{self.name}1", self.R, 0.0, None, self.D / 2,
                           self.conic, reflective=True)]

    def focal_length(self) -> float:
        return self.R / 2.0
