Diagnostic modelling and parameter inversion: from observation residuals to a bounded fit
=========================================================================================

This chapter answers one concrete question: **given an axisymmetric equilibrium model and measurements of flux and pressure at a few locations, how do you turn model predictions into residuals with consistent dimensions, and recover two parameters within parameter bounds?**

By the end you should be able to carry out this chain on your own: sample predictions at specified ``R-Z`` points, normalize the mismatch by the observation standard deviations, run one trial with the real Picard forward, and finally perform a fit from Latin-hypercube initial values with bounded least squares — and understand the difference between "the optimizer converged" and "the fit is trustworthy".

.. note::

   This chapter is a tutorial, not a contract summary. Full parameters, failure behavior and applicability for every entry point are on the API reference pages linked at the end of the chapter. The tutorial code accumulates in order; if you copy a single section, keep the model definitions that precede it.

Setup: a two-parameter manufactured equilibrium
-----------------------------------------------

Consider a manufactured axisymmetric, purely poloidal model. The domain is a ``7 x 7`` grid with ``R in [0.2, 0.6] m`` and ``Z in [-0.2, 0.2] m``. The vacuum field is

.. code-block:: text

   psi_vac(R) = B0 * R^2 / 2,   B0 = 1 T

The pressure profile is set by a radial pressure gradient ``a`` and an anisotropy ratio ``r``:

.. code-block:: text

   p_perp(R)     = 5 Pa + a * R^2 / 2
   p_parallel(R) = r * p_perp(R)

The pressure feeds back into the poloidal flux through a prescribed rank-one Green response. With constants ``g = 0.6`` and ``C = 0.064``, the equilibrium field amplitude satisfies

.. code-block:: text

   B = (B0 + sqrt(B0^2 + 4 * g * a * C)) / 2
   psi(R,Z) = B * R^2 / 2

``psi`` has units of ``Wb/rad`` with the convention ``psi = R A_phi``; the full single-turn flux is ``2*pi*psi`` in ``Wb``. This is a **manufactured model**: the constants, the response and the observation locations are chosen to make the inference chain clear, and they do not correspond to any real device.

Three observation conventions run through the chapter:

- field arrays are indexed as ``[Z, R]``, while observation points are ordered as ``[R, Z]``;
- a flux request must explicitly choose ``raw_psi`` or ``magnetic_flux`` and state its unit;
- a pressure channel must state its unit explicitly; ``Pa`` is the unit accepted by the current implementation.

From the equilibrium state to predictions at observation points
---------------------------------------------------------------

Start with only the "forward" step: given parameters, compute predicted values at the observation points. ``synthesize_equilibrium_diagnostics`` samples the grid with a bilinear sampler and returns only the channels you explicitly request.

.. code-block:: python

   import numpy as np
   from scirel.diagnostics import synthesize_equilibrium_diagnostics

   B0, a_true, ratio_true = 1.0, 1.7, 1.6
   R, Z = np.meshgrid(np.linspace(0.2, 0.6, 7), np.linspace(-0.2, 0.2, 7))
   points = np.array([[R[2, 2], Z[2, 2]], [R[-2, -2], Z[-2, -2]]])

   def analytic_state(gradient, ratio):
       gain, C = 0.6, 0.064
       B = (B0 + np.sqrt(B0**2 + 4*gain*gradient*C)) / 2
       p_perp = 5.0 + gradient * R**2 / 2
       return {'psi': B*R**2/2, 'psi_unit': 'Wb/rad',
               'profiles': {'p_parallel': ratio*p_perp, 'p_perp': p_perp},
               'profile_units': {'p_parallel': 'Pa', 'p_perp': 'Pa'}}

   def predict(state, request):
       return synthesize_equilibrium_diagnostics(
           R=R, Z=Z, equilibrium=state, observations=request)

   request = {'flux_loops': {'points': points, 'quantity': 'magnetic_flux', 'unit': 'Wb'},
              'thomson': {'points': points,
                          'p_parallel': {'unit': 'Pa'}, 'p_perp': {'unit': 'Pa'}}}
   linked = predict(analytic_state(a_true, ratio_true), request)
   raw = predict(analytic_state(a_true, ratio_true),
                 {'flux_loops': {'points': points,
                                 'quantity': 'raw_psi', 'unit': 'Wb/rad'}})

   print("flux_loops (Wb) =", np.round(linked['flux_loops'], 9))
   print("raw psi (Wb/rad) =", np.round(raw['flux_loops'], 9))
   print("p_parallel (Pa) =", np.round(linked['thomson']['p_parallel'], 9))
   print("p_perp (Pa)     =", np.round(linked['thomson']['p_perp'], 9))
   print("units =", linked['units'])
   print("p_parallel/p_perp =",
         linked['thomson']['p_parallel'] / linked['thomson']['p_perp'])

