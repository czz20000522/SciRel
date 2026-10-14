"""Source-shaped composition of declared D1 mappings; no independent science."""
from . import magnetized as current

def selected_fields(scan_state,seeds,*,rng_seed=None):
    """Scan carrier + normalized source seeds -> original near-mode EM fields.

    `scan_state` is the genuine current.scan_spectrum predecessor, including its
    final d. No plotting or extra output reconstruction is inserted here.
    """
    selected=current.select_modes(scan_state,seeds)
    return current.reconstruct_polarization(selected,rng_seed=rng_seed)

def rendered_output(scan_state,seeds,*,scales=(1.,1.,1.),runtime=0.,rng_seed=None):
    """Scan -> all-root presentation -> selection -> selected plot -> writer.

    The original writer owns its one reconstruction. SourceOutputError retains
    partial native artifacts and observable state when the source stage fails.
    """
    all_roots=current.render_spectrum(scan_state,runtime=runtime)
    selected=current.select_modes(all_roots,seeds)
    plotted=current.render_selected_modes(selected,scales=scales,runtime=runtime)
    return current.source_output(plotted,runtime=runtime,rng_seed=rng_seed)

def preset_output(scan_state,*,scenario='default',runtime=0.,rng_seed=None):
    """Source all-root plot -> stored source seed/scaling script -> writer."""
    all_roots=current.render_spectrum(scan_state,runtime=runtime)
    selected=current.select_preset(all_roots,scenario=scenario,runtime=runtime)
    return current.source_output(selected,runtime=runtime,rng_seed=rng_seed)
