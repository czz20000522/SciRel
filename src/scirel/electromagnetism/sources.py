"""Mutable weighted circular-filament sources and ordered devices."""

from __future__ import annotations

import numpy as np

from scirel.geometry import Mesh, rotate

from .greens import compute_greens


def _points(value):
    """Return a finite ``(N, 2)`` cylindrical point table."""
    if np.iscomplexobj(value):
        raise ValueError("rz_pts must contain real values")
    points = np.asarray(value, dtype=float)
    if points.ndim != 2 or points.shape[1] != 2:
        raise ValueError("rz_pts must have shape (N, 2)")
    if not np.all(np.isfinite(points)) or np.any(points[:, 0] < 0.0):
        raise ValueError("rz_pts must be finite with non-negative radius")
    return points


def _common_current(value):
    """Validate a finite scalar current override."""
    current = np.asarray(value, dtype=float)
    if current.ndim != 0 or not np.isfinite(current):
        raise ValueError("current must be a finite scalar")
    return float(current)


def _weights(value, count):
    weights = np.asarray(value, dtype=float)
    if weights.ndim != 1 or weights.size != count or not np.all(np.isfinite(weights)):
        raise ValueError("weights must be a finite vector matching npts")
    return weights.copy()


def _rebuild_atomic(source, changes):
    """Apply parameter changes transactionally and rebuild the point cloud."""
    old_values = {name: getattr(source, name) for name in changes}
    old_points = source._rz_pts.copy()
    try:
        for name, value in changes.items():
            if name in {"_nr", "_nz"}:
                if isinstance(value, (bool, np.bool_)) or int(value) != value or int(value) < 1:
                    raise ValueError("point count must be positive integer")
                value = int(value)
            else:
                value = float(value)
                if not np.isfinite(value):
                    raise ValueError("geometry parameters must be finite")
                if name in {"_dr", "_dz", "_width", "_height"} and value <= 0.0:
                    raise ValueError("geometry dimensions must be positive")
                if name == "_r0" and value < 0.0:
                    raise ValueError("radius must be non-negative")
            setattr(source, name, value)
        source._build()
        _points(source._rz_pts)
        if hasattr(source, "_weights") and len(source._weights) != len(source._rz_pts):
            raise ValueError("point count must match weights; construct a new source to resize")
    except Exception:
        for name, value in old_values.items():
            setattr(source, name, value)
        source._rz_pts = old_points
        raise
    source._invalidate()


def _replace_points_atomic(source, value):
    points = _points(value)
    if hasattr(source, "_weights") and points.shape[0] != source._weights.size:
        raise ValueError("point count must match weights; construct a new source to resize")
    source._rz_pts = points.copy()
    source._invalidate()


