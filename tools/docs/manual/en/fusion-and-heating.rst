Fusion reactions and energy deposition: from DD neutron energy to a heating ledger
==================================================================================

This chapter has only three public relations, so it is written as one runnable small case rather than expanded as a function catalog. It follows three consecutive questions:

1. Given the velocities of two deuterons and a detector line of sight, how much energy does the neutron from the D(d,n)3He reaction have in the laboratory frame?
2. Given a fast ion's birth energy, the electron temperature and the ion mass, how much power does this local approximation assign to ions?
3. Given a ledger of power already absorbed by four species, how do the percentages close?

These three questions live at different levels: **single-reaction kinematics, model-given heating partition, and normalization bookkeeping for known power**. They can each be run, but they cannot automatically be assembled into a complete model containing reaction rates, particle trajectories and energy transport.

.. note::

   This chapter is a tutorial, not a contract summary. The full signatures, parameter units, failure behavior and applicability of the three functions are in the API reference pages at the end of the chapter; the code calls only public SciRel functions, and every number is an actual run result.

Preparation: reactions, energy ledger and units
-----------------------------------------------

The neutron branch of the DD reaction is

.. code-block:: text

   D + D -> n + 3He + 3.27 MeV

Here ``Q = 3.27 MeV`` is the total energy released by the reaction. The relative motion of the deuterons supplies additional kinetic energy, which is shared by the neutron and 3He by mass. The implementation first computes the centre velocity and the squared CM neutron speed:

.. code-block:: text

   V       = (v1 + v2) / 2
   v_rel   = v1 - v2
   E_avail = Q + (1/2) * (m_D/2) * |v_rel|^2
   E_cm    = m_He3 / (m_n + m_He3) * E_avail
   u^2     = E_cm / k_n

The detector vector ``d`` is a **laboratory-frame** line of sight from the reaction point to the detector. After the unit-norm gate, let ``n = d / |d|`` and write the laboratory neutron velocity along that ray as ``s*n``. It must satisfy

.. code-block:: text

   |s*n - V|^2 = u^2
   a = V . n
   b^2 = |V - a*n|^2
   s = a ± sqrt(u^2 - b^2)
   E_lab = 1000 * k_n * s^2   (keV)

The function returns an energy only when this laboratory ray has one distinct strictly positive root. A positive tangent is accepted; zero speed cannot reach the detector; an unreachable ray or two distinct positive roots raises ``ValueError`` because the single-value interface has no branch selector. The roots are intersections of a velocity sphere with a laboratory ray. The detector direction must not be substituted for a CM emission angle, and the result must not be written as a ``cos(theta)`` CM-angle formula.

Units need special care: both velocities are in **cm/s**, the detector direction is dimensionless, and the returned energy is in **keV**. Velocities and the detector vector must be in the same Cartesian system; the function performs no coordinate transformation. Complex or non-finite components, wrong shapes and detector norms outside ``1e-12`` are rejected.

Stationary reactants and laboratory rays
----------------------------------------------------------

With stationary reactants ``V=0``, every unit ray has one positive root and returns the mass-partition anchor:

.. code-block:: python

   from scirel.fusion import calculate_dd_neutron_lab_energy_kev as E
   still = E(reactant1_velocity_cm_s=(0.0, 0.0, 0.0),
             reactant2_velocity_cm_s=(0.0, 0.0, 0.0),
             detector_unit_vector=(1.0, 0.0, 0.0))
   v1, v2 = (1.0e8, 0.0, 0.0), (5.0e7, 0.0, 0.0)
   forward = E(reactant1_velocity_cm_s=v1, reactant2_velocity_cm_s=v2,
               detector_unit_vector=(1.0, 0.0, 0.0))
   backward = E(reactant1_velocity_cm_s=v1, reactant2_velocity_cm_s=v2,
                detector_unit_vector=(-1.0, 0.0, 0.0))
   print(still, forward, backward)

The outputs are ``2450.475899416``, ``2624.190695809`` and ``2284.596359041 keV``. Both forward and backward rays are reachable with one positive root. If the boost places a ray through the interior of the velocity sphere, two distinct positive roots exist; the single-value entry rejects that ambiguity instead of selecting a branch silently.

Scanning the detector direction: energy is not isotropic
----------------------------------------------------------

For ``v1=(1.3e8,0,0)`` and ``v2=0``, scan laboratory rays in the ``x-y`` plane:

