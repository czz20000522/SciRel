"""Small composition operators for normalized kinetic dispersion probes. Each helper validates its scalar contract before assembling a shared equilibrium query."""
from __future__ import annotations

import numpy as np

__all__ = ["evaluate_kinetic_dispersion_relation"]


def probe_frequency(*, omega_frac, wn):
    """Scale the caller's angular-frequency fraction by the graph's own normalisation.

    This is a bounded scalar affine adapter. The source driver writes its frequency probe
    as a fraction of its own normalisation frequency (``w=wf(p)*wcn``), so the caller gives
    the dimensionless fraction and the graph supplies the ``wn`` it derived from the same
    equilibrium controls. No source-captured absolute frequency enters the call.
    """
    omega_frac = float(omega_frac)
    wn = float(wn)
    if not np.isfinite(omega_frac) or not np.isfinite(wn):
        raise ValueError("omega_frac and wn must be finite")
    if wn <= 0.0:
        raise ValueError("wn must be strictly positive")
    return {"omega": omega_frac * wn}


def probe_wavenumber(*, kx_frac, kn):
    """Scale the caller's perpendicular-wavenumber fraction by the graph's own normalisation.

    The source writes ``kx=kxf(p)*kn``; the graph supplies the ``kn`` it derived from the
    same equilibrium controls, so the physical probe value is computed here rather than
    injected from any captured source result.
    """
    kx_frac = float(kx_frac)
    kn = float(kn)
    if not np.isfinite(kx_frac) or not np.isfinite(kn):
        raise ValueError("kx_frac and kn must be finite")
    if kn <= 0.0:
        raise ValueError("kn must be strictly positive")
    return {"kx": kx_frac * kn}


def omega_to_frequency(*, omega):
    """Convert an angular frequency to a frequency.

    This is a bounded unit adapter: ``f = omega / (2*pi)`` is the SI definition of the
    angular-frequency convention, not a scientific mapping.
    """
    omega = float(omega)
    if not np.isfinite(omega):
        raise ValueError("omega must be finite")
    return {"f": omega / (2.0 * np.pi)}


def evaluate_kinetic_dispersion_relation(
    ms,
    qs,
    ns_unit,
    Ts_unit,
    B0,
    n00,
    T00,
    omega_frac,
    kz,
    kx_frac,
    lmx=5,
):
    """Return both kinetic determinant paths over one shared equilibrium snapshot.

    ``omega_frac`` and ``kx_frac`` are dimensionless fractions; the graph derives ``wn``,
    ``kn`` and the absolute ``omega``/``kx`` itself from the caller's raw equilibrium
    controls. ``kz`` is the source driver's own absolute parallel wavenumber.
    """
    # Resolve the scale operator first so its established input validation runs before
    # loading the two determinant implementations and their numerical helpers.
    from .species_equilibrium_scales import derive_species_equilibrium_scales

    scales = derive_species_equilibrium_scales(
        ms=ms, qs=qs, ns_unit=ns_unit, Ts_unit=Ts_unit, B0=B0, n00=n00, T00=T00
    )
    kz = float(kz)
    if not np.isfinite(kz):
        raise ValueError("kz must be finite")

    # These are graph dependencies, not namespace dependencies.  Load them only at the
    # public call boundary after the shared equilibrium and scalar checks have succeeded.
    from .kinetic_dispersion_ronnmark import evaluate_kinetic_dispersion_ronnmark
    from .kinetic_dispersion_sum_fluid import evaluate_fluid_kinetic_dispersion_sum

    omega = probe_frequency(omega_frac=omega_frac, wn=scales["wn"])["omega"]
    kx = probe_wavenumber(kx_frac=kx_frac, kn=scales["kn"])["kx"]
    f = omega_to_frequency(omega=omega)["f"]
    shared = dict(B0=B0, qs=qs, ms=ms, ns0=scales["ns0"], Ts0=scales["Ts0"],
                  f=f, kz=kz, kx=kx)
    summed = evaluate_fluid_kinetic_dispersion_sum(**shared, lmx=lmx)
    ronnmark = evaluate_kinetic_dispersion_ronnmark(**shared)
    return {
        "scales": scales,
        "omega": omega,
        "kx": kx,
        "f": f,
        "determinant_sum_n": summed["determinant"],
        "determinant_ronnmark": ronnmark["determinant"],
        "K_sum_n": summed["K"],
        "D_sum_n": summed["D"],
        "K_ronnmark": ronnmark["K"],
        "D_ronnmark": ronnmark["D"],
        "branches": ronnmark["branches"],
        "graph_order": [
            "species_equilibrium_scales",
            "probe_frequency",
            "probe_wavenumber",
            "omega_to_frequency",
            "kinetic_dispersion_sum_n",
            "kinetic_dispersion_ronnmark",
        ],
    }
