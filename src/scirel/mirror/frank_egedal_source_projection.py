"""Project a loss-cone source onto the retained Frank--Egedal angular modes."""

import math
import numpy as np

from ._loss_cone_modes import regular_even_mode


def fractional_mode(degree, xi, n_terms, backend="truncated"):
    """Regular even angular mode; legacy n_terms does not truncate the solution."""
    if backend not in {"truncated", "hypergeometric"}:
        raise ValueError("legendre_backend must be truncated or hypergeometric")
    if int(n_terms) != n_terms or n_terms < 2:
        raise ValueError("legendre_terms must be an integer of at least two")
    return regular_even_mode(degree, xi)


def _make_batch_safe_fractional_mode(backend):
    """Return the internal callback with an explicit batch-contract marker."""

    def mode(degree, xi, terms):
        return fractional_mode(degree, xi, terms, backend)

    mode._scirel_batch_safe = True
    return mode


def project_frank_egedal_source_modes(
    *,
    mirror_ratio=2.0,
    legendre_terms=15,
    legendre_backend="truncated",
    legendre_degrees=None,
    legendre_mode_count=6,
    legendre_spectrum_grid_points=256,
    source_coefficients=None,
    nbi_pitch_angle_deg=45.0,
    spectrum_operator=None,
):
    """Project a point-pitch source onto retained Frank--Egedal angular modes.

    Parameters
    ----------
    mirror_ratio : real scalar, optional
        Mirror ratio [dimensionless]. It is converted to float. The default is
        ``2.0``. No separate finite or physical ``>1`` validation is imposed;
        the derived boundary and the inactive branch follow the existing
        arithmetic.
    legendre_terms : scalar, optional
        Legacy retained-term count [count]. It is converted to ``int``. The
        default is ``15``. In the active branch it must be at least two; it
        does not truncate the regular mode evaluation.
    legendre_backend : text, optional
        Legacy backend name [text]. The default is ``'truncated'``. The active
        branch accepts ``'truncated'`` or ``'hypergeometric'``; both select the
        same regular scaled initial-value evaluator. The inactive branch does
        not read or return this control.
    legendre_degrees : array_like, shape (N_mode,), optional
        Explicit finite one-dimensional fractional modes [dimensionless]. The
        default is ``None``. Supplying degrees bypasses the spectrum operator;
        integer degrees are allowed.
    legendre_mode_count : scalar, optional
        Spectrum mode count [count] used only when ``legendre_degrees`` is not
        supplied. It is converted to ``int``. The default is ``6``.
    legendre_spectrum_grid_points : scalar, optional
        Spectrum grid-point count [count] used only when ``legendre_degrees``
        is not supplied. It is converted to ``int``. The default is ``256``.
    source_coefficients : array_like, shape (N_mode,), optional
        Explicit source coefficients paired with ``legendre_degrees``. Values
        must be finite and have the same shape as the degrees [computed branch:
        dimensionless in the source-defined normalized angular convention;
        explicit branch: caller-supplied normalization]. The default is
        ``None``, which computes point-pitch coefficients by quadrature.
    nbi_pitch_angle_deg : real scalar, optional
        Point-source NBI pitch angle [degree]. It is converted to float only
        when coefficients are computed. The default is ``45.0``. Its cosine is
        clipped to the active interval.
    spectrum_operator : callable, optional
        Caller-provided degree generator used when ``legendre_degrees`` is
        absent. It is called as
        ``spectrum_operator(xi_tp_mid, mode_count, grid_points, backend)`` and
        must return a mapping with a finite nonempty one-dimensional
        ``degrees`` array [xi_tp_mid and returned degrees: dimensionless;
        mode_count and grid_points: count; backend: text]. The default is
        ``None``.

    Returns
    -------
    degrees : ndarray of float64, shape (N_mode,)
        Explicit or generated fractional degrees [dimensionless], in their
        supplied order. The inactive branch returns an empty array.
    source_coefficients : ndarray of float64, shape (N_mode,)
        Explicit coefficients or computed NBI point-pitch projection
        coefficients [computed branch: dimensionless in the source-defined
        normalized angular convention; explicit branch: caller-supplied
        normalization]. The inactive branch returns an empty array.
    degree_source : str
        Degree origin [text]: ``'caller_supplied'``,
        ``'scirel.mirror.loss_cone_spectrum'`` or
        ``'inactive_loss_cone'``.
    legendre_terms : int
        Converted term-count control [count] carried in the result.
    legendre_backend : str
        Active-branch backend label [text]. This key is absent in the inactive
        branch.
    xi_tp_mid : float
        Mirror-ratio-derived pitch-cosine turning boundary [dimensionless].
    fractional_mode : callable
        Evaluator for a normalized fractional mode as
        ``fractional_mode(degree, xi, terms)``. It returns dimensionless values
        [dimensionless return] and may raise on invalid input or failed
        integration.

    Raises
    ------
    TypeError
        If the removed ``params`` mapping is supplied, the removed
        ``turning_b`` alias is used, or an unknown keyword is supplied.
    ValueError
        If active degree or coefficient arrays, the backend, term controls, or
        the required spectrum operator violate the declared contract.
    RuntimeError
        If source-mode normalization fails to converge, needs more than 8192
        nodes, or produces a non-finite or nonpositive normalization.

    See Also
    --------
    evaluate_frank_egedal_hot_ion_moments : Consume the returned modes and coefficients.
    evaluate_frank_egedal_radial_envelope : Build the radial envelope used by the source.
    assemble_frank_egedal_pressure : Assemble the pressure state.

    Notes
    -----
    The turning boundary is evaluated as
    ``xi_tp_mid=sqrt(max(0,1-1/max(mirror_ratio,1e-12)))``. Explicit degrees
    bypass spectrum evaluation. Otherwise the optional spectrum operator
    generates the degrees. Computed coefficients use

    .. math:: c_\\nu = u_\\nu(\\operatorname{clip}(\\cos\\theta_{NBI},0,\\xi_{tp}))
        / (4\\pi\\int_0^{\\xi_{tp}}u_\\nu^2\\,d\\xi).

    The regular even initial-value mode is not excluded at integer degree and
    is not polynomial-truncated. Gauss-Legendre normalization is refined by
    successively doubling nodes until the relative agreement is ``1e-10`` or
    less. The inactive cone returns empty arrays and no partial active result
    is returned.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.mirror.frank_egedal_source_projection import project_frank_egedal_source_modes
    >>> r=project_frank_egedal_source_modes(mirror_ratio=1.5,legendre_degrees=[2.],nbi_pitch_angle_deg=60.)
    >>> a=1/np.sqrt(3); norm=a-2*a**3+9*a**5/5
    >>> np.testing.assert_allclose(r['source_coefficients'],[.25/(4*np.pi*norm)],rtol=2e-10)
    """
    mirror_ratio = float(mirror_ratio)
    xi_tp_mid = math.sqrt(max(0.0, 1.0 - 1.0 / max(mirror_ratio, 1e-12)))
    if xi_tp_mid <= 0.0:
        return {
            "degrees": np.empty(0),
            "source_coefficients": np.empty(0),
            "degree_source": "inactive_loss_cone",
            "legendre_terms": int(legendre_terms),
            "xi_tp_mid": xi_tp_mid,
            "fractional_mode": fractional_mode,
        }
    n_terms = int(legendre_terms)
    backend = str(legendre_backend)
    if backend not in {"truncated", "hypergeometric"}:
        raise ValueError("legendre_backend must be truncated or hypergeometric")
    explicit = legendre_degrees
    if explicit is not None:
        degrees = np.asarray(explicit, dtype=float)
        if degrees.ndim != 1 or degrees.size == 0 or (not np.all(np.isfinite(degrees))):
            raise ValueError("legendre_degrees must be a non-empty finite one-dimensional array")
        degree_source = "caller_supplied"
    else:
        if spectrum_operator is None:
            raise ValueError("spectrum_operator is required when legendre_degrees is absent")
        spectrum = spectrum_operator(
            xi_tp_mid,
            int(legendre_mode_count),
            int(legendre_spectrum_grid_points),
            backend,
        )
        degrees = np.asarray(spectrum["degrees"], dtype=float)
        if degrees.ndim != 1 or degrees.size == 0 or (not np.all(np.isfinite(degrees))):
            raise ValueError(
                "spectrum_operator must return a non-empty finite one-dimensional degrees array"
            )
        degree_source = "scirel.mirror.loss_cone_spectrum"
    if n_terms < 2:
        raise ValueError("legendre_terms must be at least two")
    explicit_coefficients = source_coefficients
    if explicit_coefficients is not None:
        coefficients = np.asarray(explicit_coefficients, dtype=float)
        if coefficients.shape != degrees.shape or not np.all(np.isfinite(coefficients)):
            raise ValueError("source_coefficients must be finite and match legendre_degrees")
    else:
        from scipy.special import roots_legendre

        pitch_angle_degrees = float(nbi_pitch_angle_deg)
        xi_nbi = float(np.clip(math.cos(math.radians(pitch_angle_degrees)), 0.0, xi_tp_mid))
        coefficients = []
        for degree in degrees:
            previous = None
            start_nodes = 2 ** int(
                np.ceil(
                    np.log2(
                        max(32.0, 8 * np.sqrt(degree * (degree + 1)) * np.arcsin(xi_tp_mid) / np.pi)
                    )
                )
            )
            for node_count in (start_nodes * 2**i for i in range(8)):
                if node_count > 8192:
                    raise RuntimeError(
                        "source-mode normalization requires unresolved angular resolution"
                    )
                nodes, weights = roots_legendre(node_count)
                values = fractional_mode(degree, 0.5 * xi_tp_mid * (nodes + 1.0), n_terms, backend)
                norm = 0.5 * xi_tp_mid * float(np.dot(weights, values * values))
                if previous is not None and abs(norm - previous) <= 1e-10 * abs(norm):
                    break
                previous = norm
            else:
                raise RuntimeError("source-mode normalization quadrature failed to converge")
            if not np.isfinite(norm) or norm <= 0.0:
                raise RuntimeError("source-mode normalization is not finite and positive")
            coefficients.append(
                float(fractional_mode(degree, xi_nbi, n_terms, backend)) / (4 * math.pi * norm)
            )
        coefficients = np.asarray(coefficients)
    return {
        "degrees": degrees,
        "source_coefficients": coefficients,
        "degree_source": degree_source,
        "legendre_terms": n_terms,
        "legendre_backend": backend,
        "xi_tp_mid": xi_tp_mid,
        "fractional_mode": _make_batch_safe_fractional_mode(backend),
    }


__all__ = ["project_frank_egedal_source_modes"]
