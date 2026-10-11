"""WHAM source coil geometry; currents remain constructor-default 1 A."""
from scirel.electromagnetism import Device, RectangularCoil
class WHAM(Device):
    def __init__(self):
        super().__init__()
        self.hts1=RectangularCoil(.25,.942,nr=8,nz=4,dr=.0475,dz=.0275)
        self.hts2=RectangularCoil(.25,-.942,nr=8,nz=4,dr=.0475,dz=.0275)
        self.cc1=RectangularCoil(1.005,.205,nr=2,nz=5,dr=.025,dz=.024)
        self.cc2=RectangularCoil(1.005,-.205,nr=2,nz=5,dr=.025,dz=.024)
__all__=['WHAM']
