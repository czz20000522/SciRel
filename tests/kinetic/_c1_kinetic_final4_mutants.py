"""Internal mutants for the four C1 kinetic evidence files, loaded as a pytest plugin.

Why this file exists
--------------------
``scripts/mutation_check.py`` mutates only *returned* values (scale/negate/zero/swap/constant).  Those
mutants say nothing about the specific claims the new evidence files make, e.g. "a returned root is a
zero of the determinant", "the ladder is exactly the declared colon ladder", "a false success is
rejected", "a rejected point seeds nothing".  This plugin supplies one targeted mutant per claim so the
ledger in ``c1_kinetic_final4_mutant_check.py`` can answer the question the repository's rule 7 asks:
*would this assertion change if the thing I care about changed?*

Selection is by environment variable, never by test code:

* ``C1F4_MUTANT``  -- mutant name (empty means "load the plugin, mutate nothing").
* ``C1F4_HITS``    -- file this plugin appends one line to every time a mutated callable is invoked.
  A mutant that never reaches the code under test leaves this file empty, which is the positive
  control separating "the tests did not constrain it" from "the mutation never ran".

Mutants patch module attributes at ``pytest_configure`` time, before the test modules import their
symbols, and each patch replaces the *internal* callable a public entry resolves at call time where
that is possible (``_reference_fsolve``, ``scan_frequencies``, ``seed_wavenumber``).  The continuation
and residual mutants wrap the public callable instead, because the behaviour they inject (dropping the
residual bound, swallowing a failure, ignoring ``pm``) lives inline in that function.
"""

from __future__ import annotations

import functools
import os

import numpy as np

MUTANT = os.environ.get("C1F4_MUTANT", "")
HITS = os.environ.get("C1F4_HITS", "")


def _hit(tag: str) -> None:
    if HITS:
        with open(HITS, "a", encoding="utf-8") as handle:
            handle.write(tag + "\n")


def _record_wrap(tag, function):
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        _hit(tag)
        return function(*args, **kwargs)

    return wrapper


# --------------------------------------------------------------------------- roots


def _install_roots(name):
    from scirel.kinetic import kinetic_wavevector_roots as module

    original = module._reference_fsolve

    if name == "roots_seed":
        # "The solver never moved": return the initial point with a converged flag.  A root finder can
        # regress exactly this way (returning the seed) and still report plausible diagnostics.
        def patched(fcn, x0, *args, **kwargs):
            _hit(name)
            return complex(x0), complex(fcn(complex(x0))), 1, 1, 1

    elif name == "roots_conj":

        def patched(fcn, x0, *args, **kwargs):
            _hit(name)
            root, fval, info, niter, nfev = original(fcn, x0, *args, **kwargs)
            return np.conjugate(root), fval, info, niter, nfev

    elif name == "roots_scaled":

        def patched(fcn, x0, *args, **kwargs):
            _hit(name)
            root, fval, info, niter, nfev = original(fcn, x0, *args, **kwargs)
            return root * (1.0 + 1e-4), fval, info, niter, nfev

    elif name == "roots_flag_ok":

        def patched(fcn, x0, *args, **kwargs):
            _hit(name)
            root, fval, _info, niter, nfev = original(fcn, x0, *args, **kwargs)
            return root, fval, 1, niter, nfev

    else:
        return False
    module._reference_fsolve = patched
    return True


# --------------------------------------------------------------------------- scan