.. code-block:: text

     0 deg   2606.618 keV
    30 deg   2585.762 keV
    60 deg   2529.617 keV
    90 deg   2454.875 keV
   120 deg   2382.341 keV
   150 deg   2330.613 keV
   180 deg   2311.965 keV

Energy changes with the line of sight, but the 90-degree value is not the average of the forward and backward values; non-collinear values come from the quadratic intersection of the velocity sphere with the laboratory ray. This is a line-of-sight energy curve for a fixed velocity pair, not a measured angular distribution or a DD spectrum; the function computes no reaction rate, yield, angular weight or subsequent transport.

From reaction energy to heating: fast-ion partition
---------------------------------------------------

Knowing the neutron energy of a single reaction is still not knowing where the power goes. The next relation answers a more local question: for a fast ion with birth energy ``E_birth`` in a plasma with electron temperature ``T_e``, how much power does the prescribed local approximation assign to ions?

.. code-block:: python

   from scirel.plasma import fast_ion_fractional_heating

   for birth in (0.0, 10.0, 100.0, 1000.0, 3500.0):
       fraction = fast_ion_fractional_heating(birth, 10.0, 2.0)
       print(f"E_birth = {birth:6.0f} keV  f_i = {fraction:.6f}")

   a = fast_ion_fractional_heating(100.0, 1.0, 2.0)
   b = fast_ion_fractional_heating(1000.0, 10.0, 2.0)
   print(f"same x^2: {a:.9f} vs {b:.9f}")
   print(f"alpha, 3.5 MeV, T_e=10 keV: {fast_ion_fractional_heating(3500.0, 10.0, 4.0):.6f}")

Actual output:

.. code-block:: text

   E_birth =      0 keV  f_i = 1.000000
   E_birth =     10 keV  f_i = 0.995559
   E_birth =    100 keV  f_i = 0.883525
   E_birth =   1000 keV  f_i = 0.308602
   E_birth =   3500 keV  f_i = 0.110967
   same x^2: 0.308601931 vs 0.308601931
   alpha, 3.5 MeV, T_e=10 keV: 0.199848

The relation is

.. code-block:: text

   x^2 = E_birth / (10 * m_fast * T_e)
   f_i = (2 / x^2) * integral_0^x t / (1 + t^3) dt

``E_birth`` and ``T_e`` are in keV, ``m_fast`` is in amu, and ``f_i`` is dimensionless. It gives only the ion share; in this two-channel ledger the electron share can be written as ``1 - f_i``, but the function does not return an electron share and does not simulate the slowing-down history of either channel.

A few numbers can be read as follows: when the birth energy is well below ``10 * m_fast * T_e``, ``f_i`` approaches 1; as the energy rises, ``f_i`` falls. At ``T_e = 10 keV`` and a deuteron mass of 2 amu, ``f_i`` is 0.9956 at 10 keV, 0.8835 at 100 keV, and 0.3086 at 1000 keV. A 3500 keV deuteron gives 0.1110; an alpha with the same 3.5 MeV but mass 4 amu gives 0.1998 because the mass also enters ``x^2``.

``100 keV, T_e=1, m=2`` and ``1000 keV, T_e=10, m=2`` both give ``x^2=5``, so ``f_i`` agrees to ``0.308601931``. This is a check: the function depends on these three inputs only through ``x^2``, and is not separately fitting ``E``, ``T_e`` and ``m``.

``E_birth = 0`` returns exactly 1.0, the continuous limit of the integral as ``x -> 0``; it does not mean that zero-energy fast ions really exist. It is a mathematical boundary, not an experimental point.

What this section does not establish: ``f_i`` is the partition fraction of the given local approximation, not a particle-trajectory or slowing-down simulation; it has no spatial transport, profile evolution, collision operator or experimental calibration. It also does not tell you where or how fast the power is deposited. The 10 in ``x^2`` is part of this approximation, not a universal constant.

From a power ledger to percentages: absorbed shares
---------------------------------------------------

The third relation handles another level: if the **already absorbed power** of four species is given, how do we close them into percentages?

.. code-block:: python

   import numpy as np
   from scirel.diagnostics import compute_species_absorption_fraction

   ledger = [3.0, 2.0, 0.8, 0.2]   # MW, in the four-species order supplied by the caller
   out = compute_species_absorption_fraction(ledger)
   print("total:", out["total_power"], "MW")
   print("percent:", np.round(out["species_fraction_percent"], 6))
   print("sum:", out["total_fraction_percent"])
   print("residual:", out["fraction_sum_residual_percent"])
   print("branch:", out["branch"])

   try:
       compute_species_absorption_fraction([0.0, 0.0, 0.0, 0.0])
   except ValueError as exc:
       print("zero total ->", exc)