Actual output:

.. code-block:: text

   flux_loops (Wb) = [0.3705327  0.94856371]
   raw psi (Wb/rad) = [0.05897211 0.1509686 ]
   p_parallel (Pa) = [8.15111111 8.38684444]
   p_perp (Pa)     = [5.09444444 5.24177778]
   units = {'flux_loops': 'Wb', 'thomson': {'p_parallel': 'Pa', 'p_perp': 'Pa'}}
   p_parallel/p_perp = [1.6 1.6]

At the first observation point, ``R = 0.3333 m``, ``raw_psi`` is ``0.05897211 Wb/rad``, while the full flux is ``0.37053270 Wb`` — exactly a factor of ``2*pi`` apart. The second point has a larger radius, so both quantities are larger. The pressure ratio at both points is exactly the input ``1.6``, because the profiles are constructed with the same scaling.

The name ``flux_loops`` is also easy to misread: the current entry point only samples the flux at these ``(R, Z)`` points. It does not integrate a loop along a contour, and it does not automatically multiply in coil turns or a reference-loop difference. ``thomson``, in turn, is a historical namespace: here it only means "sample the given profiles at points", not a Thomson-scattering instrument model. The two observation points happen to lie on grid nodes, so this section's sampling has no interpolation error; moving the points inside a cell introduces bilinear error.

**What this section does not establish**: unit labels in a prediction do not mean the input data have been correctly calibrated; ``Wb/rad`` is multiplied by ``2*pi`` only when the caller explicitly declares that convention; and no coil turns, reference-loop difference or instrument response are added automatically.

Turning mismatches into a fixed-order residual vector
-----------------------------------------------------

Once predictions exist, mismatches in different units still need to become one vector the optimizer can use. ``reduce_observation_residuals`` first freezes the observation layout, then computes ``(prediction - value) / sigma`` in a fixed order.

.. code-block:: python

   from scirel.diagnostics import reduce_observation_residuals

   observations = {
       'flux_loops': {'points': points, 'values': linked['flux_loops'], 'sigma': 1e-3,
                      'unit': 'Wb', 'quantity': 'magnetic_flux'},
       'thomson': {'points': points,
                   'p_parallel': {'values': linked['thomson']['p_parallel'],
                                  'sigma': 0.02, 'unit': 'Pa'},
                   'p_perp': {'values': linked['thomson']['p_perp'],
                              'sigma': 0.02, 'unit': 'Pa'}},
   }
   trial = predict(analytic_state(1.0, 1.2), request)
   reduced = reduce_observation_residuals(predicted=trial, observations=observations)

   print("residual_vector =", np.array2string(reduced['residual_vector'], precision=6))
   print("chi2 =", round(reduced['chi2'], 1))
   print("residual count =", reduced['residual_vector'].size)

Actual output:

.. code-block:: text

   residual_vector = [  -8.541339  -21.865827 -104.222222 -110.808889   -1.944444   -4.977778]
   chi2 = 23720.5
   residual count = 6

The vector order is fixed: first the two ``flux_loops``, then the two ``p_parallel``, then the two ``p_perp``; within each channel, the input's C order is preserved. A negative sign means the prediction is below the observation. Here ``sigma`` is a weight declared by the caller — ``1e-3 Wb`` for flux and ``0.02 Pa`` for pressure — so the same absolute mismatch is amplified more in the pressure channels. ``chi2`` is simply the sum of squares of this six-dimensional vector.

The initial point ``(a, r) = (1.0, 1.2)`` is far from the true values ``(1.7, 1.6)`` and the anisotropy ratio is off by the most, so the two ``p_parallel`` residuals are the largest; the flux residuals are only about ``-8.5`` and ``-21.9`` ``sigma``. This shows that the channels have different sensitivities to the parameters, but it **cannot** be used to decide which parameter is "more wrong".

**What this section does not establish**: ``chi2`` is not a p-value and not a goodness-of-fit test; there is no covariance, no degrees-of-freedom correction and no instrumental systematic error here. ``sigma`` is a declared value, not an estimate from repeated measurements. A large residual only means a large mismatch under this weighting and these parameters; it does not mean the physical model has been refuted.

One real forward trial: convergence, fixed-point residual, and failure penalty
------------------------------------------------------------------------------

