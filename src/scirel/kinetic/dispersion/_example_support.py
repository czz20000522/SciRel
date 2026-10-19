"""Python adapters for the packaged PDRK example renderers.

These helpers perform only coordinate and unit bookkeeping. Numerical plots,
stored reference tables, and finite-order approximations continue through the
native transport boundary in :mod:`_example_native`.
"""

import numpy as np

from . import _example_native as _native


def fluid_deck():
    """Return an independent float64 copy of the packaged SI fluid deck."""

    return np.array(_native.fluid_deck(), dtype=np.float64, copy=True)


def fluid_plot_scan(
    graph,
    state,
    *,
    method=2,
    length_scale_m=None,
    frequency_scale_rad_s=None,
    capture_png=True,
    transport=None,
):
    """Map a fluid graph to the native renderer's explicit ports.

    Method 2 accepts optional ``k`` and ``omega`` normalization scales.
    Methods 1, 3, and 4 retain their SI/radian axes and reject a scale rather
    than silently applying one to a different coordinate convention.
    """

    from ._fluid_parallel import normalize_plot_coordinates

    normalize_plot_coordinates(
        [0.0], [0.0],
        length_scale_m=length_scale_m,
        frequency_scale_rad_s=frequency_scale_rad_s,
    )
    if method != 2 and length_scale_m is not None:
        raise ValueError(
            "source methods3/4 plot SI/radian axes; normalization here is method2-only"
        )

    w1 = np.asarray(graph["w1"])
    w2 = np.asarray(graph["w2"])
    axes = graph["axis_values"]
    values = {
        "kk": np.array([]), "tt": np.array([]),
        "kkx": np.array([]), "kkz": np.array([]),
        "ww1": w1, "ww2": w2, "k": 0.0,
    }
    if method in (1, 2):
        values.update(kk=np.asarray(axes[0]), ww1=w1[:, 0, :], ww2=w2[:, 0, :])
    elif method == 3:
        values.update(
            tt=np.asarray(axes[1]),
            k=float(np.hypot(graph["kx"][0, 0], graph["kz"][0, 0])),
            ww1=w1[0, :, :],
            ww2=w2[0, :, :],
        )
    elif method == 4:
        values.update(
            kkx=np.asarray(graph["kx"]).T,
            kkz=np.asarray(graph["kz"]).T,
            ww1=w1.transpose(1, 0, 2),
            ww2=w2.transpose(1, 0, 2),
        )
    else:
        raise ValueError("method1..4 required")

    equilibrium = {
        "s": len(state["q"]),
        "c2": state["c2"],
        "ms": state["m"],
        "betasz": np.array([]) if state["beta_z"] is None else state["beta_z"],
        "betasp": np.array([]) if state["beta_p"] is None else state["beta_p"],
    }
    return _native.fluid_plot_scan(
        values,
        equilibrium,
        method=method,
        tmpcwp=1.0 if length_scale_m is None else length_scale_m,
        tmpwcs1=(
            1.0 if frequency_scale_rad_s is None else frequency_scale_rad_s
        ),
        capture_png=capture_png,
        transport=transport,
    )


def em1d_plot(graph, state, predecessor_plot=None, *, pm=1, transport=None):
    """Compose an accepted continuation with an explicitly supplied figure."""

    continuation = {
        "k": graph["k"],
        "wre": np.real(graph["omega"]),
        "wie": np.imag(graph["omega"]),
    }
    return _native.em1d_plot(
        continuation, state, predecessor_plot, pm=pm, transport=transport
    )


def reference_table(*, transport=None):
    """Read the stored four-column WHAMP reference table."""

    return _native.reference_table(transport=transport)


def reference_overlay(predecessor_plot=None, *, transport=None):
    """Overlay the stored WHAMP table on a supplied native figure."""

    return _native.reference_overlay(predecessor_plot, transport=transport)
