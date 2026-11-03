Plasma equilibrium: from a pressure profile to flux feedback
==============================================================

This chapter answers one concrete question: **given a midplane pressure profile, how do we turn it into a pressure relation on flux, and use the Green response of the toroidal current to perform one (or a bounded number of) equilibrium feedback steps?**

We follow a continuous path: first build ``P(psi)`` and ``dP/dpsi`` from pressure samples, then perform one Picard update with a real circular-loop response matrix, then enter the composite entry point with two residual gates, and finally use a controlled diagonal response to explain what "convergence" actually checks. Every step shows its actual output and states what it does not prove.

.. note::

    This chapter is a tutorial, not a contract summary. The complete signature, parameter units, failure behavior and applicability of each function are on the API reference pages linked at the end of the chapter; the tutorial code uses only public SciRel functions.

Setup: coordinates, units and a pressure profile
--------------------------------------------------

Use cylindrical coordinates ``(R, phi, Z)`` and assume axisymmetry. The poloidal flux is

.. code-block:: text

   psi(R, Z) = R * A_phi

Its unit is ``Wb/rad``; the toroidal current ``I`` is in ``A``; the Green response ``g_psi`` maps current to ``psi`` and has units ``Wb/rad/A``. None of the formulas in this chapter carries an extra ``2*pi``; if you are used to whole-turn flux, you must convert the factor and the unit together yourself.

In this library's discrete convention the pressure part of the equilibrium is written ``P = P(psi)``. The discrete current is

.. code-block:: text

   I_target = R * (dP/dpsi) * dR * dZ

This is the discrete closure relation that distributes toroidal current onto each grid cell; it is not a complete Grad–Shafranov solution by itself. The total flux has two parts:

.. code-block:: text

   psi_next = g_psi @ I_new + psi_vac

First define a linearly decreasing pressure profile on a regular ``[Z, R]`` grid that is exactly zero at ``R=0.8``:

.. code-block:: python

   import numpy as np
   from scirel.equilibrium.pressure_flux_state import build_pressure_flux_state

   r_grid, z_grid = np.meshgrid(
       np.linspace(0.2, 0.8, 4),
       [-0.1, 0.0, 0.1],
   )

   def pressure(radius):
       return max(1.0e6 * (1.0 - radius / 0.8), 0.0)

   for radius in np.linspace(0.2, 0.8, 4):
       print(f"R={radius:.1f}  P={pressure(radius):.0f} Pa")

Actual output:

.. code-block:: text

   R=0.2  P=750000 Pa
   R=0.4  P=500000 Pa
   R=0.6  P=250000 Pa
   R=0.8  P=0 Pa

The zero here is an **exact zero**, not an approximate zero such as ``1e-12``; the boundary test below depends on this. The grid must also contain a complete ``Z=0`` row, because pressure samples are read only from that midplane.

What this section cannot establish: the physical plausibility of the pressure profile, the real geometry of a device, or that ``psi = R`` is the flux of some real equilibrium. We have only chosen a self-consistent set of input conventions.

From pressure samples to ``dP/dpsi``
--------------------------------------

``build_pressure_flux_state`` does three things: it sorts the midplane samples by physical radius; it takes the flux prefix before the first exact zero-pressure point; and it fits ``P(psi)`` with a cubic spline and provides ``dP/dpsi``. It also returns an all-zero current vector, which is only a placeholder for "not yet solved", not an equilibrium current.

.. code-block:: python

   state = build_pressure_flux_state(
       r_grid, z_grid, r_grid.copy(), pressure
   )
   print("dP/dpsi [Pa/(Wb/rad)]:")
   print(state["pressure_derivative"].reshape(3, 4).round(1))
   print(f"psi_edge = {state['psi_edge']:.6f} Wb/rad")
   print(f"limiter_index = {state['limiter_index']}")
   print("psi_samples =", state["pressure_of_psi"]["psi_samples"])

Actual output:

.. code-block:: text

   dP/dpsi [Pa/(Wb/rad)]:
   [[-1250000. -1250000. -1250000. -1250000.]
    [-1250000. -1250000. -1250000. -1250000.]
    [-1250000. -1250000. -1250000. -1250000.]]
   psi_edge = 0.800000 Wb/rad
   limiter_index = 3
   psi_samples = [0.2 0.4 0.6 0.8]

