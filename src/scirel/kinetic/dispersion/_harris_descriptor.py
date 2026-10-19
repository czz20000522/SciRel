"""Local descriptor assembly for a finite rational dispersion relation."""

import numpy as np


def rational_frequency_descriptor(*, constant, poles, residues):
    """Assemble ``A x = omega H x`` for a rational scalar response.

    The represented relation is ``constant + sum(residue/(omega-pole)) = 0``.
    Pole amplitudes occupy the first rows and the final row is the field
    equation. No roots are filtered here; callers retain all finite and
    infinite generalized eigenpairs for separate qualification.
    """

    constant_array = np.asarray(constant)
    pole_array = np.asarray(poles)
    residue_array = np.asarray(residues)
    if (
        constant_array.shape != ()
        or pole_array.ndim != 1
        or pole_array.size == 0
        or residue_array.shape != pole_array.shape
    ):
        raise ValueError(
            "constant must be scalar and poles/residues equal nonempty vectors"
        )
    arrays = (constant_array, pole_array, residue_array)
    if any(array.dtype.kind not in "iufc" for array in arrays):
        raise ValueError("coefficients must be finite numeric values")
    if not all(np.all(np.isfinite(array)) for array in arrays):
        raise ValueError("coefficients must be finite numeric values")

    constant_value = complex(constant_array)
    pole_values = np.asarray(pole_array, dtype=np.complex128)
    residue_values = np.asarray(residue_array, dtype=np.complex128)
    if (
        not np.isfinite(constant_value)
        or not np.isfinite(pole_values).all()
        or not np.isfinite(residue_values).all()
    ):
        raise ValueError("coefficients not representable in complex128")

    pole_count = pole_values.size
    matrix = np.zeros((pole_count + 1, pole_count + 1), dtype=np.complex128)
    inertia = np.zeros_like(matrix)
    matrix[:pole_count, :pole_count] = np.diag(pole_values)
    matrix[:pole_count, pole_count] = -residue_values
    matrix[pole_count, :pole_count] = 1.0
    matrix[pole_count, pole_count] = -constant_value
    inertia[:pole_count, :pole_count] = np.eye(pole_count)
    return {
        "A": matrix,
        "H": inertia,
        "constant": constant_value,
        "poles": pole_values.copy(),
        "residues": residue_values.copy(),
        "state_order": ("auxiliary_pole_amplitudes", "field"),
        "physical_root_filter": "NOT_PERFORMED",
    }
