"""SphericalLens: две преломляющие сферы + толщина + материал n(λ)."""
from __future__ import annotations
import numpy as np
from minizemax.core.materials import AIR, n_at
from minizemax.core.surfaces import SphericalSurface, PlaneSurface
from minizemax.core.transform import Transform
from minizemax.components.base import OpticalComponent
from minizemax.system.lens_data import SurfaceRow


class SphericalLens(OpticalComponent):
    def __init__(self, R1, R2, d, D, material, z=0.0, name="L", conic1=0.0, conic2=0.0):
        super().__init__(z)
        self.R1, self.R2, self.d, self.D = float(R1), float(R2), float(d), float(D)
        self.material = material
        self.name = name
        self.conic1, self.conic2 = conic1, conic2

    @property
    def length(self) -> float:
        return self.d

    def _mk(self, radius, conic, z, mb, ma, name):
        if np.isfinite(radius):
            return SphericalSurface(Transform.translation(z), mb, ma,
                                    self.D / 2, radius, conic, name=name)
        return PlaneSurface(Transform.translation(z), mb, ma, self.D / 2, name=name)

    def surfaces(self):
        s1 = self._mk(self.R1, self.conic1, self.z, AIR, self.material, f"{self.name}1")
        s2 = self._mk(self.R2, self.conic2, self.z + self.d, self.material, AIR, f"{self.name}2")
        return [s1, s2]

    def rows(self):
        g = getattr(self.material, "name", None)
        return [
            SurfaceRow(f"{self.name}1", self.R1, self.d, g, self.D / 2, self.conic1),
            SurfaceRow(f"{self.name}2", self.R2, 0.0, None, self.D / 2, self.conic2),
        ]

    def efl_paraxial(self, wl: float) -> float:
        """Формула шлифовщика: 1/f = (n-1)[1/R1 - 1/R2 + (n-1)d/(n R1 R2)]."""
        n = n_at(self.material, wl)
        iR1 = 1.0 / self.R1 if np.isfinite(self.R1) else 0.0
        iR2 = 1.0 / self.R2 if np.isfinite(self.R2) else 0.0
        inv = (n - 1.0) * (iR1 - iR2 + (n - 1.0) * self.d * iR1 * iR2 / n)
        return 1.0 / inv