Actual output:

.. code-block:: text

   total: 6.0 MW
   percent: [50.       33.333333 13.333333  3.333333]
   sum: 99.99999999999999
   residual: -1.4210854715202004e-14
   branch: nonzero_total
   zero total -> zero total_power has no source-defined percentage result

The four numbers are interpreted in the caller's order; the function does not infer species names and does not reorder them. The total power is 6.0 MW, and the shares are 50%, 33.333333%, 13.333333% and 3.333333%. The returned share sum is ``99.99999999999999`` with residual ``-1.42e-14``. This residual is double-precision rounding, not lost power; the function returns the sum of the **actually returned percentages**, not the sum of unrounded rational numbers.

Zero total power raises ``ValueError``: percentage shares are undefined. Negative ledger entries are allowed and represent a signed contribution; the function reports them as computed and does not clip them. Extreme cancellation can amplify the rounding of individual shares, and the returned sum may then deviate noticeably from 100; ``fraction_sum_residual_percent`` exposes exactly this situation.

What this section does not establish: this function does not compute absorption physics. It does not know which species the four entries are, and does not verify whether the powers are physical. It only closes the ledger; the absorbed powers must be supplied by you or by an upstream model.

What the three layers cannot assemble automatically
---------------------------------------------------

Placing the three relations side by side easily creates an illusion: can we compute all the way from DD neutron energy to heating and absorption? Not at present. They answer questions at different levels:

.. list-table::
   :header-rows: 1

   * - relation
     - input
     - output
     - does not provide
   * - DD neutron laboratory-frame energy
     - two deuteron velocities, detector direction
     - one neutron energy (keV)
     - reaction rate, angular distribution, subsequent transport
   * - fast-ion heating partition
     - birth energy, electron temperature, fast-ion mass
     - ion partition fraction (dimensionless)
     - trajectories, profiles, experimental calibration
   * - species absorption shares
     - four already absorbed powers
     - percentages and closure residual
     - absorption physics, species identification

A complete energy-deposition chain still needs at least a reaction rate ``<sigma v>``, a distribution function, an angular distribution, a slowing-down/deposition profile and a transport model. Each of the three functions in this chapter covers only a small segment; before multiplying or chaining them, identify which segment is missing.

Common misuse and boundaries
----------------------------

- **Velocity units**: the DD entry point uses cm/s, not m/s. Passing the wrong unit does not raise an error, but the energy is off by about ``10^4``.
- **Detector vector**: it must be a unit vector with tolerance ``1e-12``; a non-unit vector is rejected and is not normalized automatically. Velocities and the detector vector must be in the same Cartesian system.
- **Reaction channel**: ``Q = 3.27 MeV`` corresponds only to D(d,n)3He. Do not apply it to D(d,p)T or D-T (the latter has ``Q`` about 17.6 MeV).
- **Relativity**: the relation is non-relativistic and has no velocity cutoff; but at very large velocities the non-relativistic approximation itself no longer applies.
- **Angular weights**: the function returns only energy, not an angular-distribution weight. A higher forward energy does not imply a larger forward yield.
- **Heating inputs**: ``E_birth`` may be 0; ``T_e`` and ``m_fast`` must be strictly positive. ``f_i = 1`` at ``E_birth = 0`` is a mathematical limit, not a physical particle.
- **Meaning of heating**: ``f_i`` is the ion partition fraction of the local approximation, not an "ion temperature" or a "deposited power". To obtain power, multiply by the fast-ion power you have, which is another model input.
- **Ledger**: it must contain exactly four entries; zero total power fails; negative entries are signed contributions, not errors. Under extreme cancellation, inspect ``fraction_sum_residual_percent`` and do not assume the sum is close to 100.
- **Residual is not error**: the percentage-closure residual is a rounding quantity, not an error estimate of the absorption model.

API references and complete failure behavior for the three functions:

- :doc:`../reference/generated/scirel.fusion.dd-neutron-lab-energy`
- :doc:`../reference/generated/scirel.plasma.fast-ion-heating`
- :doc:`../reference/generated/scirel.diagnostics.species-absorption-fraction`

.. seealso::

   If you care about reaction rates, collision cross sections or distribution functions, return to :doc:`/user-guide/index` and choose the atomic-collisions or kinetic-transport domain; the three relations in this chapter do not replace those models and cannot by themselves form a closed energy-transport loop.
