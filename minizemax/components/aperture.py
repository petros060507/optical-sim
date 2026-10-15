"""ApertureStop: отдельная диафрагма = плоскость AIR->AIR (преломления нет,
работает только апертурный клип уже протестированной PlaneSurface)."""
from __future__ import annotations
import numpy as np
from minizemax.core.materials import AIR
from minizemax.core.surfaces import PlaneSurface
from minizemax.core.transform import Transform
from minizemax.components.base import OpticalComponent
from minizemax.system.lens_data import SurfaceRow


class ApertureStop(OpticalComponent):
    def __init__(self, D, z=0.0, name="STO"):
        super().__init__(z)
        self.D, self.name = float(D), name

    def surfaces(self):
        return [PlaneSurface(Transform.translation(self.z), AIR, AIR,
                             self.D / 2, name=self.name)]

    def rows(self):
        return [SurfaceRow(self.name, np.inf, 0.0, None, self.D / 2, stop=True)]
