"""PlaneParallelPlate: две плоские поверхности (переиспользует PlaneSurface)."""
from __future__ import annotations
import numpy as np
from minizemax.core.materials import AIR, n_at
from minizemax.core.surfaces import PlaneSurface
from minizemax.core.transform import Transform
from minizemax.components.base import OpticalComponent
from minizemax.system.lens_data import SurfaceRow


class PlaneParallelPlate(OpticalComponent):
    def __init__(self, d, D, material, z=0.0, name="P"):
        super().__init__(z)
        self.d, self.D, self.material, self.name = float(d), float(D), material, name

    @property
    def length(self): return self.d

    def surfaces(self):
        s1 = PlaneSurface(Transform.translation(self.z), AIR, self.material,
                          self.D / 2, name=f"{self.name}1")
        s2 = PlaneSurface(Transform.translation(self.z + self.d), self.material, AIR,
                          self.D / 2, name=f"{self.name}2")
        return [s1, s2]

    def rows(self):
        # Сохраняем сам Material-объект (ConstantMaterial и т.п.), не имя
        # Это позволяет использовать материалы вне каталога (например, для тестов)
        return [SurfaceRow(f"{self.name}1", np.inf, self.d, self.material, self.D / 2),
                SurfaceRow(f"{self.name}2", np.inf, 0.0, None, self.D / 2)]

    def lateral_shift(self, theta_rad: float, wl: float) -> float:
        """Вертикальный сдвиг луча (по y): s_y = s_perp / cos(θ)."""
        n = n_at(self.material, wl)
        s = np.sin(theta_rad); c = np.cos(theta_rad)
        s_perp = self.d * s * (1.0 - c / np.sqrt(n * n - s * s))
        return s_perp / c  # переводим перпендикулярный сдвиг в вертикальный