class CurrentFilamentSet:
    """A finite collection of weighted circular filaments.

    Parameters
    ----------
    current : real scalar, optional
        Common drive current [A]. Must be finite. The default is ``1.0``.
    weights : array_like, shape (N,), optional
        Signed filament weights [dimensionless], one per point. Must be finite
        and match the point count. The default is one per point.
    mesh : Mesh or array-like, optional
        Target mesh [m] stored for later field calls. The default is ``None``.

    Raises
    ------
    ValueError
        If ``current``, ``weights``, or ``mesh`` violates its contract.
    TypeError
        If an unknown keyword argument is supplied; a misspelt entry is not
        silently ignored.
    """

    def __init__(self, current=1.0, weights=None, mesh=None):
        self._mesh = None
        _points(self._rz_pts)
        self._current = _common_current(current)
        self._weights = (
            np.ones(self.npts, dtype=float) if weights is None else _weights(weights, self.npts)
        )
        self._cache_key = None
        self._cache = None
        if mesh is not None:
            self.mesh = mesh

    @property
    def npts(self):
        return len(self._rz_pts)

    @property
    def rz_pts(self):
        return self._rz_pts

    @rz_pts.setter
    def rz_pts(self, value):
        _replace_points_atomic(self, value)

    @property
    def weights(self):
        return self._weights

    @weights.setter
    def weights(self, value):
        self._weights = _weights(value, self.npts)
        self._invalidate()

    @property
    def current(self):
        return self._current

    @current.setter
    def current(self, value):
        self._current = _common_current(value)
        self._invalidate()

    @property
    def total_current(self):
        return self.current * np.sum(self.weights)

    @total_current.setter
    def total_current(self, value):
        weight_sum = float(np.sum(self.weights))
        if not np.isfinite(weight_sum) or weight_sum == 0.0:
            raise ValueError("cannot set total_current when weight sum is zero")
        self.current = float(value) / weight_sum

    @property
    def rzw(self):
        return np.column_stack((self.rz_pts, self.weights))

    @property
    def mesh(self):
        return self._mesh

    @mesh.setter
    def mesh(self, value):
        self._mesh = value if value is None or isinstance(value, Mesh) else Mesh.from_array(value)
        self._invalidate()

    def _invalidate(self):
        self._cache_key = None
        self._cache = None

    def _mesh_points(self, mesh):
        target = (
            self.mesh
            if mesh is None
            else (mesh if isinstance(mesh, Mesh) else Mesh.from_array(mesh))
        )
        if target is None:
            raise ValueError("a mesh is required for field evaluation")
        return target, Mesh.to_points(target)

    def _cache_token(self, mesh):
        target, points = self._mesh_points(mesh)
        return id(target), points.shape, points.tobytes(), self.rzw.tobytes()

    def _greens(self, mesh=None):
        target, points = self._mesh_points(mesh)
        token = self._cache_token(target)
        if token != self._cache_key:
            self._cache = compute_greens(self.rzw, points)
            self._cache_key = token
        return self._cache

    def gpsi(self, mesh=None):
        return self._greens(mesh)[0].copy()

    def gBR(self, mesh=None):
        return self._greens(mesh)[1].copy()

    def gBZ(self, mesh=None):
        return self._greens(mesh)[2].copy()

    def psi(self, current=None, mesh=None):
        return _common_current(self.current if current is None else current) * self._greens(mesh)[0]

    def BR(self, current=None, mesh=None):
        return _common_current(self.current if current is None else current) * self._greens(mesh)[1]

    def BZ(self, current=None, mesh=None):
        return _common_current(self.current if current is None else current) * self._greens(mesh)[2]

    def translate(self, vector):
        delta = np.asarray(vector, dtype=float)
        if delta.shape != (2,) or not np.all(np.isfinite(delta)):
            raise ValueError("translation must contain finite (R, Z)")
        _replace_points_atomic(self, self.rz_pts + delta)

    def rotate(self, angle, pivot=(0.0, 0.0)):
        angle = float(angle)
        pivot = np.asarray(pivot, dtype=float)
        if not np.isfinite(angle) or pivot.shape != (2,) or not np.all(np.isfinite(pivot)):
            raise ValueError("rotation requires a finite angle and 2-vector pivot")
        _replace_points_atomic(self, rotate(self.rz_pts, angle, pivot))

    @property
    def patch(self):
        return None

    def simplify(self):
        raise NotImplementedError("simplify is not supported for finite weighted filaments")


class ArbitraryPoints(CurrentFilamentSet):
    """Construct finite weighted circular-filament source points.

    Parameters
    ----------
    rz_pts : array_like, shape (N, 2)
        Finite cylindrical ``(R, Z)`` filament centers [m]. Radius must be
        nonnegative.
    **kwargs : object, optional
        Additional inherited constructor entries; see Other Parameters.

    Other Parameters
    ----------------
    current : real scalar, optional
        Common drive current [A]. The default is ``1.0``.
    weights : array_like, shape (N,), optional
        Signed filament weights [dimensionless]. The default is one per point.
    mesh : Mesh or array-like, optional
        Target mesh [m] used when calling field methods without a mesh. The
        default is ``None``.

    Returns
    -------
    source : ArbitraryPoints
        Constructed source exposing geometry and mesh-dependent field methods
        [Object; property units as described].

    Raises
    ------
    ValueError
        If points, current, weights or mesh violate their contracts.
    FloatingPointError
        If a field evaluation is not representable.
    NotImplementedError
        If ``simplify`` is requested.

    See Also
    --------
    scirel.electromagnetism.RectangularCoil : Parameterized rectangular source array.
    scirel.electromagnetism.MagnetRing : Signed permanent-magnet ring approximation.
    scirel.electromagnetism.Device : Ordered collection of source objects.

    Notes
    -----
    Points are ordinary ideal circular filaments in caller order. A positive-
    radius filament is active unless its weight is zero; active source/target
    coincidence is singular. Geometry and weights are mutable and are validated
    again when a field is evaluated.

    Examples
    --------
    >>> from scirel.electromagnetism import ArbitraryPoints
    >>> s=ArbitraryPoints([[1.,0.]],mesh=[[.2,.3]])
    >>> assert s.psi().shape == (1,)
    """

    def __init__(self, rz_pts, **kwargs):
        self._rz_pts = np.asarray(rz_pts, dtype=float)
        if self._rz_pts.ndim != 2 or self._rz_pts.shape[1] != 2:
            raise ValueError("rz_pts must have shape (N, 2)")
        super().__init__(**kwargs)