Because here ``psi = R``, we have ``P = 1e6 * (1 - psi/0.8)`` and the derivative is constantly ``-1.25e6 Pa/(Wb/rad)``. The three Z rows are identical because the input flux has not yet been changed by the current; this does not mean the two-dimensional equilibrium is satisfied. ``limiter_index = 3`` is the 4th point (counting from 0) after sorting the midplane samples by radius, not an index into a C-order flattened array and not a grid row number. ``psi_edge = 0.8`` comes from the first exact zero-pressure sample.

The spline inside ``pressure_of_psi`` extrapolates as zero outside the sample interval; the derivative is zeroed in cells with ``psi > psi_edge``. This truncation is a discrete convention, not something derived automatically from a physical boundary condition.

What this section cannot establish: that ``dP/dpsi`` equals this constant over the whole two-dimensional region; that pressure remains outside the zero-pressure boundary; or that a spline fit can replace a real pressure-transport model. It only states what the derivative is under this set of samples and this truncation rule.

One Picard update: current, Green response and residual
---------------------------------------------------------

Now supply a vacuum response matrix. ``get_gpsi`` treats every point on the grid as a circular-loop source of unit current and returns the ``psi = R * A_phi`` response at the target points; the diagonal is zero because the self-field of a line current is not part of this discrete response. A real device of course needs a more appropriate vacuum or equilibrium response; here we use this one to get the "current -> flux" step working.

.. code-block:: python

   from scirel.electromagnetism import get_gpsi
   from scirel.equilibrium.isotropic_picard_step import pressure_flux_picard_step

   g_psi = get_gpsi(r_grid, z_grid)
   step = pressure_flux_picard_step(
       r_grid, z_grid, r_grid.copy(), r_grid.copy(), g_psi,
       state["pressure_derivative"], state["psi_edge"],
       state["zero_currents"], 0.0,
   )
   print("plasma_currents [A]:")
   print(step["plasma_currents"].reshape(3, 4).round(1))
   print("psi_next [Wb/rad]:")
   print(step["psi_next"].round(6))
   print(f"residual = {step['residual']:.6e}")

Actual output:

.. code-block:: text

   plasma_currents [A]:
   [[ -5000. -10000. -15000. -20000.]
    [ -5000. -10000. -15000. -20000.]
    [ -5000. -10000. -15000. -20000.]]
   psi_next [Wb/rad]:
   [[0.197026 0.389587 0.581105 0.77836 ]
    [0.196783 0.388643 0.57915  0.77572 ]
    [0.197026 0.389587 0.581105 0.77836 ]]
   residual = 6.901919e-02

The current is exactly ``-25000 * R``: the cell area is ``dR * dZ = 0.2 * 0.1 = 0.02``, the derivative is ``-1.25e6``, so ``R * (-1.25e6) * 0.02 = -25000 R``. The minus sign comes from the pressure decreasing with ``psi``. At the outer midplane the flux drops from ``0.8`` to about ``0.77836``; the top and bottom rows differ slightly from the midplane because the Green matrix couples currents at different Z positions.

``residual = 6.9e-2`` is

.. code-block:: text

   ||psi_next - psi_state||_2 / |psi_edge|

It measures "how much this step changed the flux", not an already-converged error, and not a deviation from a real equilibrium. For a single step with ``relax=0`` it only describes the step size.

What this section cannot establish: that one more step will converge; that this Green response is adequate for the device; or that the sign of the current already corresponds to the correct physical toroidal direction. It only demonstrates that one current assembly and one Green contraction are finite and reproducible on this set of inputs.

Composite entry point: why "running the iterations" is not equilibrium
------------------------------------------------------------------------

``solve_isotropic_pressure_flux`` puts the steps above into a bounded loop and checks two residuals at the same time:

- ``residual``: the relative norm of the flux update between consecutive iterations;
- ``closure_residual``: the relative difference between the current and the pressure target current rebuilt from the new flux.

Only when both are below ``tol`` is the run considered converged. Below we again use the same ``get_gpsi`` response, with ``relax=0.5`` and ``maxiter=20``:

