"""DetectorScreen: компонент-приёмник (обёртка над engine.tracer.Detector)."""
from __future__ import annotations
import numpy as np
from minizemax.components.base import OpticalComponent
from minizemax.system.lens_data import SurfaceRow


class DetectorScreen(OpticalComponent):
    def __init__(self, half_size=10.0, nx=256, ny=256, z=0.0, name="IMA"):
        super().__init__(z)
        self.half_size, self.nx, self.ny, self.name = float(half_size), nx, ny, name

    def surfaces(self):
        return []

    def rows(self):
        return [SurfaceRow("IMA", np.inf, 0.0, None, self.half_size)]

    def detector(self):
        from minizemax.engine.tracer import Detector
        return Detector(z=self.z, half_size=self.half_size, nx=self.nx, ny=self.ny)
