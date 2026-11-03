"""WHAM coil geometry with device-library constructor defaults."""

from scirel.electromagnetism import Device, RectangularCoil


class WHAM(Device):
    def __init__(self):
        super().__init__()
        self.hts1 = RectangularCoil(0.25, 0.942, nr=8, nz=4, dr=0.0475, dz=0.0275)
        self.hts2 = RectangularCoil(0.25, -0.942, nr=8, nz=4, dr=0.0475, dz=0.0275)
        self.cc1 = RectangularCoil(1.005, 0.205, nr=2, nz=5, dr=0.025, dz=0.024)
        self.cc2 = RectangularCoil(1.005, -0.205, nr=2, nz=5, dr=0.025, dz=0.024)


__all__ = ["WHAM"]
