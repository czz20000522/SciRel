"""Finite-volume cell values and boundary constraints for one coordinate."""

from dataclasses import dataclass

import numpy as np


__all__ = ["CellVariable"]


def finite_array(value, name, shape=None):
    """Return a writable float64 copy after strict real-array validation."""

    if np.ma.isMaskedArray(value) and np.any(np.ma.getmaskarray(value)):
        raise ValueError(f"{name} must not be masked")
    object_values = np.asarray(value, dtype=object)
    if any(isinstance(item, (bool, np.bool_)) for item in object_values.flat):
        raise TypeError(f"{name} must be real numeric, not boolean")
    raw = np.asarray(value)
    if raw.dtype.kind not in "iuf":
        raise TypeError(f"{name} must be real numeric")
    result = np.array(raw, dtype=np.float64, copy=True)
    if shape is not None and result.shape != shape:
        raise ValueError(f"{name} must have shape {shape}")
    if not np.isfinite(result).all():
        raise ValueError(f"{name} must be finite")
    return result


def finite_scalar(value, name):
    """Validate a scalar through the common finite-array path."""

    return float(finite_array(value, name, ()).item())


def checked(value):
    """Raise when a finite-volume operation leaves the finite range."""

    if not np.isfinite(value).all():
        raise FloatingPointError("nonfinite finite-volume result")
    return value


@dataclass(frozen=True)
class CellVariable:
    """One-dimensional point samples with explicit endpoint constraints."""

    value: object
    face_centers: object
    left_face_constraint: object = None
    right_face_constraint: object = None
    left_face_grad_constraint: object = 0.0
    right_face_grad_constraint: object = 0.0

    def __post_init__(self):
        values = finite_array(self.value, "value")
        if values.ndim != 1 or values.size < 2:
            raise ValueError("value must be one-dimensional with at least two cells")
        faces = finite_array(self.face_centers, "face_centers", (values.size + 1,))
        with np.errstate(over="ignore", invalid="ignore"):
            widths = np.diff(faces)
            centers = faces[:-1] + widths / 2.0
        if (
            not np.isfinite(widths).all()
            or np.any(widths <= 0.0)
            or not np.isfinite(centers).all()
            or np.any(np.diff(centers) <= 0.0)
        ):
            raise ValueError("face and midpoint spacings must be finite and positive")

        values.setflags(write=False)
        faces.setflags(write=False)
        object.__setattr__(self, "value", values)
        object.__setattr__(self, "face_centers", faces)

        for side in ("left", "right"):
            value_name = f"{side}_face_constraint"
            gradient_name = f"{side}_face_grad_constraint"
            boundary_value = getattr(self, value_name)
            boundary_gradient = getattr(self, gradient_name)
            if (boundary_value is None) == (boundary_gradient is None):
                raise ValueError("exactly one boundary value or gradient is required at each end")
            if boundary_value is not None:
                object.__setattr__(self, value_name, finite_scalar(boundary_value, value_name))
            if boundary_gradient is not None:
                object.__setattr__(
                    self, gradient_name, finite_scalar(boundary_gradient, gradient_name)
                )

    @property
    def cell_widths(self):
        return np.diff(self.face_centers)

    @property
    def cell_centers(self):
        return self.face_centers[:-1] + self.cell_widths / 2.0

    @property
    def cell_spacings(self):
        return np.diff(self.cell_centers)

    @property
    def left_face_value(self):
        if self.left_face_constraint is not None:
            return self.left_face_constraint
        return self.value[0] - self.left_face_grad_constraint * self.cell_widths[0] / 2.0

    @property
    def right_face_value(self):
        if self.right_face_constraint is not None:
            return self.right_face_constraint
        return self.value[-1] + self.right_face_grad_constraint * self.cell_widths[-1] / 2.0

    def face_value(self):
        """Interpolate values to faces, using the declared endpoint data."""

        centers = self.cell_centers
        weights = (self.face_centers[1:-1] - centers[:-1]) / self.cell_spacings
        with np.errstate(all="ignore"):
            internal = (1.0 - weights) * self.value[:-1] + weights * self.value[1:]
            return checked(
                np.concatenate(([self.left_face_value], internal, [self.right_face_value]))
            )

    def face_grad(self, *, two_point_mask=None):
        """Return ``du/dx`` at every face using local quadratic stencils."""

        n = self.value.size
        faces = self.face_centers
        centers = self.cell_centers
        gradients = np.empty(n + 1, dtype=float)

        for index in range(1, n):
            if index < n - 1:
                coordinates = centers[index - 1 : index + 2] - faces[index]
                samples = self.value[index - 1 : index + 2]
            elif self.right_face_constraint is None:
                widths = self.cell_widths[-2:]
                scaled_left, scaled_right = widths / np.max(widths)
                weight = (scaled_left - scaled_right) / (scaled_left + 3.0 * scaled_right)
                secant = (self.value[-1] - self.value[-2]) / self.cell_spacings[-1]
                gradients[index] = (
                    1.0 - weight
                ) * secant + weight * self.right_face_grad_constraint
                continue
            else:
                coordinates = np.concatenate(
                    (centers[-2:] - faces[index], [faces[-1] - faces[index]])
                )
                samples = np.concatenate((self.value[-2:], [self.right_face_constraint]))

            left, middle, right = coordinates
            first = (middle + right) / (
                -left * left + left * middle + left * right - middle * right
            )
            last = (-left - middle) / (
                left * middle - left * right - middle * right + right * right
            )
            gradients[index] = first * (samples[0] - samples[1]) + last * (samples[2] - samples[1])

        if two_point_mask is not None:
            mask = np.asarray(two_point_mask)
            if mask.dtype.kind != "b" or mask.shape != (n + 1,):
                raise ValueError("two_point_mask must be boolean N+1")
            gradients[1:-1] = np.where(
                mask[1:-1], np.diff(self.value) / self.cell_spacings, gradients[1:-1]
            )

        if self.left_face_constraint is not None:
            gradients[0] = (self.value[0] - self.left_face_constraint) / (self.cell_widths[0] / 2.0)
        else:
            gradients[0] = self.left_face_grad_constraint
        if self.right_face_constraint is not None:
            gradients[-1] = (self.right_face_constraint - self.value[-1]) / (
                self.cell_widths[-1] / 2.0
            )
        else:
            gradients[-1] = self.right_face_grad_constraint
        return checked(gradients)

    def grad(self):
        """Return the finite-volume gradient from interpolated face values."""

        return checked(np.diff(self.face_value()) / self.cell_widths)
