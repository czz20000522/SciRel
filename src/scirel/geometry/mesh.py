"""Geometry primitives in cylindrical ``(R, Z)`` coordinates.

The source project used a property named ``theta`` but evaluated ``cos(Z/r)``.
SciRel defines the documented polar angle instead: radians from +Z toward +R,
``atan2(R, Z)``.  The origin has no polar angle and raises ``ValueError``.
"""
from __future__ import annotations

from abc import ABCMeta
from collections.abc import Iterable
import math
from typing import Any

import numpy as np


class Mesh(metaclass=ABCMeta):
    """Base class for a finite set or rectangular grid of ``(R, Z)`` points."""

    def __init__(self) -> None:
        self._R: np.ndarray | None = None
        self._Z: np.ndarray | None = None

    @property
    def R(self) -> np.ndarray:
        return self._R

    @property
    def Z(self) -> np.ndarray:
        return self._Z

    @property
    def r(self) -> np.ndarray:
        return np.hypot(self._R, self._Z)

    @property
    def theta(self) -> np.ndarray:
        radius = self.r
        if np.any(radius == 0):
            raise ValueError("polar angle theta is undefined at the origin")
        return np.arctan2(self._R, self._Z)

    @property
    def shape(self) -> tuple[int, ...]:
        return self._R.shape

    @classmethod
    def to_points(cls, mesh: Any) -> np.ndarray:
        """Return an ``(N, 2)`` floating array in ``(R, Z)`` order.

        A Mesh, an ``N x 2`` array, a ``2 x N`` array, or a pair of matching
        coordinate arrays is accepted.  Structured dimensions are flattened in
        row-major order; the caller owns any reconstruction of the original
        shape.
        """
        if isinstance(mesh, cls):
            return np.column_stack((np.asarray(mesh.R).ravel(), np.asarray(mesh.Z).ravel()))
        arr = np.asarray(mesh) if isinstance(mesh, np.ndarray) else None
        if arr is not None:
            if arr.ndim != 2:
                raise ValueError("mesh array must be two-dimensional")
            if arr.shape[1] == 2:
                return np.asarray(arr, dtype=float)
            if arr.shape[0] == 2:
                return np.column_stack((arr[0].ravel(), arr[1].ravel())).astype(float)
            raise ValueError("mesh array must have shape (N, 2) or (2, N)")
        if isinstance(mesh, Iterable) and not isinstance(mesh, (str, bytes)):
            vals = list(mesh)
            if len(vals) != 2:
                raise ValueError("coordinate iterable must contain R and Z")
            r, z = np.asarray(vals[0]), np.asarray(vals[1])
            if r.shape != z.shape:
                raise ValueError("R and Z coordinate arrays must have equal shape")
            return np.column_stack((r.ravel(), z.ravel())).astype(float)
        raise ValueError("unsupported mesh type")

    @classmethod
    def from_array(cls, mesh: Any) -> "Mesh":
        """Construct a mesh from common array layouts."""
        arr = np.asarray(mesh)
        if arr.ndim == 2:
            if arr.shape[1] == 2:
                return PointsMesh(arr[:, 0], arr[:, 1])
            if arr.shape[0] == 2:
                return PointsMesh(arr[0], arr[1])
            raise ValueError("expected Nx2 points or two coordinate rows")
        if arr.ndim == 3 and arr.shape[0] == 2:
            rpts, zpts = arr[0], arr[1]
            if rpts.ndim != 2 or zpts.shape != rpts.shape:
                raise ValueError("structured coordinates must be matching 2-D arrays")
            r_expected = np.broadcast_to(np.linspace(np.min(rpts), np.max(rpts), rpts.shape[1]), rpts.shape)
            z_expected = np.broadcast_to(np.linspace(np.min(zpts), np.max(zpts), zpts.shape[0])[:, None], zpts.shape)
            if not (np.allclose(rpts, r_expected, rtol=0., atol=0.) and np.allclose(zpts, z_expected, rtol=0., atol=0.)):
                raise ValueError("structured coordinates must form a regular rectangular grid")
            return RectMesh(
                rmin=float(np.min(rpts)), rmax=float(np.max(rpts)), nr=rpts.shape[1],
                zmin=float(np.min(zpts)), zmax=float(np.max(zpts)), nz=rpts.shape[0],
            )
        raise ValueError("expected Nx2, 2xN, or 2xNyxNx coordinates")


