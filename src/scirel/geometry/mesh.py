"""Finite point and rectangular meshes in cylindrical ``(R, Z)`` space."""

from __future__ import annotations

from abc import ABCMeta
from collections.abc import Iterable
from typing import Any

import numpy as np


class Mesh(metaclass=ABCMeta):
    """Base class for finite meshes in cylindrical ``(R, Z)`` coordinates.

    Returns
    -------
    mesh : Mesh
        Abstract mesh handle [one object]. Concrete subclasses expose paired
        ``R`` and ``Z`` coordinate arrays [m], derived radius and polar angle
        [m, rad], and the coordinate-array shape [dimensionless].

    Raises
    ------
    ValueError
        Accessing ``theta`` raises when any point is at the origin, where the
        polar angle is undefined. ``to_points`` rejects unsupported array
        layouts and mismatched shapes; only ``from_array`` additionally rejects
        non-rectilinear structured coordinates.

    See Also
    --------
    PointsMesh : Unstructured cylindrical points.
    RectMesh : Regular rectangular R-Z mesh.
    rotate : Rotate planar points about a pivot.

    Notes
    -----
    ``R`` and ``Z`` are stored as matching arrays. The derived radius is
    ``hypot(R, Z)`` and the polar angle is ``arctan2(R, Z)`` in radians.
    Construction and coordinate conversion do not infer a physical boundary,
    topology, or interpolation rule.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry import Mesh, PointsMesh
    >>> mesh = PointsMesh([0.2], [0.3])
    >>> np.testing.assert_allclose(Mesh.to_points(mesh), [[0.2, 0.3]])
    """

    def __init__(self) -> None:
        self._R: np.ndarray | None = None
        self._Z: np.ndarray | None = None

    @property
    def R(self) -> np.ndarray:
        """Return radial coordinate R in metres as a ``float64`` array."""
        return self._R

    @property
    def Z(self) -> np.ndarray:
        """Return axial coordinate Z in metres as a ``float64`` array."""
        return self._Z

    @property
    def r(self) -> np.ndarray:
        """Return cylindrical radius ``hypot(R, Z)`` in metres."""
        return np.hypot(self._R, self._Z)

    @property
    def theta(self) -> np.ndarray:
        """Return polar angle ``arctan2(R, Z)`` in radians.

        Raises
        ------
        ValueError
            If any stored point is at the origin, where ``theta`` is undefined.
        """
        radius = self.r
        if np.any(radius == 0.0):
            raise ValueError("polar angle theta is undefined at the origin")
        return np.arctan2(self._R, self._Z)

    @property
    def shape(self) -> tuple[int, ...]:
        """Return the shape of the stored R and Z coordinate arrays."""
        return self._R.shape

    @classmethod
    def to_points(cls, mesh: Any) -> np.ndarray:
        """Flatten a supported mesh representation into paired R-Z points.

        Parameters
        ----------
        mesh : Mesh or array-like or iterable
            Mesh object, ``(N, 2)`` or ``(2, N)`` coordinate array, or an
            iterable containing separate R and Z coordinate arrays [m].

        Returns
        -------
        points : ndarray of float64, shape (N, 2)
            One ``[R, Z]`` row per point [m]. Array order is row-major when a
            structured mesh is flattened.

        Raises
        ------
        ValueError
            If the value is not supported, an array is not two-dimensional, an
            array has neither two rows nor two columns, or separate R and Z
            arrays have different shapes.

        See Also
        --------
        from_array : Construct a point or rectangular mesh from array layouts.

        Notes
        -----
        This is a representation conversion, not a coordinate transform. It
        does not validate finiteness or require nonnegative radius.

        Examples
        --------
        >>> import numpy as np
        >>> from scirel.geometry import Mesh, PointsMesh
        >>> mesh = PointsMesh([0.2, 0.4], [-0.1, 0.3])
        >>> np.testing.assert_allclose(Mesh.to_points(mesh), [[0.2, -0.1], [0.4, 0.3]])
        """
        if isinstance(mesh, cls):
            return np.column_stack((np.asarray(mesh.R).ravel(), np.asarray(mesh.Z).ravel()))
        if isinstance(mesh, np.ndarray):
            if mesh.ndim != 2:
                raise ValueError("mesh array must be two-dimensional")
            if mesh.shape[1] == 2:
                return np.asarray(mesh, dtype=float)
            if mesh.shape[0] == 2:
                return np.column_stack((mesh[0].ravel(), mesh[1].ravel())).astype(float)
            raise ValueError("mesh array must have shape (N, 2) or (2, N)")
        if isinstance(mesh, Iterable) and not isinstance(mesh, (str, bytes)):
            coordinates = list(mesh)
            if len(coordinates) != 2:
                raise ValueError("coordinate iterable must contain R and Z")
            r, z = np.asarray(coordinates[0]), np.asarray(coordinates[1])
            if r.shape != z.shape:
                raise ValueError("R and Z coordinate arrays must have equal shape")
            return np.column_stack((r.ravel(), z.ravel())).astype(float)
        raise ValueError("unsupported mesh type")

    @classmethod
    def from_array(cls, mesh: Any) -> "Mesh":
        """Construct a mesh from point or structured coordinate arrays.

        Parameters
        ----------
        mesh : array-like
            Either an ``(N, 2)`` / ``(2, N)`` point array, or a ``(2, Nz, Nr)``
            array containing the R and Z coordinate meshes [m]. Structured
            coordinates must form a regular rectangular grid.

        Returns
        -------
        mesh : Mesh
            ``PointsMesh`` for point layouts or ``RectMesh`` for a regular
            structured layout [one mesh object].

        Raises
        ------
        ValueError
            If the rank or leading axis is unsupported, point arrays do not
            have two rows or columns, structured R and Z shapes differ, or the
            structured coordinates do not form a regular rectangular grid.

        See Also
        --------
        to_points : Flatten a mesh to paired R-Z points.
        PointsMesh : Unstructured point mesh.
        RectMesh : Regular rectangular mesh.

        Notes
        -----
        Structured coordinates are checked exactly against uniformly spaced
        broadcast axes. Irregular or distorted structured meshes are rejected
        rather than silently approximated by a rectangle.

        Examples
        --------
        >>> import numpy as np
        >>> from scirel.geometry import Mesh
        >>> mesh = Mesh.from_array(np.array([[0.2, -0.1], [0.5, 0.3], [0.8, 0.0]]))
        >>> np.testing.assert_allclose(Mesh.to_points(mesh), [[0.2, -0.1], [0.5, 0.3], [0.8, 0.0]])
        """
        array = np.asarray(mesh)
        if array.ndim == 2:
            if array.shape[1] == 2:
                return PointsMesh(array[:, 0], array[:, 1])
            if array.shape[0] == 2:
                return PointsMesh(array[0], array[1])
            raise ValueError("expected Nx2 points or two coordinate rows")
        if array.ndim == 3 and array.shape[0] == 2:
            r_values, z_values = array
            if r_values.ndim != 2 or z_values.shape != r_values.shape:
                raise ValueError("structured coordinates must be matching 2-D arrays")
            expected_r = np.broadcast_to(
                np.linspace(r_values.min(), r_values.max(), r_values.shape[1]), r_values.shape
            )
            expected_z = np.broadcast_to(
                np.linspace(z_values.min(), z_values.max(), z_values.shape[0])[:, None],
                z_values.shape,
            )
            if not np.array_equal(r_values, expected_r) or not np.array_equal(z_values, expected_z):
                raise ValueError("structured coordinates must form a regular rectangular grid")
            return RectMesh(
                rmin=float(r_values.min()),
                rmax=float(r_values.max()),
                nr=r_values.shape[1],
                zmin=float(z_values.min()),
                zmax=float(z_values.max()),
                nz=z_values.shape[0],
            )
        raise ValueError("expected Nx2, 2xN, or 2xNyxNx coordinates")