class RectangularCoil(CurrentFilamentSet):
    """Construct a parameterized rectangular array of circular filaments.

    Parameters
    ----------
    r0 : float, optional
        Centroid radius [m]. Must be finite and nonnegative. The default is
        ``1.0``.
    z0 : float, optional
        Centroid height [m]. Must be finite. The default is ``0.0``.
    nr : int, optional
        Positive radial point count [dimensionless]. The default is ``1``.
    nz : int, optional
        Positive axial point count [dimensionless]. The default is ``1``.
    dr : float, optional
        Positive radial center spacing [m]. The default is ``0.1``.
    dz : float, optional
        Positive axial center spacing [m]. The default is ``0.1``.
    angle : float, default=0.0
        Finite rotation angle [degree] about the centroid. The default is
        ``0.0``.
    **kwargs : object, optional
        Additional inherited constructor entries; see Other Parameters.

    Other Parameters
    ----------------
    current : real scalar, optional
        Common drive current [A]. The default is ``1.0``.
    weights : array_like, shape (nr*nz,), optional
        Signed filament weights [dimensionless]. The default is one per point.
    mesh : Mesh or array-like, optional
        Target mesh [m] stored for later field calls. The default is ``None``.

    Returns
    -------
    source : RectangularCoil
        Constructed source with ordered filament centers, ``area`` [m2] and
        ``current_density`` properties [Object; property units as described].

    Raises
    ------
    ValueError
        If geometry, counts or inherited options are invalid.
    FloatingPointError
        If a field evaluation is not representable.

    See Also
    --------
    scirel.electromagnetism.ArbitraryPoints : Source with arbitrary filament points.
    scirel.electromagnetism.MagnetRing : Signed permanent-magnet ring approximation.
    scirel.electromagnetism.Device : Ordered collection of source objects.

    Notes
    -----
    Points are ordered with radial index outermost and axial index innermost.
    ``angle`` uses the package row-vector rotation convention. Parameterized
    setters rebuild atomically and preserve the previous valid state when
    validation fails; changing a count must preserve the weight cardinality.

    Examples
    --------
    >>> from scirel.electromagnetism import RectangularCoil
    >>> c=RectangularCoil(nr=2)
    >>> assert c.npts == 2
    """

    def __init__(self, r0=1.0, z0=0.0, nr=1, nz=1, dr=0.1, dz=0.1, angle=0.0, **kwargs):
        if (
            isinstance(nr, (bool, np.bool_))
            or isinstance(nz, (bool, np.bool_))
            or int(nr) != nr
            or int(nz) != nz
            or nr < 1
            or nz < 1
        ):
            raise ValueError("nr and nz must be positive integers")
        if not np.all(np.isfinite((r0, z0, dr, dz, angle))) or r0 < 0.0 or dr <= 0.0 or dz <= 0.0:
            raise ValueError("invalid coil geometry")
        self._r0, self._z0 = float(r0), float(z0)
        self._nr, self._nz = int(nr), int(nz)
        self._dr, self._dz, self._angle = float(dr), float(dz), float(angle)
        self._build()
        super().__init__(**kwargs)

    def _build(self):
        radial = np.linspace(
            self._r0 - self._dr * (self._nr - 1) / 2.0,
            self._r0 + self._dr * (self._nr - 1) / 2.0,
            self._nr,
        )
        axial = np.linspace(
            self._z0 - self._dz * (self._nz - 1) / 2.0,
            self._z0 + self._dz * (self._nz - 1) / 2.0,
            self._nz,
        )
        points = np.column_stack((np.repeat(radial, self._nz), np.tile(axial, self._nr)))
        self._rz_pts = (
            points if self._angle == 0.0 else rotate(points, self._angle, (self._r0, self._z0))
        )

    npts = property(lambda self: self._nr * self._nz)
    r0 = property(lambda self: self._r0, lambda self, value: _rebuild_atomic(self, {"_r0": value}))
    z0 = property(lambda self: self._z0, lambda self, value: _rebuild_atomic(self, {"_z0": value}))
    nr = property(lambda self: self._nr, lambda self, value: self._set_count("_nr", value))
    nz = property(lambda self: self._nz, lambda self, value: self._set_count("_nz", value))
    dr = property(lambda self: self._dr, lambda self, value: _rebuild_atomic(self, {"_dr": value}))
    dz = property(lambda self: self._dz, lambda self, value: _rebuild_atomic(self, {"_dz": value}))
    angle = property(
        lambda self: self._angle, lambda self, value: _rebuild_atomic(self, {"_angle": value})
    )

    @property
    def centroid(self):
        return np.array([self.r0, self.z0])

    @centroid.setter
    def centroid(self, value):
        center = np.asarray(value, dtype=float)
        if center.shape != (2,) or not np.all(np.isfinite(center)):
            raise ValueError("centroid must contain finite (R, Z)")
        _rebuild_atomic(self, {"_r0": center[0], "_z0": center[1]})

    @property
    def area(self):
        return self._nr * self._nz * self._dr * self._dz

    @property
    def current_density(self):
        return self.total_current / self.area

    def _set_count(self, name, value):
        if isinstance(value, (bool, np.bool_)) or int(value) != value or int(value) < 1:
            raise ValueError("point count must be a positive integer")
        candidate = int(value)
        other = self._nz if name == "_nr" else self._nr
        if candidate * other != len(self._weights):
            raise ValueError("point count changes must preserve the existing weight cardinality")
        _rebuild_atomic(self, {name: candidate})

    def translate(self, vector):
        delta = np.asarray(vector, dtype=float)
        if delta.shape != (2,) or not np.all(np.isfinite(delta)):
            raise ValueError("translation must contain finite (R, Z)")
        _rebuild_atomic(self, {"_r0": self._r0 + delta[0], "_z0": self._z0 + delta[1]})

    def rotate(self, angle, pivot=(0.0, 0.0)):
        angle = float(angle)
        pivot = np.asarray(pivot, dtype=float)
        if not np.isfinite(angle) or pivot.shape != (2,) or not np.all(np.isfinite(pivot)):
            raise ValueError("rotation requires a finite angle and 2-vector pivot")
        center = rotate(np.array([[self._r0, self._z0]]), angle, pivot)[0]
        _rebuild_atomic(self, {"_r0": center[0], "_z0": center[1], "_angle": self._angle + angle})


