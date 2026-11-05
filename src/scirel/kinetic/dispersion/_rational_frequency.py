"""Validated finite-root view of a rational frequency descriptor."""

import numpy as np

from ._harris_descriptor import rational_frequency_descriptor


def solve_rational_frequency(*, constant, poles, residues):
    """Solve a rational relation and expose cancellation diagnostics.

    Exactly coincident poles are combined. A zero combined residue is removed
    exactly, with no tolerance based merging of nearby resonances. The result
    keeps the complete finite generalized spectrum and separately reports the
    roots that satisfy both pencil and rational residual gates.
    """

    descriptor = rational_frequency_descriptor(constant=constant, poles=poles, residues=residues)
    groups = {}
    for pole, residue in zip(descriptor["poles"], descriptor["residues"]):
        groups[pole] = groups.get(pole, 0j) + residue
    kept = [(pole, residue) for pole, residue in groups.items() if residue != 0]
    canceled = [pole for pole, residue in groups.items() if residue == 0]
    if not kept:
        classification = (
            "IDENTICALLY_ZERO" if descriptor["constant"] == 0 else "NONZERO_CONSTANT_NO_ROOTS"
        )
        return {
            "omega": np.empty(0, complex),
            "all_finite": np.empty(0, complex),
            "infinite_count": 0,
            "canceled_poles": np.asarray(canceled),
            "rational_residual": np.empty(0),
            "pencil_residual": np.empty(0),
            "classification": classification,
            "constant": descriptor["constant"],
            "poles": np.empty(0, complex),
            "residues": np.empty(0, complex),
        }

    pole_values = np.asarray([pole for pole, _ in kept])
    residue_values = np.asarray([residue for _, residue in kept])
    descriptor = rational_frequency_descriptor(
        constant=descriptor["constant"],
        poles=pole_values,
        residues=residue_values,
    )

    from scipy.linalg import eig

    homogeneous, vectors = eig(
        descriptor["A"], descriptor["H"], right=True, homogeneous_eigvals=True
    )
    alpha, beta = homogeneous
    finite = beta != 0
    roots = alpha[finite] / beta[finite]
    norms = np.linalg.norm(descriptor["A"], 2) + abs(roots) * np.linalg.norm(descriptor["H"], 2)
    finite_vectors = vectors[:, finite]
    pencil_residual = np.linalg.norm(
        descriptor["A"] @ finite_vectors - descriptor["H"] @ finite_vectors * roots,
        axis=0,
    ) / (norms * np.linalg.norm(finite_vectors, axis=0))
    with np.errstate(divide="ignore", invalid="ignore"):
        terms = residue_values[None, :] / (roots[:, None] - pole_values[None, :])
        rational_residual = abs(descriptor["constant"] + terms.sum(axis=1)) / (
            abs(descriptor["constant"]) + abs(terms).sum(axis=1)
        )

    accepted = (
        np.isfinite(roots)
        & np.isfinite(rational_residual)
        & (rational_residual <= 1e-8)
        & (pencil_residual <= max(1e-11, 128 * len(alpha) * np.finfo(float).eps))
    )
    accepted_roots = roots[accepted]
    accepted_roots = accepted_roots[np.argsort(-accepted_roots.imag, kind="stable")]
    return {
        "omega": accepted_roots,
        "all_finite": roots,
        "accepted": accepted,
        "infinite_count": int((~finite).sum()),
        "canceled_poles": np.asarray(canceled),
        "rational_residual": rational_residual,
        "pencil_residual": pencil_residual,
        "classification": "DESCRIPTOR_WITH_EXPLICIT_ROOT_QUALIFICATION",
        "constant": descriptor["constant"],
        "poles": pole_values,
        "residues": residue_values,
        "alpha": alpha,
        "beta": beta,
        "A": descriptor["A"],
        "H": descriptor["H"],
    }