class PointsMesh(Mesh):
    """Points mesh

    Parameters
    ----------
    rpts : Finite float64
        Radial coordinates [m] Shape: ``N``. Equal shape to zpts; R >= 0

    zpts : Finite float64
        Axial coordinates [m] Shape: ``N``. Equal shape to rpts

    Returns
    -------
    mesh : PointsMesh
        Constructed PointsMesh object. Available properties/methods: R: Radial coordinates
        [m], N; Z: Axial coordinates [m], N [Object; property units as described] Shape:
        ``one object``. Properties expose generated coordinates; field methods require
        configured or supplied target mesh

    Raises
    ------
    ValueError
        Raises ValueError for nonfinite coordinates, mismatched shapes, negative radius, malformed point dimensions, or invalid rectangular bounds/counts.

    See Also
    --------
    Mesh : Related geometry callable.
    RChord : Radial chord.
    ZChord : Axial chord.
    RectMesh : Rectangular R-Z mesh.

    Notes
    -----
    Each paired rpts,zpts value defines one point

    **Coordinates.** Cylindrical R-Z

    **Boundary.** R must be nonnegative

    **Preconditions.**

    * Inputs satisfy the documented finite cylindrical coordinate and shape contract

    **Limits.**

    * Negative radius
    * Mismatched shapes

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry import PointsMesh
    >>> mesh = PointsMesh([0.2], [0.3])
    >>> np.testing.assert_allclose(mesh.R, [0.2])
    >>> np.testing.assert_allclose(mesh.Z, [0.3])
    """

    def __init__(self, rpts: Iterable[float], zpts: Iterable[float]):
        super().__init__()
        radius = np.asarray(rpts, dtype=float).squeeze()
        axial = np.asarray(zpts, dtype=float).squeeze()
        if radius.shape != axial.shape:
            raise ValueError("R and Z coordinate arrays must have equal shape")
        if radius.ndim == 0:
            radius, axial = radius.reshape(1), axial.reshape(1)
        if not np.isfinite(radius).all() or not np.isfinite(axial).all():
            raise ValueError("mesh coordinates must be finite")
        if np.any(radius < 0.0):
            raise ValueError("cylindrical radius R must be non-negative")
        self._R, self._Z = radius, axial


