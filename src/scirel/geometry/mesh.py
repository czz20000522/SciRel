"""Finite point and rectangular meshes in cylindrical ``(R, Z)`` space."""
from __future__ import annotations

from abc import ABCMeta
from collections.abc import Iterable
from typing import Any

import numpy as np


class Mesh(metaclass=ABCMeta):
    """Base class for mesh-like objects storing matching R and Z arrays."""

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
        if np.any(radius == 0.0):
            raise ValueError("polar angle theta is undefined at the origin")
        return np.arctan2(self._R, self._Z)

    @property
    def shape(self) -> tuple[int, ...]:
        return self._R.shape

    @classmethod
    def to_points(cls, mesh: Any) -> np.ndarray:
        """Convert a mesh representation to an ``(N, 2)`` array."""
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
        """Construct a point or regular rectangular mesh from array layouts."""
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
            expected_r = np.broadcast_to(np.linspace(r_values.min(), r_values.max(), r_values.shape[1]), r_values.shape)
            expected_z = np.broadcast_to(np.linspace(z_values.min(), z_values.max(), z_values.shape[0])[:, None], z_values.shape)
            if not np.array_equal(r_values, expected_r) or not np.array_equal(z_values, expected_z):
                raise ValueError("structured coordinates must form a regular rectangular grid")
            return RectMesh(
                rmin=float(r_values.min()), rmax=float(r_values.max()), nr=r_values.shape[1],
                zmin=float(z_values.min()), zmax=float(z_values.max()), nz=z_values.shape[0],
            )
        raise ValueError("expected Nx2, 2xN, or 2xNyxNx coordinates")


class PointsMesh(Mesh):
    """Unstructured points in cylindrical coordinates."""

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
    """Radial chord at fixed Z."""
    def __init__(self, rpts: Iterable[float], z0: float = 0.0):
        values = np.asarray(rpts)
        super().__init__(rpts, float(z0) * np.ones(len(values)))


class ZChord(PointsMesh):
    """Vertical chord at fixed R."""
    def __init__(self, zpts: Iterable[float], r0: float = 0.0):
        values = np.asarray(zpts)
        super().__init__(float(r0) * np.ones(len(values)), zpts)


class SphericalRChord(PointsMesh):
    """Chord of varying spherical radius at a fixed angle in degrees."""
    def __init__(self, rpts: Iterable[float], theta0: float = 0.0):
        radius = np.asarray(rpts, dtype=float)
        angle = np.deg2rad(theta0)
        super().__init__(radius * np.sin(angle), radius * np.cos(angle))


class ThetaChord(PointsMesh):
    """Chord of varying polar angle at fixed spherical radius in degrees."""
    def __init__(self, tpts: Iterable[float], r0: float = 1.0):
        angle = np.deg2rad(np.asarray(tpts, dtype=float))
        super().__init__(float(r0) * np.sin(angle), float(r0) * np.cos(angle))


class RectMesh(Mesh):
    """Regular rectangular R-Z mesh."""

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