class PointsMesh(Mesh):
    """Unstructured points in cylindrical coordinates."""

    def __init__(self, rpts: Iterable[float], zpts: Iterable[float]):
        super().__init__()
        r, z = np.asarray(rpts, dtype=float).squeeze(), np.asarray(zpts, dtype=float).squeeze()
        if r.shape != z.shape:
            raise ValueError("R and Z coordinate arrays must have equal shape")
        if r.ndim == 0:
            r, z = r.reshape(1), z.reshape(1)
        if np.any(~np.isfinite(r)) or np.any(~np.isfinite(z)):
            raise ValueError("mesh coordinates must be finite")
        if np.any(r < 0):
            raise ValueError("cylindrical radius R must be non-negative")
        self._R, self._Z = r, z


class RChord(PointsMesh):
    """Radial chord at fixed ``Z``."""
    def __init__(self, rpts: Iterable[float], z0: float = 0.0):
        super().__init__(rpts, float(z0) * np.ones(len(rpts)))


class ZChord(PointsMesh):
    """Vertical chord at fixed ``R``."""
    def __init__(self, zpts: Iterable[float], r0: float = 0.0):
        super().__init__(float(r0) * np.ones(len(zpts)), zpts)


class SphericalRChord(PointsMesh):
    """Spherical-radius chord at fixed polar angle in degrees."""
    def __init__(self, rpts: Iterable[float], theta0: float = 0.0):
        radius = np.asarray(rpts, dtype=float)
        angle = np.deg2rad(theta0)
        super().__init__(radius * np.sin(angle), radius * np.cos(angle))


class ThetaChord(PointsMesh):
    """Polar-angle chord at fixed spherical radius in degrees."""
    def __init__(self, tpts: Iterable[float], r0: float = 1.0):
        angle = np.deg2rad(np.asarray(tpts, dtype=float))
        super().__init__(float(r0) * np.sin(angle), float(r0) * np.cos(angle))


class RectMesh(Mesh):
    """Regular rectangular ``R-Z`` grid."""

    def __init__(self, rmin=0.0, rmax=1.0, nr=101, zmin=-0.5, zmax=0.5, nz=101):
        super().__init__()
        self._rmin, self._rmax, self._nr = rmin, rmax, nr
        self._zmin, self._zmax, self._nz = zmin, zmax, nz
        self._validate()
        self._set_mesh()

    def _validate(self):
        vals = (self._rmin, self._rmax, self._zmin, self._zmax)
        if any(not np.isfinite(v) for v in vals):
            raise ValueError("mesh bounds must be finite")
        if self._rmin < 0 or self._rmax < self._rmin or self._zmax < self._zmin:
            raise ValueError("invalid rectangular mesh bounds")
        for name in ("_nr", "_nz"):
            value = getattr(self, name)
            if isinstance(value, bool) or int(value) != value or int(value) < 1:
                raise ValueError("mesh point counts must be positive integers")
            setattr(self, name, int(value))

    rmin = property(lambda s: s._rmin, lambda s, v: s._set_param("_rmin", v))
    rmax = property(lambda s: s._rmax, lambda s, v: s._set_param("_rmax", v))
    nr = property(lambda s: s._nr, lambda s, v: s._set_param("_nr", v))
    zmin = property(lambda s: s._zmin, lambda s, v: s._set_param("_zmin", v))
    zmax = property(lambda s: s._zmax, lambda s, v: s._set_param("_zmax", v))
    nz = property(lambda s: s._nz, lambda s, v: s._set_param("_nz", v))

    def _set_param(self, name, value):
        old = getattr(self, name)
        setattr(self, name, value)
        try:
            self._validate()
        except Exception:
            setattr(self, name, old)
            raise
        self._set_mesh()

    def _set_mesh(self):
        self._R, self._Z = np.meshgrid(
            np.linspace(self.rmin, self.rmax, self.nr),
            np.linspace(self.zmin, self.zmax, self.nz),
        )


__all__ = ["Mesh", "PointsMesh", "RChord", "ZChord", "SphericalRChord", "ThetaChord", "RectMesh"]