class MagnetRing(CurrentFilamentSet):
    """Construct a signed-filament geometry approximation.

    Parameters
    ----------
    r0 : float, optional
        Centroid radius [m]. Must be finite and nonnegative. The default is
        ``1.0``.
    z0 : float, optional
        Centroid height [m]. Must be finite. The default is ``0.0``.
    width : float, optional
        Positive radial cross-section width [m]. The default is ``0.01``.
    height : float, optional
        Positive axial cross-section height [m]. The default is ``0.01``.
    mu_hat : float, optional
        Finite centroid orientation angle [degree]. The default is ``0.0``.
    **kwargs : object, optional
        Additional inherited constructor entries; see Other Parameters.

    Other Parameters
    ----------------
    current : real scalar, optional
        Common drive current [A]. The default is ``1.0``.
    weights : array_like, shape (even N,), optional
        Signed filament weights [dimensionless]. The default is eight ``-1``
        values followed by eight ``+1`` values. An even positive finite vector
        is required.
    mesh : Mesh or array-like, optional
        Target mesh [m] stored for later field calls. The default is ``None``.

    Returns
    -------
    source : MagnetRing
        Constructed signed-filament source with mesh-dependent fields
        [Object; property units as described].

    Raises
    ------
    ValueError
        If geometry or weights violate the declared domain.
    FloatingPointError
        If a field evaluation is not representable.
    NotImplementedError
        If ``simplify`` is requested.

    See Also
    --------
    scirel.electromagnetism.RectangularCoil : Parameterized rectangular source array.
    scirel.electromagnetism.ArbitraryPoints : Source with arbitrary filament points.
    scirel.electromagnetism.Device : Ordered collection of source objects.

    Notes
    -----
    The two radial faces each receive ``N/2`` axial filament points and
    opposite default weights. This is a signed-filament geometry
    approximation, not a material magnetization model. Parameterized setters
    rebuild atomically and preserve the prior valid state when validation
    fails.

    Examples
    --------
    >>> from scirel.electromagnetism import MagnetRing
    >>> r=MagnetRing()
    >>> assert r.npts == 16
    """

    def __init__(self, r0=1.0, z0=0.0, width=0.01, height=0.01, mu_hat=0.0, **kwargs):
        values = np.asarray((r0, z0, width, height, mu_hat), dtype=float)
        if not np.all(np.isfinite(values)) or r0 < 0.0 or width <= 0.0 or height <= 0.0:
            raise ValueError("invalid magnet geometry")
        supplied_weights = kwargs.pop("weights", None)
        if supplied_weights is None:
            supplied_weights = np.r_[-np.ones(8), np.ones(8)]
        weights = np.asarray(supplied_weights, dtype=float)
        if (
            weights.ndim != 1
            or weights.size < 2
            or weights.size % 2
            or not np.all(np.isfinite(weights))
        ):
            raise ValueError("weights must have an even positive length")
        self._r0, self._z0 = float(r0), float(z0)
        self._width, self._height, self._mu_hat = float(width), float(height), float(mu_hat)
        self._weights = weights.copy()
        self._build()
        super().__init__(weights=weights, **kwargs)

    def _build(self):
        half = self._weights.size // 2
        axial = np.linspace(self._z0 - self._height / 2.0, self._z0 + self._height / 2.0, half)
        points = np.vstack(
            (
                np.column_stack((np.full(half, self._r0 - self._width / 2.0), axial)),
                np.column_stack((np.full(half, self._r0 + self._width / 2.0), axial)),
            )
        )
        self._rz_pts = (
            points if self._mu_hat == 0.0 else rotate(points, self._mu_hat, (self._r0, self._z0))
        )

    npts = property(lambda self: len(self._weights))
    r0 = property(lambda self: self._r0, lambda self, value: _rebuild_atomic(self, {"_r0": value}))
    z0 = property(lambda self: self._z0, lambda self, value: _rebuild_atomic(self, {"_z0": value}))
    width = property(
        lambda self: self._width, lambda self, value: _rebuild_atomic(self, {"_width": value})
    )
    height = property(
        lambda self: self._height, lambda self, value: _rebuild_atomic(self, {"_height": value})
    )
    mu_hat = property(
        lambda self: self._mu_hat, lambda self, value: _rebuild_atomic(self, {"_mu_hat": value})
    )

    @property
    def centroid(self):
        return np.array([self.r0, self.z0])

    @centroid.setter
    def centroid(self, value):
        center = np.asarray(value, dtype=float)
        if center.shape != (2,) or not np.all(np.isfinite(center)):
            raise ValueError("centroid must contain finite (R, Z)")
        _rebuild_atomic(self, {"_r0": center[0], "_z0": center[1]})

    def translate(self, vector):
        delta = np.asarray(vector, dtype=float)
        if delta.shape != (2,) or not np.all(np.isfinite(delta)):
            raise ValueError("translation must contain finite (R, Z)")
        _rebuild_atomic(self, {"_r0": self._r0 + delta[0], "_z0": self._z0 + delta[1]})

    def rotate(self, angle, pivot=(0.0, 0.0)):
        angle = float(angle)
        pivot = np.asarray(pivot, dtype=float)
        if not np.isfinite(angle) or pivot.shape != (2,) or not np.all(np.isfinite(pivot)):
            raise ValueError("rotation requires a finite angle and 2-vector pivot")
        center = rotate(np.array([[self._r0, self._z0]]), angle, pivot)[0]
        _rebuild_atomic(self, {"_r0": center[0], "_z0": center[1], "_mu_hat": self._mu_hat + angle})


