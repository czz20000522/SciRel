"""Declared PDRK TaskGraphs, called with one explicit scientific port mapping.

Each wrapper only unpacks ports. Numerical relations remain in their named
operators; failures propagate with the underlying stage's partial-result rule.
"""
from . import magnetized as _m
from . import _workflow_impl as _w

def solve_dispersion(inputs):
    """Species initialization then an ordered spectral scan."""
    return _m.solve_dispersion(**inputs)

def scan_spectrum(inputs):
    """Ordered finite coordinate scan with explicit carried frequency guess."""
    return _m.scan_spectrum(**inputs)

def reconstruct_polarization(inputs):
    """Selected modes to newly solved, normalized electric/magnetic fields."""
    return _m.reconstruct_polarization(**inputs)

def original_program(inputs):
    """Packaged full stored program and writer with noninteractive choices."""
    return _m.original_program(**inputs)

def selected_fields(inputs):
    """Select normalized seed modes then reconstruct their fields."""
    return _w.selected_fields(**inputs)

def rendered_output(inputs):
    """Spectrum presentation, explicit selection, selected presentation, writer."""
    return _w.rendered_output(**inputs)

def preset_output(inputs):
    """Stored scenario selection and scaling followed by the native writer."""
    return _w.preset_output(**inputs)

from . import rational as _r

def ordered_rational_spectrum(inputs):
    """Ordered model-specific scan with explicit root and pole classification."""
    return _r.ordered_spectrum(**inputs)

def regenerate_jpole(inputs):
    """Declared precision Padé generation with its linear residual proof."""
    return _r.jpole_generator(**inputs)

def reassemble_rational_program(inputs):
    """Native-family reconstruction with independent numeric/plot artifacts."""
    return _r.reassemble_original_program(**inputs)