class RChord(PointsMesh):
    """Radial chord

    Parameters
    ----------
    rpts : Finite float64
        Radial coordinates [m] Shape: ``N``. R >= 0

    z0 : Finite float64, optional
        Fixed axial coordinate [m] Shape: ``scalar``. Finite Optional; default ``0.0``.

    Returns
    -------
    mesh : RChord
        Constructed RChord object. Available properties/methods: R: Radial coordinates [m],
        N; Z: Axial coordinates [m], N [Object; property units as described] Shape: ``one
        object``. Properties expose generated coordinates; field methods require configured
        or supplied target mesh

    Raises
    ------
    ValueError
        Raises ValueError for nonfinite coordinates, mismatched shapes, negative radius, malformed point dimensions, or invalid rectangular bounds/counts.

    See Also
    --------
    PointsMesh : Points mesh.
    ZChord : Axial chord.
    RectMesh : Rectangular R-Z mesh.

    Notes
    -----
    R coordinates vary while Z is constant

    **Coordinates.** Cylindrical R-Z

    **Boundary.** R nonnegative

    **Preconditions.**

    * Inputs satisfy the documented finite cylindrical coordinate and shape contract

    **Limits.**

    * Negative radius

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry import RChord
    >>> mesh = RChord([0.2, 0.5], 0.3)
    >>> np.testing.assert_allclose(mesh.R, [0.2, 0.5])
    >>> np.testing.assert_allclose(mesh.Z, [0.3, 0.3])
    """

    def __init__(self, rpts: Iterable[float], z0: float = 0.0):
        values = np.asarray(rpts)
        super().__init__(rpts, float(z0) * np.ones(len(values)))


class ZChord(PointsMesh):
    """Axial chord

    Parameters
    ----------
    zpts : Finite float64
        Axial coordinates [m] Shape: ``N``. Finite

    r0 : Finite float64, optional
        Fixed radial coordinate [m] Shape: ``scalar``. R >= 0 Optional; default ``0.0``.

    Returns
    -------
    mesh : ZChord
        Constructed ZChord object. Available properties/methods: R: Radial coordinates [m],
        N; Z: Axial coordinates [m], N [Object; property units as described] Shape: ``one
        object``. Properties expose generated coordinates; field methods require configured
        or supplied target mesh

    Raises
    ------
    ValueError
        Raises ValueError for nonfinite coordinates, mismatched shapes, negative radius, malformed point dimensions, or invalid rectangular bounds/counts.

    See Also
    --------
    RChord : Radial chord.
    SphericalRChord : Spherical radial chord.
    ThetaChord : Polar-angle chord.

    Notes
    -----
    Z coordinates vary while R is constant

    **Coordinates.** Cylindrical R-Z

    **Boundary.** R nonnegative

    **Preconditions.**

    * Inputs satisfy the documented finite cylindrical coordinate and shape contract

    **Limits.**

    * Negative radius

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry import ZChord
    >>> mesh = ZChord([-0.2, 0.4], 0.3)
    >>> np.testing.assert_allclose(mesh.R, [0.3, 0.3])
    >>> np.testing.assert_allclose(mesh.Z, [-0.2, 0.4])
    """

    def __init__(self, zpts: Iterable[float], r0: float = 0.0):
        values = np.asarray(zpts)
        super().__init__(float(r0) * np.ones(len(values)), zpts)