def _install_scan(name):
    from scirel.kinetic import kinetic_wavevector_scan as module

    if name == "scan_ulp":
        original = module.scan_frequencies

        def patched(*args, **kwargs):
            _hit(name)
            out = original(*args, **kwargs)
            omegas = np.array(out["omegas"], dtype=np.float64, copy=True)
            omegas[-1] = np.nextafter(omegas[-1], np.inf)
            return {"omegas": omegas, "count": out["count"]}

    elif name == "scan_seed":
        original = module.seed_wavenumber

        def patched(*args, **kwargs):
            _hit(name)
            out = original(*args, **kwargs)
            return {"kx_start": complex(out["kx_start"]) * (1.0 + 1e-12)}

    elif name == "scan_flag_ok":
        from scirel.kinetic import kinetic_wavevector_roots as roots_module

        original = roots_module.solve_kinetic_wavevector_roots

        def patched(*args, **kwargs):
            _hit(name)
            out = original(*args, **kwargs)
            out = dict(out)
            out["status"] = np.ones_like(np.asarray(out["status"]))
            out["success"] = np.ones(np.asarray(out["success"]).shape, dtype=bool)
            return out

    else:
        return False
    if name == "scan_ulp":
        module.scan_frequencies = patched
    elif name == "scan_seed":
        module.seed_wavenumber = patched
    else:
        from scirel.kinetic import kinetic_wavevector_roots as roots_module

        roots_module.solve_kinetic_wavevector_roots = patched
    return True


# --------------------------------------------------------------------------- continuation


def _install_continuation(name):
    from scirel.kinetic.dispersion import parallel as public_module
    from scirel.kinetic.dispersion import parallel_continuation as internal_module

    original = internal_module.continue_em1d if hasattr(internal_module, "continue_em1d") else None
    original = original or internal_module._continue_em1d

    if name == "cont_noise":
        # Accepted root reported with a small relative error: the residual bound was certified on the
        # unperturbed value, so only an external reference (the vacuum closed form) can see it.
        def patched(inputs):
            _hit(name)
            result = original(inputs)
            result = dict(result)
            result["omega"] = np.asarray(result["omega"]) * (1.0 + 1e-6)
            return result

    elif name == "cont_ignore_bound":
        # The residual bound is effectively disabled: a solver "success" is then accepted unconditionally.
        def patched(inputs):
            _hit(name)
            modified = dict(inputs)
            modified["residual_tolerance"] = 1e300
            return original(modified)

    elif name == "cont_swallow_failure":
        # A rejected point is turned into a plausible partial result instead of stopping the run.
        def patched(inputs):
            _hit(name)
            try:
                return original(inputs)
            except Exception as failure:  # noqa: BLE001 - the mutant's whole point
                record = getattr(failure, "record", {}) or {}
                prefix = tuple(record.get("accepted_prefix", ()))
                return {
                    "k": np.asarray(list(inputs.get("k_grid") or []), dtype=float)[: len(prefix)],
                    "omega": np.asarray(prefix, dtype=complex),
                    "records": [],
                }

    else:
        return False
    public_module.continue_em1d = patched
    internal_module.continue_em1d = patched
    return True


# --------------------------------------------------------------------------- residual


def _install_residual(name):
    from scirel.kinetic.dispersion import _fluid_parallel as internal_module
    from scirel.kinetic.dispersion import parallel as public_module

    original = internal_module.em1d_parallel_residual

    if name == "res_drop_pm":

        def patched(state, omega, k, *, pm=1):
            _hit(name)
            return original(state, omega, k, pm=1)

    elif name == "res_signed_k":

        def patched(state, omega, k, *, pm=1):
            _hit(name)
            return original(state, omega, abs(k), pm=pm)

    elif name == "res_scale":

        def patched(state, omega, k, *, pm=1):
            _hit(name)
            value, scale = original(state, omega, k, pm=pm)
            return complex(value) * (1.0 + 1e-4), scale

    else:
        return False
    public_module.em1d_parallel_residual = patched
    internal_module.em1d_parallel_residual = patched
    return True


# Mutant names carry a short family prefix ("cont_noise", "res_scale"); the installer is selected by it.
INSTALLERS = {
    "roots": _install_roots,
    "scan": _install_scan,
    "cont": _install_continuation,
    "res": _install_residual,
}


def pytest_configure(config):
    _hit("configure:" + MUTANT)
    if not MUTANT:
        return
    family = MUTANT.split("_", 1)[0]
    installer = INSTALLERS.get(family)
    installed = installer(MUTANT) if installer else False
    _hit(("installed:" if installed else "unknown:") + MUTANT)
