"""Small native-resource facade used by the packaged PDRK examples.

The Python layer owns port preparation and validation. Octave remains the
owner of the historical plotting and table-producing routines; this module
only describes their closed input/output contracts and starts the generic
transport boundary.
"""

from pathlib import Path
from typing import Mapping

import numpy as np


ROOT = Path(__file__).resolve().parent / "_native"

_PLOT_OUTPUTS = (
    "figure_native", "figure_png", "line_x", "line_y", "line_offsets",
    "line_axes", "line_width", "line_markers", "axes_limits", "legend_labels",
)
_ACTION_SPECS = {
    "fluid_plot": (
        "examples/fluid_plot_scan.m",
        ("plot_line_count", "plot_surface_count", "png_bytes"),
        ("s", "method", "kk", "tt", "kkx", "kkz", "ww1", "ww2", "c2",
         "ms", "betasz", "betasp", "k", "tmpcwp", "tmpwcs1", "capture_png"),
        ("examples",),
    ),
    "em_plot": (
        "examples/em1d_plot.m", _PLOT_OUTPUTS,
        ("predecessor_figure", "k", "wre", "wie", "cwp", "wcs1", "pm"),
        ("examples",),
    ),
    "whamp_data": (
        "examples/whamp_data.m", ("whpdat", "kxwhp", "kzwhp", "wrwhp", "wiwhp"),
        (), ("examples",),
    ),
    "reference_overlay": (
        "examples/whamp_overlay.m",
        (*_PLOT_OUTPUTS, "whpdat", "kxwhp", "kzwhp", "wrwhp", "wiwhp"),
        ("predecessor_figure",), ("examples",),
    ),
    "finiteN": ("finiteN/action.m", ("w",), ("z", "N"), ("finiteN",)),
}


def state(value):
    """Return the mapping carried by a native result or a plain mapping."""

    return value.state if hasattr(value, "state") else value


def source_numeric(value):
    """Narrow numeric ports to the dtypes accepted by MAT transport."""

    from scipy import sparse

    if sparse.issparse(value):
        target = np.complex128 if value.dtype.kind == "c" else np.float64
        already_native = (
            value.dtype.kind == "f" and value.dtype.itemsize == 8
        ) or (value.dtype.kind == "c" and value.dtype.itemsize == 16)
        if value.dtype.kind in "biufc" and not already_native:
            return value.astype(target)
        return value

    array = np.asarray(value)
    if array.dtype.kind in "biuf" and not (
        array.dtype.kind == "f" and array.dtype.itemsize == 8
    ):
        return array.astype(np.float64)
    if array.dtype.kind == "c" and array.dtype.itemsize != 16:
        return array.astype(np.complex128)
    return value


def invoke(name: str, ports: Mapping[str, object], transport=None):
    """Invoke one declared native action with a fresh action registry."""

    from ._transport import NativeAction, NativeTransport

    actions = {key: NativeAction(*spec) for key, spec in _ACTION_SPECS.items()}
    prepared = {
        key: value if key == "predecessor_figure" else source_numeric(value)
        for key, value in ports.items()
    }
    runner = transport or NativeTransport(ROOT, actions)
    return runner.invoke(name, prepared)


def fluid_deck():
    """Load the packaged SI fluid example deck without changing its units."""

    return np.loadtxt(ROOT / "examples/pdrf_SI.in", skiprows=1, ndmin=2)


def fluid_plot_scan(
    scan, equilibrium, *, method=2, tmpcwp=None, tmpwcs1=None,
    capture_png=False, transport=None,
):
    """Forward a prepared fluid scan to the native plotting routine."""

    values = state(scan)
    equilibrium_values = state(equilibrium)
    ports = {
        key: values[key]
        for key in ("kk", "tt", "kkx", "kkz", "ww1", "ww2", "k")
    }
    ports.update({
        key: equilibrium_values[key]
        for key in ("s", "c2", "ms", "betasz", "betasp")
    })
    ports.update(
        method=method,
        tmpcwp=np.array([]) if tmpcwp is None else tmpcwp,
        tmpwcs1=np.array([]) if tmpwcs1 is None else tmpwcs1,
        capture_png=capture_png,
    )
    return invoke("fluid_plot", ports, transport)


def em1d_plot(
    continuation, initialized_state, predecessor_plot, *, pm=1, transport=None,
):
    """Forward one EM continuation step and an optional predecessor figure."""

    values = state(continuation)
    equilibrium_values = state(initialized_state)
    ports = {key: values[key] for key in ("k", "wre", "wie")}
    ports.update({key: equilibrium_values[key] for key in ("cwp", "wcs1")})
    ports.update(
        pm=pm,
        predecessor_figure=(
            np.array([], dtype=np.uint8)
            if predecessor_plot is None
            else state(predecessor_plot)["figure_native"]
        ),
    )
    return invoke("em_plot", ports, transport)


def reference_table(*, transport=None):
    """Read the packaged WHAMP reference table through the native boundary."""

    return invoke("whamp_data", {}, transport)


def reference_overlay(predecessor_plot, *, transport=None):
    """Overlay the stored WHAMP table on an explicitly supplied figure."""

    figure = (
        np.array([], dtype=np.uint8)
        if predecessor_plot is None
        else state(predecessor_plot)["figure_native"]
    )
    return invoke("reference_overlay", {"predecessor_figure": figure}, transport)


def faddeeva_finite_N(z, N=16, *, transport=None):
    """Evaluate the packaged finite-order Faddeeva approximation."""

    if (
        not isinstance(N, (int, np.integer))
        or isinstance(N, (bool, np.bool_))
        or N <= 0
    ):
        raise ValueError("positive integer N required")
    return invoke("finiteN", {"z": z, "N": N}, transport)
