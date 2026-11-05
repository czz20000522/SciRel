"""Internal workflow cases retained for testing only; not a public capability."""

from scirel.kinetic.dispersion import magnetized as _magnetized


def selected_fields(scan_state, seeds, *, rng_seed=None):
    """Select seeded modes and reconstruct their normalized fields."""

    selected = _magnetized.select_modes(scan_state, seeds)
    return _magnetized.reconstruct_polarization(selected, rng_seed=rng_seed)


def rendered_output(scan_state, seeds, *, scales=(1.0, 1.0, 1.0), runtime=0.0, rng_seed=None):
    """Render all roots, select requested modes, and persist their fields."""

    all_roots = _magnetized.render_spectrum(scan_state, runtime=runtime)
    selected = _magnetized.select_modes(all_roots, seeds)
    plotted = _magnetized.render_selected_modes(selected, scales=scales, runtime=runtime)
    return _magnetized.source_output(plotted, runtime=runtime, rng_seed=rng_seed)


def preset_output(scan_state, *, scenario="default", runtime=0.0, rng_seed=None):
    """Render a named stored scenario through the native writer."""

    all_roots = _magnetized.render_spectrum(scan_state, runtime=runtime)
    selected = _magnetized.select_preset(all_roots, scenario=scenario, runtime=runtime)
    return _magnetized.source_output(selected, runtime=runtime, rng_seed=rng_seed)