.. code-block:: python

   from scirel.equilibrium import solve_isotropic_pressure_flux

   result = solve_isotropic_pressure_flux(
       r_grid=r_grid, z_grid=z_grid, pressure_of_radius=pressure,
       psi_vac=r_grid.copy(), g_psi=g_psi,
       tol=1e-8, maxiter=20, relax=0.5,
   )
   print(f"status = {result['status']}")
   print(f"iterations = {result['iterations']}")
   print(f"residual = {result['residual']:.6e}")
   print(f"closure_residual = {result['closure_residual']:.6e}")
   print(f"failure_reason = {result['failure_reason']}")
   print("last update residuals:", np.round(result["residual_history"][-4:], 6))
   print("last closure residuals:", np.round(result["closure_residual_history"][-4:], 6))

Actual output:

.. code-block:: text

   status = maxiter
   iterations = 20
   residual = 7.796787e-03
   closure_residual = 1.912028e-01
   failure_reason = maxiter_reached
   last update residuals: [0.010253 0.007003 0.008676 0.007797]
   last closure residuals: [0.334588 0.499996 0.372273 0.191203]

This did not converge. ``iterations = 20`` only says the budget was used up; ``status = maxiter`` is the conclusion. The update residual is hovering around ``1e-2``, but the closure residual is still oscillating between ``0.19`` and ``0.50``: the current cannot reproduce the pressure target rebuilt from the updated flux. The reason is not that some number was "computed wrongly", but that this combination is not yet self-consistent: the flux produced by ``get_gpsi`` changes the midplane shape so that it is no longer simply ``psi = R``, and the spline derivative rebuilt from the same pressure samples therefore drifts away from the original linear derivative; at the same time the ``relax=0.5`` damping keeps the current behind the target. Both residuals must decrease together; looking only at the smaller update residual would wrongly suggest that "it is almost converged".

What this section cannot establish: that this physical model is necessarily invalid, or that another device would fail the same way. It shows that the given pressure profile, Green response, spline representation and damping strategy do not satisfy both gates at once on this set of discrete inputs; nor may ``closure_residual`` be used as an experimental error or stability criterion.

A controlled convergence case: what the residual gates check
--------------------------------------------------------------

To separate "iteration algebra" from "whether the vacuum response is appropriate", replace the response with a diagonal matrix only:

.. code-block:: text

   g_psi = 4.0e-8 * I

It means that each cell's current produces a little flux only at its own location; it is obviously not a real vacuum field and is used only to isolate the numerical path. All other inputs stay the same:

.. code-block:: python

   controlled = solve_isotropic_pressure_flux(
       r_grid=r_grid, z_grid=z_grid, pressure_of_radius=pressure,
       psi_vac=r_grid.copy(),
       g_psi=4.0e-8 * np.eye(r_grid.size),
       tol=1e-10, maxiter=20, relax=0.0,
   )
   print(f"status = {controlled['status']}")
   print(f"iterations = {controlled['iterations']}")
   print(f"residual = {controlled['residual']:.6e}")
   print(f"closure_residual = {controlled['closure_residual']:.6e}")
   print("psi midplane [Wb/rad]:", controlled["psi"][1].round(6))
   print("currents midplane [A]:", controlled["plasma_currents"][1].round(2))
   print("update history:", np.round(controlled["residual_history"], 12))

Actual output:

.. code-block:: text

   status = converged
   iterations = 4
   residual = 2.386091e-12
   closure_residual = 1.005293e-12
   psi midplane [Wb/rad]: [0.1998   0.3996   0.599399 0.799199]
   currents midplane [A]: [ -5005.01 -10010.02 -15015.03 -20020.04]
   update history: [2.37408233e-03 2.37646100e-06 2.38100000e-09 2.00000000e-12]

The diagonal response writes the flux as ``psi = (1 - eps) * R``; substituting into ``P(psi)`` changes the derivative to ``-1.25e6/(1 - eps)``, so the current is ``-25000 R/(1 - eps)`` and the fixed point satisfies ``eps ≈ 1e-3``. The contraction factor of the iteration is about ``4e-8 * 25000 = 1e-3``, so the update residual shrinks by about a factor of one thousand per step and reaches ``1e-12`` after four steps. The returned ``psi`` and current do correspond to ``eps ≈ 0.001``: the outer edge is ``0.8 * 0.999 ≈ 0.7992`` and the current is about ``-5005 A`` (not ``-5000 A``).

