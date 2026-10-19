"""Nonnegative conservative remapping of cylindrical velocity distributions.

The default ``correct=1`` is a scientific successor to the saved KN1DPy
``interp_fvrvxx`` handoff. It retains cell-overlap interpolation and the
stateless two-velocity/one-spatial-axis interface, but replaces the defective
AN/BN correction. Historical source parity is not claimed for the correction.

Discrete cell masses use ``pi*(r_right**2-r_left**2)*dvx``. Source density,
axial momentum density and squared-speed energy density are converted to
mesh_b normalization and linearly interpolated in x BEFORE division by
density. This preserves extensive moments when density varies spatially.
At each nonzero-density slice, a relative-entropy projection of overlap cell
probabilities enforces those three moments and nonnegativity. Its reference
mixes 1e-12 cell-volume probability into the normalized overlap; this opens
zero-overlap cells, without changing target moments or clipping the result.
Targets on a convex-hull face use only nodes on that face. Damped Newton
updates solve the dual with gradient equal to the moment residual and
covariance Hessian; max_correction_iterations bounds updates per slice.

A finite destination grid cannot represent every source moment. Targets
outside conv{(vx_j, vr_i**2+vx_j**2)} raise InfeasibleMomentsError with a
separating-inequality diagnostic. A numerically unresolved feasible target
raises MomentCorrectionConvergenceError; neither failure returns a partial
result. Face classification uses 64 binary64 eps in scaled geometry; every
returned corrected slice must satisfy all three scaled moments within
128 eps. These are roundoff checks, not physical target relaxation.

Zero density returns zero. Identical velocity meshes/normalizations use exact
convex spatial interpolation; identical spatial nodes therefore give identity.
Spatial nodes outside the source interval are zero-filled. Nonuniform grids,
nonzero drift and unequal positive Tnorm are supported when target moments
are realizable and the binary64 computation is representable. The retained
``correct=0`` algebraic compatibility branch includes its historical density
rescale and has no three-moment or nonnegative-physical-distribution contract.
``do_warn`` emits the historical boundary warnings without changing values.

This validates a finite-grid mathematical transfer, not atomic physics or a
whole KN1D project. The prior strict D1 qualification remains withdrawn;
original failure/replay evidence and pending redistribution licensing remain.
"""
from __future__ import annotations

import numpy as np

from .cylindrical_velocity_quadrature import make_cylindrical_velocity_quadrature

__all__ = [
    "InfeasibleMomentsError",
    "MomentCorrectionConvergenceError",
    "interp_distribution_across_mesh",
]


def _make_dvr_dvx(vr, vx):
    """Adapt the existing source-equivalent quadrature to saved field order."""
    weights = make_cylindrical_velocity_quadrature(vr=vr, vx=vx)
    return (
        weights["radial_measure"], weights["radial_four_pi_measure"],
        weights["dvx"], weights["vr_left"], weights["vr_right"],
        weights["vx_left"], weights["vx_right"], weights["volume"],
        weights["inv_dvx_ghost"], weights["vx_over_dvx_ghost"],
        weights["vr_over_dvr_ghost"], weights["speed_squared"],
        weights["positive_vx_first_index"], weights["positive_vx_last_index"],
        weights["negative_vx_first_index"], weights["negative_vx_last_index"],
    )


def _locate(table, value):
    """Reproduce KN1DPy.locate (searchsorted-based index location).

    Returns a scalar int for a scalar ``value`` (matching the source, whose
    ``len(indices) == 1`` branch collapses to a scalar), so that downstream
    scalar arithmetic like ``wxa[k] = ... + ...*f`` stays scalar.
    """
    table = np.asarray(table)
    value = np.atleast_1d(value)
    asc = table[0] <= table[-1]
    if not asc:
        table = table[::-1]
    indices = np.searchsorted(table, value, side='right' if asc else 'left') - 1
    if not asc:
        indices = len(table) - indices - 1
    indices[value < table[0]] = -1
    indices[value >= table[-1]] = len(table) - 1
    if len(indices) == 1:
        indices = indices[0]
    return indices