The prediction in the previous section came from an analytic expression. In real inversion the forward is usually a numerical solver. Here we use the axisymmetric anisotropic Picard solver: given parameters, it iterates the force balance and returns ``psi``, the pressures, a convergence flag and the fixed-point residual.

.. code-block:: python

   from scirel.equilibrium import solve_axisymmetric_anisotropic_picard
   from scirel.inference import evaluate_anisotropic_trial

   def picard(payload, maxiter=150):
       gradient, ratio = payload['params']['gradient'], payload['params']['ratio']
       p_perp = 5.0 + gradient * R**2 / 2
       state = solve_axisymmetric_anisotropic_picard(
           r_grid=R, z_grid=Z, psi_vac=B0*R**2/2,
           g_psi=0.6*(R**2/2).ravel()[:, None]*np.ones((1, R.size)),
           tol=1e-12, maxiter=maxiter, relax=0.2,
           pressure_closure=lambda _b, _psi: {
               'p_parallel': ratio*p_perp, 'p_perpendicular': p_perp})
       return {**state, 'psi_unit': 'Wb/rad',
               'profiles': {'p_parallel': state['p_parallel'],
                            'p_perp': state['p_perpendicular']},
               'profile_units': {'p_parallel': 'Pa', 'p_perp': 'Pa'}}

   good = evaluate_anisotropic_trial(
       params={'gradient': 1.7, 'ratio': 1.6}, observations=observations,
       solver_config={'r_grid': R, 'z_grid': Z},
       equilibrium_solver=picard,
       diagnostic_evaluator=lambda payload: synthesize_equilibrium_diagnostics(payload["equilibrium"], payload["R"], payload["Z"], payload["observations"]),
       residual_reducer=reduce_observation_residuals)

   print("valid =", good['valid'], " status =", good['status'])
   print("chi2 =", f"{good['chi2']:.3e}")
   print("iterations =", good['equilibrium']['iterations'])
   print("fixed_point_residual =", f"{good['equilibrium']['fixed_point_residual']:.3e}")
   print("max |psi_picard - psi_analytic| =",
         f"{np.max(np.abs(good['equilibrium']['psi']
                          - analytic_state(1.7, 1.6)['psi'])):.3e}")

Actual output:

.. code-block:: text

   valid = True  status = valid
   chi2 = 1.314e-21
   iterations = 15
   fixed_point_residual = 3.759e-14
   max |psi_picard - psi_analytic| = 6.800e-15

With the parameters fixed at their true values, the Picard iteration converges in 15 iterations, the maximum difference between the numerical ``psi`` and the analytic manufactured solution is only ``6.8e-15``, and the fixed-point residual is ``3.8e-14``. These two numbers show that "the numerical forward really reproduces this manufactured state", which is also the prerequisite for recovering the parameters later; they are not, by themselves, validation against any experimental device.

Now look at a trial that is deliberately given only one iteration:

.. code-block:: python

   bad = evaluate_anisotropic_trial(
       params={'gradient': 1.0, 'ratio': 1.2}, observations=observations,
       solver_config={'r_grid': R, 'z_grid': Z},
       equilibrium_solver=lambda payload: picard(payload, maxiter=1),
       diagnostic_evaluator=lambda payload: synthesize_equilibrium_diagnostics(payload["equilibrium"], payload["R"], payload["Z"], payload["observations"]),
       residual_reducer=reduce_observation_residuals)

   print("valid =", bad['valid'], " status =", bad['status'])
   print("failure_reason =", bad['failure_reason'])
   print("penalty residuals =", bad['residuals'])
   print("chi2 =", bad['chi2'])

Actual output:

.. code-block:: text

   valid = False  status = forward_nonconvergence
   failure_reason = equilibrium solver did not converge
   penalty residuals = [1.e+12 1.e+12 1.e+12 1.e+12 1.e+12 1.e+12]
   chi2 = 6e+24

When the forward does not converge, neither the diagnostics nor the residual reduction are called; the entry point directly returns a six-dimensional positive penalty of the same size as the observation vector, keeping ``valid=False`` and an explicit status. ``1e12`` and ``6e24`` are numerical controls for the optimizer, not physical observations, and they are not proof that "this parameter set is infeasible" — they only say that this forward run produced no usable state.

**What this section does not establish**: ``valid`` for a single trial only says that this forward chain completed; a small fixed-point residual does not imply a small residual ``chi2``, and even less that the parameters are identifiable or optimal.

Fitting inside a bounded box from stratified initial values
-----------------------------------------------------------

The optimizer needs a starting point. ``sample_latin_hypercube`` draws one point from each stratum of each parameter and then combines them with random permutations, so the initial values do not all cluster in the middle of the box. ``n_samples`` must be a positive integer; a boolean raises ``ValueError`` instead of leaking a NumPy ``TypeError``.

