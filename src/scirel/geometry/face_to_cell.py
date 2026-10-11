# Derived from TORAX: Copyright 2024 DeepMind Technologies Limited.
# Licensed under Apache-2.0; retained license: licenses/torax/LICENSE.
"""Linear interpolation from a one-dimensional face grid to cell centers.

The TORAX relation is ``cell[i] = (face[i] + face[i + 1]) / 2``.  SciRel
keeps the relation and units unchanged while making the array boundary
explicit: a finite real one-dimensional face array with at least two faces is
required.  This leaf does not infer coordinates or apply a geometry measure.

Source: TORAX 8cd1184007c82ff379d118b2ad22753358820fe5,
``torax/_src/geometry/geometry.py:face_to_cell`` (SHA-256
cae147cb1cb4cdb59e0f8a5756592ec768751099d62771008095aa53617faa90).
No canonical duplicate was found: SciRel coordinate interpolation functions
consume actual meshes and cannot replace this coordinate-free midpoint map.
SciRel rejects bool/string/complex/masked input and uses float64 arithmetic.
"""
from __future__ import annotations

import numpy as np

__all__ = ["face_to_cell"]


def face_to_cell(face):
    """Return adjacent face midpoints on the cell grid.

    ``face`` is a finite real numeric one-dimensional array-like with at least
    two entries.  The output is float64, has one fewer entry, and carries the
    same physical units as ``face``.  Shape, dtype, and finiteness failures
    raise :class:`ValueError`; no extrapolation or broadcasting is performed.
    """
    try:
        raw = np.asarray(face)
    except (TypeError, ValueError) as exc:
        raise ValueError("face must be a finite real one-dimensional array") from exc
    if raw.ndim != 1 or raw.size < 2 or raw.dtype.kind not in "iuf":
        raise ValueError("face must be a finite real one-dimensional array of at least two values")
    if np.ma.isMaskedArray(face) or any(isinstance(item, (bool, np.bool_)) for item in np.asarray(face, dtype=object).flat):
        raise ValueError("face must be a finite real one-dimensional array of at least two values")
    values = np.asarray(raw, dtype=np.float64)
    if not np.all(np.isfinite(values)):
        raise ValueError("face must contain only finite values")
    left, right = values[:-1], values[1:]
    # Sum first whenever the sum is representable, preserving subnormal
    # round-to-nearest arithmetic and symmetry. If the sum overflows, each
    # large endpoint can safely be halved without losing subnormal bits.
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        summed = left + right
        result = np.where(np.isfinite(summed), summed * 0.5, left * 0.5 + right * 0.5)
    if not np.all(np.isfinite(result)):
        raise FloatingPointError("face midpoint is not representable")
    return result