class SphericalRChord(PointsMesh):
    """Spherical radial chord

    Parameters
    ----------
    rpts : Finite float64
        Spherical radius [m] Shape: ``N``. Nonnegative radius

    theta0 : Finite float64, optional
        Fixed polar angle [degree] Shape: ``scalar``. Finite degrees Optional; default
        ``0.0``.

    Returns
    -------
    mesh : SphericalRChord
        Constructed SphericalRChord object. Available properties/methods: R: Cylindrical
        radius [m], N; Z: Axial coordinate [m], N [Object; property units as described]
        Shape: ``one object``. Properties expose generated coordinates; field methods
        require configured or supplied target mesh

    Raises
    ------
    ValueError
        Raises ValueError for nonfinite coordinates, mismatched shapes, negative radius, malformed point dimensions, or invalid rectangular bounds/counts.

    See Also
    --------
    ThetaChord : Polar-angle chord.
    PointsMesh : Points mesh.
    ZChord : Axial chord.

    Notes
    -----
    R=r sin(theta), Z=r cos(theta)

    **Coordinates.** Cylindrical storage derived from spherical inputs

    **Boundary.** Angles are degrees

    **Preconditions.**

    * Inputs satisfy the documented finite cylindrical coordinate and shape contract
    * Generated cylindrical R must be nonnegative; use nonnegative spherical radii and
      degree angles in the usual 0..180 polar domain.

    **Limits.**

    * Negative radius

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry import SphericalRChord
    >>> mesh = SphericalRChord([1.0], 90.0)
    >>> np.testing.assert_allclose(mesh.R, [1.0])
    >>> np.testing.assert_allclose(mesh.Z, [0.0], atol=1e-15)
    """

    def __init__(self, rpts: Iterable[float], theta0: float = 0.0):
        radius = np.asarray(rpts, dtype=float)
        angle = np.deg2rad(theta0)
        super().__init__(radius * np.sin(angle), radius * np.cos(angle))


class ThetaChord(PointsMesh):
    """Polar-angle chord

    Parameters
    ----------
    tpts : Finite float64
        Polar angles [degree] Shape: ``N``. Finite degrees

    r0 : Finite float64, optional
        Fixed spherical radius [m] Shape: ``scalar``. Finite radius Optional; default
        ``1.0``.

    Returns
    -------
    mesh : ThetaChord
        Constructed ThetaChord object. Available properties/methods: R: Cylindrical radius
        [m], N; Z: Axial coordinate [m], N [Object; property units as described] Shape:
        ``one object``. Properties expose generated coordinates; field methods require
        configured or supplied target mesh

    Raises
    ------
    ValueError
        Raises ValueError for nonfinite coordinates, mismatched shapes, negative radius, malformed point dimensions, or invalid rectangular bounds/counts.

    See Also
    --------
    SphericalRChord : Spherical radial chord.
    PointsMesh : Points mesh.
    ZChord : Axial chord.

    Notes
    -----
    R=r0 sin(theta), Z=r0 cos(theta)

    **Coordinates.** Cylindrical storage derived from angle inputs

    **Boundary.** Angles are degrees

    **Preconditions.**

    * Inputs satisfy the documented finite cylindrical coordinate and shape contract
    * Generated cylindrical R must be nonnegative; use nonnegative spherical radii and
      degree angles in the usual 0..180 polar domain.

    **Limits.**

    * Negative fixed radius

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry import ThetaChord
    >>> mesh = ThetaChord([0.0, 90.0])
    >>> np.testing.assert_allclose(mesh.R, [0.0, 1.0], atol=1e-15)
    >>> np.testing.assert_allclose(mesh.Z, [1.0, 0.0], atol=1e-15)
    """

    def __init__(self, tpts: Iterable[float], r0: float = 1.0):
        angle = np.deg2rad(np.asarray(tpts, dtype=float))
        super().__init__(float(r0) * np.sin(angle), float(r0) * np.cos(angle))