.. code-block:: python

   from scirel.inference import sample_latin_hypercube, solve_direct_anisotropic_inversion

   design = sample_latin_hypercube(
       bounds={'gradient': (0.2, 3.0), 'ratio': (1.1, 2.5)},
       n_samples=8, seed=3)
   for row in design['initial_samples'][:3]:
       print(f"design gradient={row['gradient']:.6f} ratio={row['ratio']:.6f}")
   print("strata(gradient) =",
         sorted(int((row['gradient'] - 0.2)/2.8*8)
                for row in design['initial_samples']))

Actual output:

.. code-block:: text

   design gradient=2.451594 ratio=1.921838
   design gradient=2.817668 ratio=2.026226
   design gradient=0.955909 ratio=1.625261
   strata(gradient) = [0, 1, 2, 3, 4, 5, 6, 7]

With the random seed fixed, the eight samples of each coordinate fall exactly one per stratum; the permutations of the two coordinates are independent. This is an initial-value design, not a posterior distribution, and it does not mean that these points "cover the physically reasonable parameters".

Connecting the forward port, the diagnostic port and the fixed-size residual gives an end-to-end inversion:

.. code-block:: python

   fit = solve_direct_anisotropic_inversion(
       initial_params={'gradient': 1.0, 'ratio': 1.2},
       bounds={'gradient': (0.2, 3.0), 'ratio': (1.1, 2.5)},
       method='least_squares', n_initial_samples=8, seed=3, max_evaluations=140,
       observations=observations, solver_config={'r_grid': R, 'z_grid': Z},
       equilibrium_solver=picard,
       diagnostic_evaluator=lambda payload: synthesize_equilibrium_diagnostics(payload["equilibrium"], payload["R"], payload["Z"], payload["observations"]))

   print("best_parameters =", fit['best_parameters'])
   print("converged/optimizer/forward =",
         fit['converged'], fit['optimizer_converged'], fit['forward_converged'])
   print("chi2 =", f"{fit['chi2']:.3e}", " residual_size =", fit['residual_size'])
   print("scientific_evaluations =", fit['scientific_evaluations'],
         " valid_trial_count =", fit['valid_trial_count'])
   print("fixed_point_residual =", f"{fit['equilibrium']['fixed_point_residual']:.3e}")
   print("max flux increment =",
         f"{float(np.max(np.abs(fit['equilibrium']['psi'] - R**2/2))):.6f}")

Actual output:

.. code-block:: text

   best_parameters = {'gradient': 1.7000000000010203, 'ratio': 1.5999999999999683}
   converged/optimizer/forward = True True True
   chi2 = 9.200e-23  residual_size = 6
   scientific_evaluations = 27  valid_trial_count = 27
   fixed_point_residual = 3.765e-14
   max flux increment = 0.011070

The absolute error of both parameters is about ``1e-12`` and ``chi2`` drops to ``9.2e-23``. ``residual_size=6`` is frozen by the observation layout before optimization starts; ``scientific_evaluations=27`` includes the initial samples, numerical differences and the final re-evaluation; ``valid_trial_count=27`` says that all 27 scientific calls produced a valid forward. This clean case has no failed trials; the failure path was shown separately in the previous section. The final parameters, residual and state come from a fresh forward call at the end, not from values cached by the optimizer.

The last number, ``max flux increment = 0.011070``, is the maximum difference between the final ``psi`` and the vacuum field ``R^2/2``. It is nonzero, which shows that the pressure gradient really does change the flux through the Green response; if this number were zero, the flux observations would carry no information about ``gradient``.

**What this section does not establish**: this is a noiseless, same-model manufactured case; the high recovery accuracy is constructed, not experimental identifiability. The optimizer stopping only means that the local iteration ended; there is no covariance, Fisher information, confidence interval or proof of a global optimum here.

Tightening the bound: optimizer convergence does not imply a trustworthy fit
----------------------------------------------------------------------------

Tighten the upper bound of ``ratio`` from ``2.5`` to ``1.4`` so that it excludes the true value ``1.6``, leaving every other setting unchanged:

