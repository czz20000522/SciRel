"""Geometry primitives for the Big Red Ball and TREX coil arrangement."""

from __future__ import annotations
import numpy as np
from scirel.electromagnetism import ArbitraryPoints, RectangularCoil, MagnetRing, Device


class TREXCoil(ArbitraryPoints):
    """Construct the fixed 88-point conductor cloud of one TREX coil.

    Parameters
    ----------
    z0 : float, optional
        Axial reference-plane coordinate [m]. The default is ``1.1``.
    **kwargs : object, optional
        Additional inherited constructor entries; see Other Parameters.

    Other Parameters
    ----------------
    current : real scalar, optional
        Common drive current [A]. The default is ``1.0``.
    weights : array_like, shape (88,), optional
        Signed filament weights [dimensionless]. The default is one per point.
    mesh : Mesh or array-like, optional
        Target mesh [m] stored for later field calls. The default is ``None``.

    Returns
    -------
    source : TREXCoil
        Constructed source with the fixed ordered conductor cloud and inherited
        current, weight, mesh and field methods [geometry m; current A;
        weights dimensionless].

    Raises
    ------
    ValueError
        If ``z0``, current, weights, mesh, or field geometry violates the
        declared domain, or a target is coincident with an active filament.
    FloatingPointError
        If a Green response is not representable.
    NotImplementedError
        If ``rz_pts`` is assigned directly.

    See Also
    --------
    scirel.configurations.BRB : Fixed Big Red Ball source composition.
    scirel.electromagnetism.ArbitraryPoints : Source with arbitrary filament points.
    scirel.electromagnetism.Device : Ordered collection of source objects.

    Notes
    -----
    Five radial columns contain sixteen axial points and a sixth column
    contains eight axial midpoints, for 88 points total. Change the point
    cloud through ``z0`` or the inherited rigid transforms; its area is a
    geometry proxy, not a conductor model.

    Examples
    --------
    >>> from scirel.configurations import TREXCoil
    >>> c=TREXCoil(z0=.7)
    >>> assert c.npts == 88
    >>> c.translate([0.,.2])
    >>> assert abs(c.z0-.9)<1e-15
    """

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
    """Construct the fixed Big Red Ball filament geometry.

    Returns
    -------
    source : BRB
        Ordered device containing two TREX coils, two rectangular coils, and
        thirty-six signed magnet rings [geometry m; current A; weights
        dimensionless].

    Raises
    ------
    TypeError
        If constructor arguments are supplied.
    ValueError
        If a child source geometry, current, weight, or mesh is invalid, or a
        child field has an active filament/target coincidence.
    FloatingPointError
        If a child Green response is not representable.
    NotImplementedError
        If cathode, anode, or sweep additions are requested.

    See Also
    --------
    scirel.configurations.TREXCoil : Fixed 88-point TREX coil source.
    scirel.electromagnetism.RectangularCoil : Parameterized rectangular source array.
    scirel.electromagnetism.MagnetRing : Signed permanent-magnet ring approximation.

    Notes
    -----
    The fixed geometry registers 40 children in attribute order: two TREX
    coils, two rectangular coils, and 36 magnet rings. It is a geometry
    composition and does not calibrate an experimental device or material
    response.

    Examples
    --------
    >>> from scirel.configurations import BRB
    >>> d=BRB()
    >>> assert len(d.current_sets)==40
    >>> assert d.hh_n.npts==88
    """

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