class Device:
    """Compose ordered circular-filament sources into one field response.

    Parameters
    ----------
    mesh : Mesh or array-like, optional
        Target mesh [m] stored for later field calls. The default is ``None``.
    **kwargs : object, optional
        Attributes assigned in insertion order; see Other Parameters.

    Returns
    -------
    source : Device
        Ordered container whose field methods sum child Green responses
        [Object; property units as described].

    Raises
    ------
    ValueError
        If the mesh is invalid or missing, a current override is invalid, or a
        child field is singular.
    AttributeError
        If the same child source object is registered under a second name.
    FloatingPointError
        If a child Green response is not representable.

    See Also
    --------
    scirel.electromagnetism.ArbitraryPoints : Source with arbitrary filament points.
    scirel.electromagnetism.RectangularCoil : Parameterized rectangular source array.
    scirel.field.solve_multi_coil_vacuum_field : Build a field from caller-supplied coil data.

    Notes
    -----
    Only ``CurrentFilamentSet`` attributes become registered children. Child
    order is assignment order; scalar current overrides apply to every child
    and vector overrides follow that order. A field call requires a configured
    or supplied mesh.

    Examples
    --------
    >>> from scirel.electromagnetism import Device,ArbitraryPoints
    >>> d=Device(mesh=[[.2,.3]])
    >>> d.a=ArbitraryPoints([[1.,0.]])
    >>> assert d.psi().shape == (1,)
    """

    def __init__(self, mesh=None, **kwargs):
        object.__setattr__(
            self,
            "_mesh",
            None if mesh is None else (mesh if isinstance(mesh, Mesh) else Mesh.from_array(mesh)),
        )
        object.__setattr__(self, "_current_sets", {})
        object.__setattr__(self, "_cache_key", None)
        object.__setattr__(self, "_cache", None)
        for name, value in kwargs.items():
            setattr(self, name, value)

    def __setattr__(self, name, value):
        registered = getattr(self, "_current_sets", None)
        if registered is not None and name not in {
            "_mesh",
            "_current_sets",
            "_cache_key",
            "_cache",
        }:
            if isinstance(value, CurrentFilamentSet):
                if any(child is value and key != name for key, child in registered.items()):
                    raise AttributeError("this current set is already registered")
                registered[name] = value
                if self.mesh is not None:
                    value.mesh = self.mesh
            elif name in registered:
                del registered[name]
            self._cache_key = self._cache = None
        object.__setattr__(self, name, value)

    def __delattr__(self, name):
        if name in self._current_sets:
            del self._current_sets[name]
            self._cache_key = self._cache = None
        object.__delattr__(self, name)

    @property
    def mesh(self):
        return self._mesh

    @mesh.setter
    def mesh(self, value):
        target = value if value is None or isinstance(value, Mesh) else Mesh.from_array(value)
        self._mesh = target
        self._cache_key = self._cache = None
        for source in self.current_sets:
            source.mesh = target

    def __iter__(self):
        return iter(self.current_sets)

    @property
    def current_sets(self):
        return list(self._current_sets.values())

    @property
    def current(self):
        return np.array([source.current for source in self.current_sets])

    @property
    def R(self):
        if self.mesh is None:
            raise ValueError("a mesh is required for coordinates")
        return self.mesh.R

    @property
    def Z(self):
        if self.mesh is None:
            raise ValueError("a mesh is required for coordinates")
        return self.mesh.Z

    @property
    def rzw(self):
        return [source.rzw for source in self.current_sets]

    def _matrix(self, name, mesh=None):
        target = self.mesh if mesh is None else mesh
        if target is None:
            raise ValueError("a mesh is required for field evaluation")
        if not self.current_sets:
            return np.zeros((0, len(Mesh.to_points(target))))
        return np.stack([getattr(source, name)(mesh=target) for source in self.current_sets])

    def gpsi(self, mesh=None):
        return self._matrix("gpsi", mesh)

    def gBR(self, mesh=None):
        return self._matrix("gBR", mesh)

    def gBZ(self, mesh=None):
        return self._matrix("gBZ", mesh)

    def _field(self, name, current=None, mesh=None):
        if mesh is None and isinstance(current, Mesh):
            mesh, current = current, None
        elif mesh is None and current is not None and np.asarray(current).ndim >= 2:
            mesh, current = current, None
        values = np.asarray(self.current if current is None else current, dtype=float)
        if values.ndim == 0:
            values = np.full(len(self.current_sets), _common_current(values))
        if values.shape != (len(self.current_sets),) or not np.all(np.isfinite(values)):
            raise ValueError("current must be finite scalar or vector matching current_sets")
        return values @ self._matrix(name, mesh)

    def psi(self, current=None, mesh=None):
        return self._field("gpsi", current, mesh)

    def BR(self, current=None, mesh=None):
        return self._field("gBR", current, mesh)

    def BZ(self, current=None, mesh=None):
        return self._field("gBZ", current, mesh)


__all__ = ["CurrentFilamentSet", "ArbitraryPoints", "RectangularCoil", "MagnetRing", "Device"]
