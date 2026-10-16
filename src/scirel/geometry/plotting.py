"""Pleiades affine plotting support, with source in-place/copy contracts.

Source: helpers.py:15-48, frozen D0 be412aa14b77. scale_patches and
transpose_patches mutate transforms; transpose_patches returns None.
get_mirror_patches shallow-copies patches. These are visual support utilities,
not transformations of physical field coordinates or vector components.
D2 composes only the data transform before calling set_transform; including
get_transform would apply intrinsic patch geometry twice. This correction
is witnessed on a Rectangle by independent affine coordinate expectations.
"""
import copy
import numpy as np


def _affine2d(*, matrix=None):
    """Load Matplotlib only when a plotting transform is requested.

    Geometry and numerical helpers remain usable without the optional plotting
    dependency.  Keep the failure at the plotting boundary so callers receive
    an actionable message instead of an import-time failure from
    ``scirel.geometry``.
    """
    try:
        from matplotlib import transforms
    except ModuleNotFoundError as error:
        if error.name == "matplotlib" or error.name.startswith("matplotlib."):
            raise ModuleNotFoundError(
                "scirel.geometry plotting helpers require Matplotlib; "
                "install Matplotlib before calling this function"
            ) from error
        raise
    if matrix is None:
        return transforms.Affine2D()
    return transforms.Affine2D(matrix=matrix)

def scale_patches(patches,scale):
    """scale patches by desired factor."""
    t = _affine2d().scale(scale)
    for p in patches:
        p.set_transform(p.get_data_transform()+t)
    return patches

def get_mirror_patches(patches,axis=0,scale=1):
    """Get mirror image patches across desired axis.
    axis = 0 means reflect across x axis, axis = 1
    means reflect across y axis. Optional scale
    argument can be used as well."""
    x_ref = np.array([[1,0,0],[0,-1,0],[0,0,1]])
    y_ref = np.array([[-1,0,0],[0,1,0],[0,0,1]])
    if axis == 0:
        matrix = x_ref
    else:
        matrix = y_ref
    t = _affine2d(matrix=matrix).scale(scale)
    mirror_patches = []
    for p in patches:
        m_patch = copy.copy(p)
        m_patch.set_transform(m_patch.get_data_transform()+t)
        mirror_patches.append(m_patch)
    return mirror_patches

def transpose_patches(patches):
    """Transpose patches (reflect across line y=x)."""
    transpose = np.array([[0,1,0],[1,0,0],[0,0,1]])
    t = _affine2d(matrix=transpose)
    mirror_patches = []
    for p in patches:
        p.set_transform(p.get_data_transform()+t)
    #return patches



__all__ = ['scale_patches', 'get_mirror_patches', 'transpose_patches']
