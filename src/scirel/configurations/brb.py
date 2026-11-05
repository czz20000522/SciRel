"""Geometry primitives for the Big Red Ball and TREX coil arrangement."""

from __future__ import annotations
import numpy as np
from scirel.electromagnetism import ArbitraryPoints, RectangularCoil, MagnetRing, Device


class TREXCoil(ArbitraryPoints):
    """Represent the fixed conductor cloud of one TREX coil."""

    _RMIN = 2.00467
    _DR = 0.0134166
    _DZ = 0.0140625
    _COND_AREA = _DR * _DR
    _NPTS = 88
    _Z_REL_POS = np.linspace(-0.105469, 0.105469, 16)
    _R_REL_POS = np.linspace(0, 0.067083, 6)

    def __init__(self, z0=1.1, **kwargs):
        self._z0 = float(z0)
        r = self._RMIN + self._R_REL_POS
        z = self._z0 + self._Z_REL_POS
        p = [(ri, zi) for ri in r[:5] for zi in z]
        p.extend((r[5], zi) for zi in (z[::2] + z[1::2]) / 2)
        super().__init__(np.asarray(p), **kwargs)

    z0 = property(lambda s: s._z0, lambda s, v: s._set_z(v))
    dr = property(lambda s: s._DR)
    dz = property(lambda s: s._DZ)
    area = property(lambda s: s._COND_AREA * s._NPTS)
    current_density = property(lambda s: s.total_current / s.area)

    def _set_z(self, v):
        self.translate([0.0, float(v) - self._z0])

    def translate(self, vector):
        """Translate the cloud and its reference plane as one valid state."""
        delta = np.asarray(vector, dtype=float)
        super().translate(delta)
        self._z0 += delta[1]

    def rotate(self, angle, pivot=(0.0, 0.0)):
        """Rotate the cloud and its centroid's reference-plane coordinate."""
        super().rotate(angle, pivot)
        self._z0 = float(self.rz_pts.mean(axis=0)[1])

    @ArbitraryPoints.rz_pts.setter
    def rz_pts(self, v):
        raise NotImplementedError("TREXCoil geometry is changed through z0")


class BRB(Device):
    """Big Red Ball filament geometry; cathode/anode and sweep APIs excluded."""

    def __init__(self):
        super().__init__()
        patch_kw = {}
        self.hh_n = TREXCoil(1.1, patch_kw=patch_kw)
        self.hh_s = TREXCoil(-1.1, patch_kw=patch_kw)
        r0, z0 = 0.185725, 1.6367
        dr, dz = 0.010583333, 0.01031667
        self.ltrx_n = RectangularCoil(r0, z0, nr=10, nz=13, dr=dr, dz=dz)
        self.ltrx_s = RectangularCoil(r0, -z0, nr=10, nz=13, dr=dr, dz=dz)
        cr = 1.514475
        theta = np.linspace(7.5, 172.5, 34)
        rzmu = np.empty((36, 3))
        rzmu[0] = [0.0768, 1.5117, 0.0]
        rzmu[1:-1, 0] = cr * np.sin(np.deg2rad(theta))
        rzmu[1:-1, 1] = cr * np.cos(np.deg2rad(theta))
        rzmu[1:-1, 2] = theta + np.mod(np.arange(1, 35), 2) * 180
        rzmu[-1] = [0.0768, -1.5117, 0.0]
        for i, (r, z, mu) in enumerate(rzmu):
            setattr(
                self,
                f"mr{i + 1}",
                MagnetRing(r0=r, z0=z, mu_hat=mu, current=2710.68, height=0.0254, width=0.0381),
            )

    def add_cathode(self, *args, **kwargs):
        raise NotImplementedError("cathodes are outside the filament geometry contract")

    def add_anode(self, *args, **kwargs):
        raise NotImplementedError("anodes are outside the filament geometry contract")

    def add_sweep(self, *args, **kwargs):
        raise NotImplementedError("persistent sweep geometry is not implemented")


__all__ = ["TREXCoil", "BRB"]
