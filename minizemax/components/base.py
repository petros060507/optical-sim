"""OpticalComponent: компонент = композиция УЖЕ протестированных поверхностей.
Никакой новой физики пересечений: только core.surfaces + core.physics."""
from __future__ import annotations
from minizemax.core.surfaces import OpticalSurface
from minizemax.system.lens_data import SurfaceRow


class OpticalComponent:
    name = "component"

    def __init__(self, z: float = 0.0):
        self.z = float(z)

    @property
    def length(self) -> float:
        """Осевая протяжённость (от первой до последней поверхности)."""
        return 0.0

    def place(self, z: float) -> "OpticalComponent":
        self.z = float(z)
        return self

    def surfaces(self) -> list[OpticalSurface]:
        raise NotImplementedError

    def rows(self) -> list[SurfaceRow]:
        """LDE-строки: компонент встраивается в уже протестированный конвейер."""
        raise NotImplementedError
