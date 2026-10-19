"""Explicit task-graph entry points for PDRK scientific operations."""

from . import _workflow_impl as _compositions
from . import magnetized as _magnetized
from . import rational as _rational

__all__ = [
    "solve_dispersion",
    "scan_spectrum",
    "reconstruct_polarization",
    "original_program",
    "selected_fields",
    "rendered_output",
    "preset_output",
    "ordered_rational_spectrum",
    "regenerate_jpole",
    "reassemble_rational_program",
]


def solve_dispersion(inputs):
    """Initialize an equilibrium and perform the ordered spectral scan."""

    return _magnetized.solve_dispersion(**inputs)


def scan_spectrum(inputs):
    """Scan a finite coordinate grid with the carried frequency guess."""

    return _magnetized.scan_spectrum(**inputs)


def reconstruct_polarization(inputs):
    """Reconstruct normalized electric and magnetic fields for selected modes."""

    return _magnetized.reconstruct_polarization(**inputs)


def original_program(inputs):
    """Run the packaged full program with explicit noninteractive inputs."""

    return _magnetized.original_program(**inputs)


def selected_fields(inputs):
    """Select seeded modes and reconstruct their fields."""

    return _compositions.selected_fields(**inputs)


def rendered_output(inputs):
    """Render, select, and write a chosen mode set."""

    return _compositions.rendered_output(**inputs)


def preset_output(inputs):
    """Render a named preset and pass it to the native writer."""

    return _compositions.preset_output(**inputs)


def ordered_rational_spectrum(inputs):
    """Evaluate the rational model's ordered spectrum."""

    return _rational.ordered_spectrum(**inputs)


def regenerate_jpole(inputs):
    """Construct Padé coefficients and retain their precision diagnostics."""

    return _rational.jpole_generator(**inputs)


def reassemble_rational_program(inputs):
    """Write the rational program's numeric and presentation artifacts."""

    return _rational.reassemble_original_program(**inputs)
