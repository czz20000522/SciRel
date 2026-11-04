# Fitting modes from a time series

Background for fitting a frequency or growth/damping rate from an initial-value simulation (for example a linearised kinetic or fluid run whose field oscillates and decays). The general rule is in the result checks: know what the signal contains, fit a model of that signal, choose the window from estimates, and show convergence. This note covers the common pitfalls for damped oscillating modes.

## Which modes are excited

An initial perturbation that is symmetric (for example even in velocity) excites the roots +ω_r and −ω_r equally, so the field is a decaying standing wave, roughly cos(ω_r t + φ) e^{γt}. The sign of ω_r is not observable in such a series: report the sign the problem's convention requires and say that it comes from the convention, not the fit. Never report a fitted 0 or a random sign as a frequency. If the sign matters, seed a travelling wave or use the phase of the complex field. Several weakly damped roots can also be excited; check that one root dominates the window or fit them together.

## Fitting the signal you have

- From |E(t)| of a standing wave, peaks come every half period: ω_r = π / (mean peak spacing).
- γ is the slope of a straight-line fit to ln(peak height) against peak time.
- Do not fit a single complex exponential to |E|: it carries no oscillating phase, so the fit returns ω ≈ 0.
- Locate each peak by interpolating around the sampled maximum (for example a parabola through three points), not at the grid sample.

## Choosing the window

- Start after the initial transient: move the start later until the fitted values stop drifting.
- End before discrete-velocity recurrence, at T_R = 2π / (k Δv) for a uniform velocity grid of spacing Δv, before the signal reaches the round-off or discretisation noise floor, and before any non-physical growth.
- Weakly damped cases need long windows, so pick Δv from the required T_R. Strongly damped cases reach the noise floor within a few periods; use the clean peaks you have and report how many.

## Grid and domain

Distributions with heavy (power-law) tails need a much wider velocity domain than a Maxwellian. Check the moments of the gridded equilibrium against the intended ones and that the truncated edges do not inject signal.

## Agreement with an independent route

Compare with an independent result, such as a dispersion-relation root, only after the time-series fit is stable under changes of grid, time step, domain and window. A remaining difference should then be explained (another excited root, a short window, a branch choice), not tuned away.