class RectMesh(Mesh):
    """Rectangular R-Z mesh

    Parameters
    ----------
    rmin : Finite float64, optional
        Minimum radius [m] Shape: ``scalar``. R >= 0 Optional; default ``0.0``.

    rmax : Finite float64, optional
        Maximum radius [m] Shape: ``scalar``. rmax >= rmin Optional; default ``1.0``.

    nr : int, optional
        Radial count [dimensionless] Shape: ``scalar``. Positive integer Optional; default
        ``101``.

    zmin : Finite float64, optional
        Minimum axial coordinate [m] Shape: ``scalar``. zmin <= zmax Optional; default
        ``-0.5``.

    zmax : Finite float64, optional
        Maximum axial coordinate [m] Shape: ``scalar``. zmax >= zmin Optional; default
        ``0.5``.

    nz : int, optional
        Axial count [dimensionless] Shape: ``scalar``. Positive integer Optional; default
        ``101``.

    Returns
    -------
    mesh : RectMesh
        Constructed RectMesh object. Available properties/methods: R: Radial mesh [m],
        (nz,nr); Z: Axial mesh [m], (nz,nr) [Object; property units as described] Shape:
        ``one object``. Properties expose generated coordinates; field methods require
        configured or supplied target mesh

    Raises
    ------
    ValueError
        Raises ValueError for nonfinite coordinates, mismatched shapes, negative radius, malformed point dimensions, or invalid rectangular bounds/counts.

    See Also
    --------
    PointsMesh : Points mesh.
    RChord : Radial chord.
    ZChord : Axial chord.

    Notes
    -----
    meshgrid over independent R and Z bounds

    **Coordinates.** Cylindrical R-Z

    **Boundary.** Finite ordered bounds and positive integer counts

    **Preconditions.**

    * Inputs satisfy the documented finite cylindrical coordinate and shape contract

    **Limits.**

    * Distorted structured coordinates
    * Negative radius
    * Noninteger counts

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry import RectMesh
    >>> mesh = RectMesh(nr=2, nz=2)
    >>> assert mesh.R.shape == (2, 2)
    >>> assert mesh.Z.shape == (2, 2)
    >>> np.testing.assert_allclose(mesh.R[0], [0.0, 1.0])
    >>> np.testing.assert_allclose(mesh.Z[:, 0], [-0.5, 0.5])
    """

    def __init__(self, rmin=0.0, rmax=1.0, nr=101, zmin=-0.5, zmax=0.5, nz=101):
        super().__init__()
        self._rmin, self._rmax, self._nr = rmin, rmax, nr
        self._zmin, self._zmax, self._nz = zmin, zmax, nz
        self._validate()
        self._set_mesh()

    def _validate(self):
        bounds = (self._rmin, self._rmax, self._zmin, self._zmax)
        if not np.isfinite(bounds).all():
            raise ValueError("mesh bounds must be finite")
        if self._rmin < 0 or self._rmax < self._rmin or self._zmax < self._zmin:
            raise ValueError("invalid rectangular mesh bounds")
        for name in ("_nr", "_nz"):
            value = getattr(self, name)
            if isinstance(value, (bool, np.bool_)) or int(value) != value or int(value) < 1:
                raise ValueError("mesh point counts must be positive integers")
            setattr(self, name, int(value))

    rmin = property(lambda self: self._rmin, lambda self, value: self._set_param("_rmin", value))
    rmax = property(lambda self: self._rmax, lambda self, value: self._set_param("_rmax", value))
    nr = property(lambda self: self._nr, lambda self, value: self._set_param("_nr", value))
    zmin = property(lambda self: self._zmin, lambda self, value: self._set_param("_zmin", value))
    zmax = property(lambda self: self._zmax, lambda self, value: self._set_param("_zmax", value))
    nz = property(lambda self: self._nz, lambda self, value: self._set_param("_nz", value))

    def _set_param(self, name, value):
        previous = getattr(self, name)
        setattr(self, name, value)
        try:
            self._validate()
        except Exception:
            setattr(self, name, previous)
            raise
        self._set_mesh()

    def _set_mesh(self):
        self._R, self._Z = np.meshgrid(
            np.linspace(self.rmin, self.rmax, self.nr),
            np.linspace(self.zmin, self.zmax, self.nz),
        )


__all__ = ["Mesh", "PointsMesh", "RChord", "ZChord", "SphericalRChord", "ThetaChord", "RectMesh"]
