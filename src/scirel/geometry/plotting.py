"""Optional affine helpers for geometry patches."""
from __future__ import annotations

import copy

import numpy as np

from scirel._optional import import_optional_module

__all__ = ["scale_patches", "get_mirror_patches", "transpose_patches"]


def _affine2d(*, matrix=None):
    transforms = import_optional_module(
        "matplotlib.transforms", extra="plot", feature="scirel.geometry plotting helpers"
    )
    return transforms.Affine2D() if matrix is None else transforms.Affine2D(matrix=matrix)


def scale_patches(patches, scale):
    """Apply a data-coordinate scale to each patch in place and return it."""
    transform = _affine2d().scale(scale)
    for patch in patches:
        patch.set_transform(patch.get_data_transform() + transform)
    return patches


def get_mirror_patches(patches, axis=0, scale=1):
    """Return shallow copies reflected across the selected coordinate axis."""
    reflection = np.array([[1, 0, 0], [0, -1, 0], [0, 0, 1]]) if axis == 0 else np.array(
        [[-1, 0, 0], [0, 1, 0], [0, 0, 1]]
    )
    transform = _affine2d(matrix=reflection).scale(scale)
    mirrored = []
    for patch in patches:
        clone = copy.copy(patch)
        clone.set_transform(clone.get_data_transform() + transform)
        mirrored.append(clone)
    return mirrored


def transpose_patches(patches):
    """Transpose each patch across the line ``Z = R`` in place."""
    transform = _affine2d(matrix=np.array([[0, 1, 0], [1, 0, 0], [0, 0, 1]]))
    for patch in patches:
        patch.set_transform(patch.get_data_transform() + transform)
    # Historical API intentionally returns None.