What this section cannot establish: that the diagonal response describes a real electromagnetic field; that this fixed point is the device equilibrium; or that "converged" means a unique solution or a stable equilibrium. ``converged`` only says that, under this set of discrete inputs and these two residual gates, the iteration stopped and satisfied both criteria at once. Whether it converges with a real response still has to be checked by an actual computation like the previous section.

Common pitfalls
-----------------

- **Exact midplane and exact zero boundary**: the ``Z=0`` row must be complete, and the first zero-pressure sample must be exactly zero. Replacing zero with ``1e-12`` is rejected.
- **Flux-coordinate factor**: ``psi`` is ``R * A_phi`` (per radian), and the Green matrix and ``dP/dpsi`` must use the same coordinate. Do not mix whole-turn webers with per-radian values, and do not add an extra ``2*pi``.
- **Meaning of ``limiter_index``**: it is the index of a midplane sample after sorting by physical radius, not a C-order flattened index; the storage order may be reversed while the physical traversal order stays the same.
- **Direction and dtype of ``plasma_mask``**: when the boolean mask is true it **suppresses** the pressure derivative of that cell; it is not a switch that "marks the plasma interior". The boundary is still determined by the first exact zero-pressure point. Fixed masks and callable results must be true boolean arrays; integer/float masks are rejected instead of silently converted.
- **Residuals are not errors**: ``residual`` is the normalized norm of the difference between consecutive flux states, and ``closure_residual`` is the difference between the current and the pressure target; both being small only says the discrete equations close on this set of inputs, not that the model is correct.
- **Do not use ``relax=1`` to freeze the iteration**: the composite entry requires ``0 <= relax < 1``; ``relax=1`` keeps the old current without forming an update and must not be treated as a "fully implicit" step.
- **``maxiter`` is a budget**: when ``status = maxiter`` the final state is only the state after the budget is exhausted; ``iterations`` must not be read as a convergence count.

Which function to use
-----------------------

- You only want to turn a midplane pressure profile into ``P(psi)`` and ``dP/dpsi``: use :doc:`../reference/generated/scirel.equilibrium.pressure-flux-state`.
- You already have flux, a pressure derivative and a Green matrix and only want to see one current/flux update and its residual: use :doc:`../reference/generated/scirel.equilibrium.isotropic-picard-step`.
- You want to run a bounded pressure-current feedback and check two residuals at once: use :doc:`../reference/generated/scirel.equilibrium.isotropic-pressure-flux`.
- You need to construct or check a vacuum circular-loop response matrix: use :doc:`../reference/generated/scirel.electromagnetism.loop-flux-matrix`.
- You want to see how anisotropic pressure enters force balance and toroidal current instead of an isotropic closure: continue with :doc:`../reference/generated/scirel.equilibrium.anisotropic-force-balance` and :doc:`../reference/generated/scirel.equilibrium.anisotropic-toroidal-current`; they are not the same model as the ``P(psi)`` single step in this chapter.
- You want to diagnose iteration residuals separately: use :doc:`../reference/generated/scirel.diagnostics.picard-flux-residual`.

Complete parameters, failure behavior, applicability and verification boundaries
----------------------------------------------------------------------------------

The numbers in this chapter correspond only to this discrete setup: a regular ``[Z, R]`` grid, a complete ``Z=0`` row, a nonnegative midplane pressure that reaches zero exactly, at least four strictly increasing flux-prefix samples, and a caller-supplied square Green response. The functions do not verify for you the physical plausibility of the grid, the origin of the pressure profile, whether the Green matrix comes from a real vacuum field, and they do not prove continuum-limit convergence, MHD stability or confinement performance.

The composite entry point only guarantees that, for the given inputs, it performs bounded feedback and reports two residuals; ``converged`` is not a synonym for "a physically correct equilibrium", and ``maxiter`` is not proof that "the model failed". For exception types, parameter shapes, units and evidence over a larger parameter domain, enter the concrete function pages from the API reference of this chapter.

This chapter does not cover anisotropic force balance, anisotropic Picard feedback, mirror-constrained closures, tabulated pressure closures or reduced Hall drift; each has its own pressure tensor, boundary and stopping condition, and the ``dP/dpsi`` or residuals here cannot be applied to them directly.

.. seealso::

   Continue with :doc:`../reference/generated/scirel.equilibrium.axisymmetric-anisotropic-picard` to see how anisotropic current and flux feedback are combined; or return to :doc:`/user-guide/index` to choose another domain.