.. code-block:: python

   bounded = solve_direct_anisotropic_inversion(
       initial_params={'gradient': 1.0, 'ratio': 1.2},
       bounds={'gradient': (0.2, 3.0), 'ratio': (1.1, 1.4)},
       method='least_squares', n_initial_samples=8, seed=3, max_evaluations=140,
       observations=observations, solver_config={'r_grid': R, 'z_grid': Z},
       equilibrium_solver=picard,
       diagnostic_evaluator=lambda payload: synthesize_equilibrium_diagnostics(payload["equilibrium"], payload["R"], payload["Z"], payload["observations"]))

   print("best_parameters =", bounded['best_parameters'])
   print("converged/optimizer/forward =",
         bounded['converged'], bounded['optimizer_converged'],
         bounded['forward_converged'])
   print("chi2 =", f"{bounded['chi2']:.3e}")
   print("scientific_evaluations =", bounded['scientific_evaluations'])
   print("ratio at upper bound =",
         abs(bounded['best_parameters']['ratio'] - 1.4) < 1e-12)
   print("fixed_point_residual =",
         f"{bounded['equilibrium']['fixed_point_residual']:.3e}")

Actual output:

.. code-block:: text

   best_parameters = {'gradient': 2.303615923647581, 'ratio': 1.3999999999999997}
   converged/optimizer/forward = True True True
   chi2 = 4.915e+03
   scientific_evaluations = 30
   ratio at upper bound = True
   fixed_point_residual = 8.265e-14

All three "success" flags are still true: the optimizer stopped, the final forward is valid, and the fixed-point residual is small. But ``chi2`` is ``4915``, ``ratio`` sits on the upper bound ``1.4``, and ``gradient`` is pushed to ``2.30`` to compensate for the truncated anisotropy. This is not a broken solver; the best point in the feasible region simply lies on the boundary.

**What this section does not establish**: you cannot treat ``gradient = 2.30`` as an estimate of the true value, and you cannot conclude that the parameters are unidentifiable just because ``ratio`` lands on the bound. What happens here is a bounded projection: the true value lies outside the box, so the fit can only return the best point inside it. Distinguishing a "boundary effect" from "insufficient data" requires widening the bounds, examining the residual structure, and performing a separate identifiability analysis.

Which layer to use when
-----------------------

- You only want predictions from a given equilibrium state at specified points: :doc:`../reference/generated/scirel.diagnostics.equilibrium-synthesis-diagnostics`.
- You already have predictions and observations and only want fixed-order residuals and their sum of squares: :doc:`../reference/generated/scirel.diagnostics.observation-residuals`.
- You have your own forward, diagnostic and residual ports and only want one penalized trial: :doc:`../reference/generated/scirel.inference.anisotropic-trial-evaluation`.
- You only need a stratified initial-value design: :doc:`../reference/generated/scirel.inference.latin-hypercube-sampling`.
- You already have a ``trial_evaluator`` and only want bounded local optimization: :doc:`../reference/generated/scirel.inference.anisotropic-parameter-optimization`.
- You have forward and diagnostic ports and want the direct "observation → trial → bounded fit" path: :doc:`../reference/generated/scirel.inference.direct-anisotropic-inversion`.

Pitfalls and boundaries
-----------------------

- **Order is part of the contract.** Residuals go flux first, then ``p_parallel``, then ``p_perp``, flattened in C order inside each channel; swapping the order does not raise an error, but it makes ``chi2`` incomparable between different calls.
- **A unit label is not a unit conversion.** The ``unit`` of observations and predictions must agree; ``magnetic_flux`` is multiplied by ``2*pi`` only when the source ``psi`` is declared in ``Wb/rad``, and is returned unchanged when it is declared in ``Wb``.
- **``sigma`` is a declared weight.** It does not come from repeated measurements and contains no systematic error; ``chi2`` is only the algebraic sum of squares under that diagonal weighting.
- **The penalty is not physics.** ``1e12`` only makes invalid trials rank lower in optimization; it is not evidence of feasibility, identifiability or physical correctness.
- **Read the three kinds of "convergence" separately.** ``optimizer_converged`` is a numerical stop, ``forward_converged`` is the forward fixed point, and ``converged`` is their combined state; none of them means that the residual has reached an experimental threshold.
- **Bounds change the answer.** When the true value lies outside the box, the best point sticks to the boundary and distorts the other parameters; check whether ``best_parameters`` lies on a bound before interpreting the numbers.

The numbers in this chapter correspond only to this manufactured two-parameter model. Changing the Green response, the observation noise, the parameterization or the device means that the ``gradient``, ``ratio`` and ``chi2`` here cannot be reused directly. Complete parameter validation, exception types and the evidence boundary for larger parameter domains are on the API reference pages above; those pages are the contract-generated reference layer, while this chapter only tells one inference path clearly.

.. seealso::

   To continue with "how observation points are sampled from the grid", read :doc:`numerical-geometry`; to return to the domain introduction, read :doc:`/user-guide/index`.