def _real_array(arr, name):
    try:
        if isinstance(arr, (list, tuple)) and any(
            isinstance(item, (bool, np.bool_))
            for item in np.asarray(arr, dtype=object).flat
        ):
            raise ValueError
        raw = np.asarray(arr)
        if raw.dtype.kind not in "iuf":
            raise ValueError
        return np.asarray(raw, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must contain real numeric values") from exc


def _as_1d(arr, name):
    a = _real_array(arr, name)
    if a.ndim != 1 or a.size == 0:
        raise ValueError(f"{name} must be a non-empty one-dimensional array")
    if not np.all(np.isfinite(a)):
        raise ValueError(f"{name} must be finite")
    return a


def _as_3d(arr, name, nvr, nvx, nx):
    a = _real_array(arr, name)
    if a.ndim != 3 or a.shape != (nvr, nvx, nx):
        raise ValueError(f"{name} must have shape ({nvr},{nvx},{nx})")
    if not np.all(np.isfinite(a)):
        raise ValueError(f"{name} must be finite")
    return a


def _real_scalar(value, name):
    array = _real_array(value, name)
    if array.ndim != 0:
        raise ValueError(f"{name} must be a real scalar")
    return float(array)


class InfeasibleMomentsError(ValueError):
    """No nonnegative distribution on the destination nodes has these moments.

    ``diagnostics`` contains the target spatial index, normalized requested
    mean velocity/energy and the separating convex-hull inequality residual.
    """

    def __init__(self, message, diagnostics):
        super().__init__(message)
        self.diagnostics = diagnostics


class MomentCorrectionConvergenceError(ValueError):
    """A feasible moment projection could not meet its numerical postcondition."""


def _positive_moment_projection(raw, volume, vx, vr, density, mean_v,
                                mean_e, max_iterations, spatial_index):
    """Relative-entropy projection of cell probabilities, with exact targets.

    The feasible moments form conv{(vx_j, vr_i**2+vx_j**2)}. Its lower
    boundary is the polygonal interpolation of vr_min**2+vx_j**2, its upper
    boundary joins the two extreme-vx points at vr_max, and its sides bound
    vx. Boundary targets restrict the support to the corresponding faces.
    On that support minimize sum p*log(p/q), sum p=1, E_p[(v,e)]=target.
    The dual has gradient = moment residual and Hessian = covariance.
    No negative-cell clipping, moment relaxation or partial result is used.
    """
    eps = np.finfo(float).eps
    vscale = max(abs(vx[0]), abs(vx[-1]))
    with np.errstate(over="ignore", invalid="ignore"):
        energies = vr[:, None]**2 + vx[None, :]**2
        escale = np.max(energies)
        features = np.column_stack((
            np.broadcast_to(vx / vscale, raw.shape).ravel(),
            (energies / escale).ravel(),
        ))
        target = np.array([mean_v / vscale, mean_e / escale])
        slopes = vx[:-1] + vx[1:]
        lower_intercepts = vr[0]**2 - vx[:-1]*vx[1:]
        upper_slope = vx[0] + vx[-1]
        upper_intercept = vr[-1]**2 - vx[0]*vx[-1]
        normals = np.vstack((
            [1., 0.], [-1., 0.],
            np.column_stack((-slopes * vscale / escale, np.ones(slopes.size))),
            [upper_slope * vscale / escale, -1.],
        ))
        offsets = np.concatenate(([-vx[0]/vscale, vx[-1]/vscale],
                                  -lower_intercepts / escale,
                                  [upper_intercept / escale]))
    if not all(np.all(np.isfinite(a)) for a in
               (features, target, normals, offsets)):
        raise ValueError(f"moment features are not representable at x_b index {spatial_index}")
    norm = np.linalg.norm(normals, axis=1)
    normals, offsets = normals/norm[:, None], offsets/norm
    margins = normals @ target + offsets
    geometry_tolerance = 64 * eps
    if np.min(margins) < -geometry_tolerance:
        raise InfeasibleMomentsError(
            f"target moments are outside the destination convex hull at x_b index {spatial_index}",
            {"x_b_index": spatial_index, "mean_v_destination_units": float(mean_v),
             "mean_energy_destination_units": float(mean_e),
             "maximum_node_energy": float(escale),
             "separating_inequality": int(np.argmin(margins)),
             "scaled_margin": float(np.min(margins))},
        )
    # Equality on a hull face forces all probability off its exterior nodes.
    boundary = margins <= geometry_tolerance
    support = np.ones(raw.size, dtype=bool)
    if np.any(boundary):
        on_faces = features @ normals[boundary].T + offsets[boundary]
        support = np.all(np.abs(on_faces) <= 128 * eps, axis=1)
    if not np.any(support):
        raise MomentCorrectionConvergenceError(
            f"cannot resolve destination hull face at x_b index {spatial_index}")

    with np.errstate(over="ignore", invalid="ignore"):
        seed = (raw * volume).ravel()
        seed_total = np.sum(seed)
    if not np.isfinite(seed_total) or np.any(seed < 0):
        raise ValueError(f"overlap cell masses are invalid at x_b index {spatial_index}")
    if seed_total > 0:
        original = seed / seed_total
        if np.max(np.abs(original @ features - target)) <= 16 * eps:
            result = (density * original).reshape(raw.shape) / volume
            if np.all(np.isfinite(result)):
                return result
    else:
        original = np.zeros_like(seed)

    # Explicit positive reference measure (NOT a relaxed target): mixing
    # 1e-12 cell-volume probability opens cells with zero overlap. The final
    # constrained density, momentum and energy are unchanged by this choice.
    reference_volume = volume.ravel()[support]
    reference_volume = reference_volume / np.sum(reference_volume)
    q = original[support]
    if np.sum(q) > 0:
        q = q / np.sum(q)
        q = (1 - 1e-12) * q + 1e-12 * reference_volume
    else:
        q = reference_volume
    centered = features[support] - target
    # A boundary edge/vertex has only one/zero independent moment direction.
    _, singular, vh = np.linalg.svd(centered, full_matrices=False)
    rank = int(np.count_nonzero(singular > 128 * eps * max(1., singular[0])))
    basis = vh[:rank].T
    x = centered @ basis
    theta = np.zeros(rank)
    logq = np.log(q)
    probability = q
    # Keep the entropy backend out of import-time and rejected-input paths.
    # SciPy remains a declared runtime dependency for this numerical branch;
    # load it only once the public input contract and finite overlap state are
    # established.
    from scipy.special import logsumexp

    for iteration in range(max_iterations + 1):
        z = logq + x @ theta
        value = logsumexp(z)
        probability = np.exp(z - value)
        residual = probability @ centered
        if np.max(np.abs(residual)) <= 32 * eps:
            break
        if iteration == max_iterations:
            raise MomentCorrectionConvergenceError(
                f"moment correction did not converge within {max_iterations} iterations at x_b index {spatial_index}")
        gradient = probability @ x
        deviation = x - gradient
        hessian = (deviation.T * probability) @ deviation
        try:
            step = np.linalg.solve(hessian, gradient)
        except np.linalg.LinAlgError as exc:
            raise MomentCorrectionConvergenceError(
                f"moment correction covariance is singular at x_b index {spatial_index}") from exc
        slope = float(gradient @ step)
        if not np.isfinite(slope) or slope <= 0:
            raise MomentCorrectionConvergenceError(
                f"moment correction has no descent direction at x_b index {spatial_index}")
        damping = 1.
        for _ in range(64):
            trial = theta - damping * step
            trial_z = logq + x @ trial
            trial_value = logsumexp(trial_z)
            trial_probability = np.exp(trial_z - trial_value)
            # The second criterion avoids objective cancellation near a root;
            # it still requires a strict reduction of the actual moment error.
            if (trial_value <= value - 1e-4*damping*slope or
                    np.linalg.norm(trial_probability @ x) <
                    (1 - 1e-4*damping)*np.linalg.norm(gradient)):
                theta = trial
                break
            damping *= .5
        else:
            raise MomentCorrectionConvergenceError(
                f"moment correction line search failed at x_b index {spatial_index}")
    result_mass = np.zeros(raw.size)
    result_mass[support] = density * probability
    result = result_mass.reshape(raw.shape) / volume
    # Postcondition is checked on the actual returned distribution, after
    # conversion back from cell probabilities (including any underflow).
    actual = (result * volume).ravel()
    actual_density = np.sum(actual)
    actual_mean = (actual / density) @ features
    if (not np.all(np.isfinite(result)) or np.any(result < 0)
            or abs(actual_density / density - 1) > 128 * eps
            or np.max(np.abs(actual_mean - target)) > 128 * eps):
        raise MomentCorrectionConvergenceError(
            f"moment correction postcondition failed at x_b index {spatial_index}")
    return result


def interp_distribution_across_mesh(
    fa,
    vr_a,
    vx_a,
    x_a,
    Tnorm_a,
    vr_b,
    vx_b,
    x_b,
    Tnorm_b,
    correct=1,
    do_warn=None,
    max_correction_iterations=1000,
):
    """Remap a cylindrical distribution while preserving three discrete moments.

    Parameters
    ----------
    fa : array_like, shape (nvra, nvxa, nxa)
        Finite real distribution; nonnegative when ``correct=1``.
    vr_a, vx_a, x_a : array_like
        Source radial velocity, axial velocity and spatial nodes. Each axis
        is finite, strictly increasing and has at least two nodes; radial
        nodes are nonnegative and axial nodes include both signs.
    Tnorm_a : float
        Positive finite source normalization temperature (eV).
    vr_b, vx_b, x_b : array_like
        Destination axes, subject to the same node contracts and the retained
        velocity/spatial overlap requirements. Outside-source x nodes get zero.
    Tnorm_b : float
        Positive finite destination normalization temperature (eV).
    correct : {0, 1}, optional
        Default 1 applies nonnegative relative-entropy moment projection.
        0 retains the historical algebraic interpolant and density rescale,
        without a physical positivity or three-moment conservation guarantee.
    do_warn : int or None, optional
        Historical boundary-warning threshold; it does not change output.
    max_correction_iterations : int, optional
        Positive cap on Newton updates per target spatial slice; default 1000.

    Returns
    -------
    fb : ndarray, shape (nvrb, nvxb, nxb)
        Finite destination distribution. For ``correct=1`` it is nonnegative
        and reproduces the spatially interpolated density, axial momentum
        density and squared-speed energy density, to scaled binary64 roundoff.

    Raises
    ------
    InfeasibleMomentsError
        Requested normalized moments lie outside the convex hull of destination
        node velocity/energy pairs. Its ``diagnostics`` identifies the slice
        and a separating inequality; changing solver iterations cannot fix it.
    MomentCorrectionConvergenceError
        A projection fails its iteration bound or numerical postcondition.
    ValueError
        Invalid inputs, missing overlap or unrepresentable intermediates.

    Notes
    -----
    Spatial interpolation acts on extensive moments before normalizing by
    density. The 1e-12 positive reference mixture changes the entropy prior,
    never the target moments. No negative clipping or partial result is used.
    Finite-grid conservation does not establish an atomic-physics model.
    """
    vr_a = _as_1d(vr_a, "vr_a")
    vx_a = _as_1d(vx_a, "vx_a")
    x_a = _as_1d(x_a, "x_a")
    vr_b = _as_1d(vr_b, "vr_b")
    vx_b = _as_1d(vx_b, "vx_b")
    x_b = _as_1d(x_b, "x_b")
    Tnorm_a = _real_scalar(Tnorm_a, "Tnorm_a")
    Tnorm_b = _real_scalar(Tnorm_b, "Tnorm_b")
    if Tnorm_a <= 0.0 or Tnorm_b <= 0.0 or not np.isfinite(Tnorm_a) or not np.isfinite(Tnorm_b):
        raise ValueError("Tnorm_a and Tnorm_b must be positive and finite")
    if isinstance(correct, (bool, np.bool_)) or not isinstance(correct, (int, np.integer)) or correct not in (0, 1):
        raise ValueError("correct must be the integer 0 or 1")
    if do_warn is not None and (
        isinstance(do_warn, (bool, np.bool_)) or not isinstance(do_warn, (int, np.integer))
    ):
        raise ValueError("do_warn must be an integer scalar or None")
    if (
        isinstance(max_correction_iterations, (bool, np.bool_))
        or not isinstance(max_correction_iterations, (int, np.integer))
        or max_correction_iterations < 1
    ):
        raise ValueError("max_correction_iterations must be a positive integer")
    for name, a in (("vr_a", vr_a), ("vr_b", vr_b),
                     ("vx_a", vx_a), ("vx_b", vx_b),
                     ("x_a", x_a), ("x_b", x_b)):
        if np.any(np.diff(a) <= 0.0):
            raise ValueError(f"{name} must be strictly increasing")
    # Declared r62 fail-closed narrowing: the saved arm leaves the minimum
    # node count unvalidated; a single-node vx_a raises a raw IndexError in
    # the correction branch (vx[1] access), and a single-node x_a/x_b or
    # vr_a/vr_b can enter _locate / _make_dvr_dvx with undefined semantics.
    # The exact document requires at least 2 nodes per axis; this asset
    # fail-closes with a named ValueError for each case, which is a
    # declared divergence from the saved arm's raw IndexError. The
    # saved-arm divergences are pinned by regression tests.
    for name, a in (("vr_a", vr_a), ("vx_a", vx_a), ("x_a", x_a),
                     ("vr_b", vr_b), ("vx_b", vx_b), ("x_b", x_b)):
        if a.size < 2:
            raise ValueError(f"{name} must have at least two nodes")
    for name, a in (("vr_a", vr_a), ("vr_b", vr_b)):
        if np.any(a < 0.0):
            raise ValueError(f"{name} must be nonnegative")
    for name, a in (("vx_a", vx_a), ("vx_b", vx_b)):
        if not np.any(a < 0.0) or not np.any(a > 0.0):
            raise ValueError(f"{name} must contain both negative and positive velocities")
    nvra, nvxa, nxa = vr_a.size, vx_a.size, x_a.size
    nvrb, nvxb, nxb = vr_b.size, vx_b.size, x_b.size
    fa = _as_3d(fa, "fa", nvra, nvxa, nxa)
    if correct and np.any(fa < 0):
        raise ValueError("fa must be nonnegative for positive moment correction")

    fV = np.sqrt(Tnorm_b / Tnorm_a)
    if not np.isfinite(fV) or fV <= 0.0:
        raise ValueError("Tnorm_b / Tnorm_a must yield a finite positive velocity scale")

    #   Overlapping index ranges (source oki/okj/okk)
    oki = np.where((fV * vr_b <= max(vr_a)) & (fV * vr_b >= min(vr_a)))[0]
    if len(oki) < 1:
        raise ValueError('No values of Vrb are within range of Vra')
    i0, i1 = oki[0], oki[-1]

    okj = np.where((fV * vx_b <= max(vx_a)) & (fV * vx_b >= min(vx_a)))[0]
    if okj.size < 1:
        raise ValueError('No values of Vxb are within range of Vxa')
    j0, j1 = okj[0], okj[-1]

    okk = np.where((x_b <= max(x_a)) & (x_b >= min(x_a)))[0]
    if okk.size < 1:
        raise ValueError('No values of Xb are within range of Xa')
    k0, k1 = okk[0], okk[-1]

    fb = np.zeros((nvrb, nvxb, nxb))

    dvr_dvx_a = _make_dvr_dvx(vr_a, vx_a)
    Vr2pidVra, _, dVxa, vraL, vraR, vxaL, vxaR = dvr_dvx_a[:7]
    Vra2Vxa2 = dvr_dvx_a[11]

    dvr_dvx_b = _make_dvr_dvx(vr_b, vx_b)
    (Vr2pidVrb, _, dVxb, vrbL, vrbR, vxbL, vxbR, Vol,
     Vth_DVx, Vx_DVx, Vr_DVr, Vrb2Vxb2, jpa, jpb, jna, jnb) = dvr_dvx_b

    #   Weight matrix (deterministic function of the meshes; the original
    #   source cache only memoises this and cannot change the result)
    source_r_left = vraL[None, None, :, None]
    source_r_right = vraR[None, None, :, None]
    destination_r_left = (fV * vrbL)[:, None, None, None]
    destination_r_right = (fV * vrbR)[:, None, None, None]
    source_x_left = vxaL[None, None, None, :]
    source_x_right = vxaR[None, None, None, :]
    destination_x_left = (fV * vxbL)[None, :, None, None]
    destination_x_right = (fV * vxbR)[None, :, None, None]
    radial_left = np.maximum(destination_r_left, source_r_left)
    radial_right = np.minimum(destination_r_right, source_r_right)
    axial_left = np.maximum(destination_x_left, source_x_left)
    axial_right = np.minimum(destination_x_right, source_x_right)
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        overlap = (
            2.0 * np.pi * np.maximum(radial_right**2 - radial_left**2, 0.0)
            * np.maximum(axial_right - axial_left, 0.0)
            / (Vr2pidVrb[:, None, None, None] * dVxb[None, :, None, None])
        )
    _weight = np.where(
        (radial_right > radial_left) & (axial_right > axial_left), overlap, 0.0
    )
    weight = np.zeros((nvrb * nvxb, nvra * nvxa))
    weight = np.reshape(_weight, weight.shape, order='F')

    #   Transfer onto mesh_b velocity space, evaluated on the mesh_a x grid
    fb_xa = np.zeros((nvrb * nvxb, nxa))
    _fa = np.reshape(fa, (nvra * nvxa, nxa), order='F')
    fb_xa = weight @ _fa

    # Density, momentum density and energy density are linear functionals.
    # Interpolate these extensive moments in x BEFORE dividing by density;
    # interpolating mean velocity/energy would violate conservation whenever
    # the source density varies. Velocities here use mesh_b normalized units.
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        va = vx_a / fV
        ea = (vr_a[:, None] / fV)**2 + va[None, :]**2
        volume_a = Vr2pidVra[:, None] * dVxa[None, :]
        masses_a = fa * volume_a[:, :, None]
        density_a = np.sum(masses_a, axis=(0, 1))
        momentum_a = np.sum(masses_a * va[None, :, None], axis=(0, 1))
        energy_a = np.sum(masses_a * ea[:, :, None], axis=(0, 1))
    if (not np.all(np.isfinite(fb_xa)) or
            (correct and not all(np.all(np.isfinite(v)) for v in
                                 (density_a, momentum_a, energy_a)))):
        raise ValueError("source moments or overlap interpolant are not representable")
    if correct and np.any((density_a == 0) & np.any(fa > 0, axis=(0, 1))):
        raise ValueError("positive source density underflows to zero")

    same_velocity_mesh = (
        Tnorm_a == Tnorm_b and np.array_equal(vr_a, vr_b)
        and np.array_equal(vx_a, vx_b)
    )
    for k in range(k0, k1 + 1):
        kL = max(int(_locate(x_a, x_b[k])), 0)
        kR = min(kL + 1, x_a.size - 1)
        kL = min(kL, kR - 1)
        t = (x_b[k] - x_a[kL]) / (x_a[kR] - x_a[kL])
        if correct and same_velocity_mesh:
            # Exact identity at source nodes; convex spatial interpolation
            # already preserves every discrete velocity moment.
            fb[:, :, k] = (1 - t) * fa[:, :, kL] + t * fa[:, :, kR]
            continue
        if correct:
            raw = (1 - t) * fb_xa[:, kL] + t * fb_xa[:, kR]
        else:
            # The uncorrected algebraic branch is retained for compatibility.
            raw = fb_xa[:, kL] + (fb_xa[:, kR] - fb_xa[:, kL]) * t
        fb[:, :, k] = raw.reshape((nvrb, nvxb), order="F")
        if correct:
            density = (1 - t) * density_a[kL] + t * density_a[kR]
            if density == 0:
                fb[:, :, k] = 0
                continue
            momentum = (1 - t) * momentum_a[kL] + t * momentum_a[kR]
            energy = (1 - t) * energy_a[kL] + t * energy_a[kR]
            fb[:, :, k] = _positive_moment_projection(
                fb[:, :, k], Vol, vx_b, vr_b, density,
                momentum / density, energy / density,
                max_correction_iterations, k,
            )

    if correct:
        feature_v = np.broadcast_to(vx_b[None, :], Vol.shape)
        feature_e = Vrb2Vxb2
        vscale = max(abs(vx_b[0]), abs(vx_b[-1]))
        escale = np.max(feature_e)
        for k in range(k0, k1 + 1):
            desired = np.array([np.interp(x_b[k], x_a, arr)
                                for arr in (density_a, momentum_a, energy_a)])
            if desired[0] == 0:
                if np.any(fb[:, :, k] != 0):
                    raise MomentCorrectionConvergenceError("zero density postcondition failed")
                continue
            actual_mass = fb[:, :, k] * Vol
            actual = np.array([np.sum(actual_mass),
                               np.sum(actual_mass * feature_v),
                               np.sum(actual_mass * feature_e)])
            with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
                normalized_actual = (actual / desired[0]) / np.array([1., vscale, escale])
                normalized_desired = (desired / desired[0]) / np.array([1., vscale, escale])
                residual = normalized_actual - normalized_desired
            if (np.any(fb[:, :, k] < 0) or not np.all(np.isfinite(actual))
                    or not np.all(np.isfinite(residual))
                    or np.any(np.abs(residual) > 128 * np.finfo(float).eps)):
                raise MomentCorrectionConvergenceError(
                    f"returned distribution fails conservation at x_b index {k}")

    #   Boundary warnings (source do_warn block; output unchanged)
    if do_warn is not None:
        from warnings import warn
        big = np.max(fb)
        if (i0 > 0) or (i1 < nvrb - 1):
            for k in range(k0, k1 + 1):
                for j in range(j0, j1 + 1):
                    if (i0 > 0) and (fb[i0, j, k] > do_warn * big):
                        warn('Non-zero value of fb detected at min(Vra) boundary')
                    if (i1 < nvrb - 1) and (fb[i1, j, k] > do_warn * big):
                        warn('Non-zero value of fb detected at max(Vra) boundary')
        if (j0 > 0) or (j1 < nvxb - 1):
            for k in range(k0, k1 + 1):
                for i in range(i0, i1 + 1):
                    if (j0 > 0) and (fb[i, j0, k] > do_warn * big):
                        warn('Non-zero value of fb detected at min(Vxa) boundary')
                    if (j1 < nvxb - 1) and (fb[i, j1, k] > do_warn * big):
                        warn('Non-zero value of fb detected at max(Vxa) boundary')
        if (k0 > 0) or (k1 < nxb - 1):
            for i in range(i0, i1 + 1):
                for j in range(j0, j1 + 1):
                    if (k0 > 0) and (fb[i, j, k0] > do_warn * big):
                        warn('Non-zero value of fb detected at min(Xa) boundary')
                    if (k1 < nxb - 1) and (fb[i, j, k1] > do_warn * big):
                        warn('Non-zero value of fb detected at max(Xa) boundary')

    # The legacy correct=0 branch keeps its historical algebraic rescale.
    # Corrected slices have already satisfied all three explicit moments.
    if not correct:
        #   Density rescale (source rescale block)
        tot_a = np.zeros(nxa)
        for k in range(nxa):
            tot_a[k] = np.sum(Vr2pidVra * (fa[:, :, k] @ dVxa))
        tot_b = np.zeros(nxb)
        # Keep SciPy out of import-time and rejected-input paths.  This
        # compatibility branch needs interp1d only after all public input
        # validation and overlap construction have succeeded.
        from scipy import interpolate

        tot_b[k0:k1 + 1] = interpolate.interp1d(x_a, tot_a, fill_value="extrapolate")(x_b[k0:k1 + 1])
        ii = np.where(fb > 0)
        if ii[0].size > 0:
            min_tot = np.min(np.array(fb[ii]))
            for k in range(k0, k1 + 1):
                tot = np.sum(Vr2pidVrb * (fb[:, :, k] @ dVxb))
                if tot > min_tot:
                    fb[:, :, k] = fb[:, :, k] * tot_b[k] / tot

    if not np.all(np.isfinite(fb)):
        raise ValueError("fb must be finite")
    return fb
