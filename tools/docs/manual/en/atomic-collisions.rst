Atomic collisions: from one cross section to a local collision frequency
========================================================================

This chapter follows one question: **given a hydrogen plasma with a temperature, density and velocity mesh, how do we get from a charge-exchange cross section to an interpretable local collision frequency?**

The path is continuous:

.. code-block:: text

   cross section sigma(E)
     -> energy-resolved <sigma v> on a Maxwellian target
     -> four-family collision matrices SIG
     -> Alpha fields
     -> Omega and nu

This path covers only part of the collision processes of atomic hydrogen. It is not a complete collisional-radiative model, and it does not include rate-coefficient fits, Saha populations, every branch of the elastic cross sections, or a parallel implementation for molecular hydrogen; those entry points are described separately at the end of the chapter.

Conventions: energies in eV, cross sections in m², rate coefficients in m³/s, densities in m^-3; the velocity mesh is normalized by the thermal speed ``Vth``; ``Omega`` is in m^-1 and ``nu`` in s^-1. The code below calls only public SciRel functions, and every numerical output was actually produced by running the code in the repository ``.venv``, not written by hand as an illustration.

From energy to cross section: branches and endpoints first
----------------------------------------------------------

The H + H+ charge-exchange cross section now defaults to a **continuous composite**: the nine-coefficient Janev logarithmic polynomial below 12.673175 keV, followed by the Lindsay & Stebbings 2005 Table 1 recommended fit through 250 keV. ``freeman=True`` retains the independent Freeman-Jones analytic branch as a comparison entry through 100 keV only:

.. code-block:: text

   Composite: E <= 12.673175 keV:
              exp(polyval(log(E), a)) * 1e-4

              E > 12.673175 keV:
              (4.15 - 0.531 ln(E_keV))^2
              * (1 - exp(-67.3/E_keV))^4.5 * 1e-20

   Freeman:   1e-4 * 0.6937e-14 * (1 - 0.155 log10(E))^2
              / (1 + 0.1112e-14 E^3.3)

The default composite is evaluated on ``[0.1, 2.5e5]`` eV and joins the two fits continuously at 12.673175 keV. The Freeman branch clips to ``[0.1, 1e5]`` eV. A positive energy above the selected upper edge emits a ``RuntimeWarning`` and returns the endpoint; below 0.1 eV the lower endpoint is returned silently. Negative energies are rejected.

.. code-block:: python

   import warnings
   import numpy as np
   from scirel.collisions import (
       evaluate_atomic_hydrogen_charge_exchange_cross_section as cx_h,
       evaluate_molecular_hydrogen_charge_exchange_cross_section as cx_h2,
   )

   energy = np.array([1.0, 10.0, 100.0, 1.0e3, 1.0e4])
   composite = cx_h(energy)
   freeman = cx_h(energy, freeman=True)
   molecular = cx_h2(energy)
   print("E/eV   H+H+ composite   H+H+ Freeman   H2+H2+")
   for e, a, f, m in zip(energy, composite, freeman, molecular):
       print(f"{e:8.0f}  {a*1e20:15.3f}  {f*1e20:13.3f}  {m*1e20:7.3f}")

   hi = cx_h(np.array([3.0e4, 1.0e5]))
   print("high-energy cross sections", np.array2string(hi, precision=6))
   lo = cx_h(np.array([0.01, 0.1]))
   print("clip low", lo[0] == lo[1], f"{lo[0]:.6e}")
   with warnings.catch_warnings(record=True) as caught:
       warnings.simplefilter("always")
       top = cx_h(np.array([3.0e5, 2.5e5]))
   print("clip high", top[0] == top[1], f"{top[0]:.6e}", "warnings", len(caught))

   try:
       cx_h(np.array([1.0, -0.5]))
   except ValueError as error:
       print(type(error).__name__, error)
   try:
       cx_h(energy, freeman=np.ones((2, 2)))
   except ValueError as error:
       print(type(error).__name__, error)

Actual output (cross-section values are in units of 1e-20 m²):

.. code-block:: text

   E/eV   H+H+ composite   H+H+ Freeman   H2+H2+
          1           60.348         69.370   12.959
         10           46.315         49.532   12.099
        100           31.434         33.027    7.581
       1000           17.441         19.855    4.771
      10000            8.979          9.844    6.048
   high-energy cross sections [3.316599e-20 1.170723e-21]
   clip low True 7.296111e-19
   clip high True 2.236413e-23 warnings 1
   ValueError energy_ev must be nonnegative
   ValueError freeman must be a scalar branch selector, not an array

At the five low-energy points the default remains the Janev value; at 30 and 100 keV it becomes ``3.316599e-20`` and ``1.170723e-21`` m² respectively instead of repeating the 20.1 keV endpoint. The paper states about ``±11%`` reliability above 6 keV and separately records an almost 30% theory-versus-measurement discrepancy at 100 keV; those are not one combined uncertainty budget.

The Freeman branch is about 15% above the default at low energy, about 17% below it at 100 keV, and stops at 100 keV. ``freeman=True`` is therefore only for an explicit comparison with that older fit. Endpoint checks show that ``E=0.01`` and ``E=0.1`` are exactly equal; the default ``E=3.0e5`` and ``E=2.5e5`` values are exactly equal with one warning. Negative energy and array-valued ``freeman`` are rejected before evaluation.

This section does not establish that these are rate coefficients, that the composite is a new experimental fit, that the Freeman difference is an uncertainty, or that the value above 250 keV is a valid extrapolation.

Putting the cross section on a Maxwellian target: energy-resolved <sigma v>
---------------------------------------------------------------------------

Next we place the cross section on a discrete cylindrical velocity mesh. A monoenergetic particle moving along the axial direction ``vx`` crosses a Maxwellian target at temperature ``T_target``; the target is discretized on a ``(vr, vx)`` mesh, and the cell volumes are supplied by the caller. The contract's rate is

.. code-block:: text

   vth = sqrt(2 e Tnorm / (m_target m_H))
   f_target(vr,vx) ∝ exp(-(vr^2 + vx^2) Tnorm / T_target)
   rate(E) = vth * sum(volume * sigma(E_rel) * v_rel * f_target)

The collision energy is constructed with the **incident particle mass** ``particle_mass_amu``, not the reduced mass; that is the convention of this operator. The target distribution is normalized by the caller's cell volumes, so multiplying every volume by the same constant does not change the result.

.. code-block:: python

   import numpy as np
   from scirel.collisions import (
       average_cross_section_over_maxwellian,
       evaluate_atomic_hydrogen_charge_exchange_cross_section as cx_h,
   )

   dvr = 3.5 / 24
   dvx = 7.0 / 36
   vr = (np.arange(24) + 0.5) * dvr
   vx = (np.arange(36) + 0.5) * dvx - 3.5
   M_H = 1.6726231e-27
   e = 1.602177e-19
   vth = np.sqrt(2.0 * e * 20.0 / (1.0 * M_H))
   volume = np.outer(vr * dvr, np.full(36, dvx)) * vth**3
   beam = np.array([0.0, 1.0, 10.0, 100.0])
   rate = average_cross_section_over_maxwellian(
       particle_energy_ev=beam,
       particle_mass_amu=1.0,
       target_temperature_ev=10.0,
       target_mass_amu=1.0,
       vx=vx, vr=vr, tnorm_ev=20.0,
       cylindrical_volume=volume,
       cross_section_m2=cx_h,
   )
   print(f"vth = {vth:.6e} m/s")
   print("E_beam/eV   <sigma v>/(m^3/s)")
   for E, R in zip(beam, rate):
       print(f"{E:9.0f}   {R:.9e}")

   sigma0 = 3.0e-20
   const = average_cross_section_over_maxwellian(
       particle_energy_ev=beam,
       particle_mass_amu=1.0,
       target_temperature_ev=20.0,
       target_mass_amu=1.0,
       vx=vx, vr=vr, tnorm_ev=20.0,
       cylindrical_volume=volume,
       cross_section_m2=lambda E: np.full_like(E, sigma0),
   )
   analytic = sigma0 * vth * 2.0 / np.sqrt(np.pi)
   print(f"const rest limit: {const[0]:.9e} vs {analytic:.9e}  ratio={const[0]/analytic:.6f}")

   scaled = average_cross_section_over_maxwellian(
       particle_energy_ev=beam,
       particle_mass_amu=1.0,
       target_temperature_ev=10.0,
       target_mass_amu=1.0,
       vx=vx, vr=vr, tnorm_ev=20.0,
       cylindrical_volume=volume * 7.5,
       cross_section_m2=cx_h,
   )
   print("volume scaling exact:", np.array_equal(scaled, rate))

Actual output:

.. code-block:: text

   vth = 6.189937e+04 m/s
   E_beam/eV   <sigma v>/(m^3/s)
           0   2.161479352e-14
           1   2.213181636e-14
          10   2.620005271e-14
         100   4.415984397e-14
   const rest limit: 2.093487534e-15 vs 2.095378633e-15  ratio=0.999097
   volume scaling exact: True

``vth`` is the thermal speed for the 20 eV normalization energy and the hydrogen target mass, about ``6.19e4`` m/s. With the real charge-exchange cross section, ``<sigma v>`` rises from ``2.16e-14`` to ``4.42e-14`` m³/s: as the incident energy increases the relative speed grows, while the cross section does not fall fast enough, so the rate rises at these four points. This trend belongs only to this beam-target setup and must not be extrapolated into "it rises at all temperatures".

The constant-cross-section check uses ``T_target = Tnorm = 20`` eV and zero beam energy. The analytic limit is ``sigma * vth * 2/sqrt(pi)``; the run value ``2.093487534e-15`` and the analytic value ``2.095378633e-15`` have ratio ``0.999097``. This difference comes from the discrete error of the 24×36 midpoint mesh; it shows that the normalization and the stationary-beam limit are right, not that the mesh has converged. Multiplying all volumes by 7.5 gives bitwise identical results, showing that volume is only a measure and the overall scale cancels after the target is normalized by it; this does **not** mean that arbitrary nonuniform volume changes leave the integral unchanged.

What this section does not establish: this is not a thermal rate coefficient between two Maxwellians, but a beam-target average of a monoenergetic particle over a discrete Maxwellian target; it must not be compared directly with a given bivariate rate fit; it does not check whether the mesh tail is resolved; and it includes no species mixing, shielding or collision frequency.

Assembling the kernels into matrices: the four SIG families
------------------------------------------------------------

To turn the cross section into a transport operator, we assemble four kernel families on a normalized cylindrical velocity mesh: charge exchange ``SIG_CX``, H–H⁺ momentum transfer ``SIG_H_P``, H–H₂ momentum transfer ``SIG_H_H2``, and H–H self-collision stress ``SIG_H_H``. The angular direction is discretized at midpoints:

.. code-block:: text

   g^2 = vr_i^2 + vr_k^2 - 2 vr_i vr_k cos(theta) + (vx_j - vx_l)^2
   theta_m = pi (m + 1/2) / n_theta

Matrix column weights are ``Vr2pidVr_k * dVx_l``, and the velocity carrier is flattened in Fortran order: ``row = i + nvr*j``, ``col = k + nvr*l``. The default is ``n_theta=5``; the contract treats this explicitly as a discretization parameter that can be refined by adding angular nodes, not as a universal accuracy guarantee.

.. code-block:: python

   import numpy as np
   from scirel.collisions import assemble_atomic_hydrogen_collision_matrices as assemble

   vr = np.array([0.5, 1.0])
   vx = np.array([-1.0, 0.0, 1.0])
   wr = np.array([1.0, 2.0])
   dx = np.ones(3)
   s5 = assemble(vr, vx, wr, dx, 10.0, mu=1.0, n_theta=5)
   s32 = assemble(vr, vx, wr, dx, 10.0, mu=1.0, n_theta=32)
   for name in ("SIG_CX", "SIG_H_P", "SIG_H_H2", "SIG_H_H"):
       a = s5[name]
       print(f"{name:8s} shape={a.shape} min={a.min(): .3e} max={a.max(): .3e} neg={np.count_nonzero(a < 0)}")
   print(f"Vth = {np.sqrt(s5['Vth2'][0]):.6e} m/s")
   for name in ("SIG_CX", "SIG_H_P", "SIG_H_H2", "SIG_H_H"):
       d = np.max(np.abs(s5[name] - s32[name]))
       rel = d / np.max(np.abs(s32[name]))
       print(f"{name:8s} max|5-32|={d:.3e} rel={rel:.3e}")

Actual output:

.. code-block:: text

   SIG_CX   shape=(6, 6) min= 3.186e-19 max= 1.710e-18 neg=0
   SIG_H_P  shape=(6, 6) min=-5.118e-18 max= 5.118e-18 neg=12
   SIG_H_H2 shape=(6, 6) min=-4.099e-20 max= 4.099e-20 neg=12
   SIG_H_H  shape=(6, 6) min=-3.904e-20 max= 1.950e-20 neg=24
   Vth = 4.376946e+04 m/s
   SIG_CX   max|5-32|=7.806e-21 rel=4.564e-03
   SIG_H_P  max|5-32|=2.754e-24 rel=5.380e-07
   SIG_H_H2 max|5-32|=6.563e-26 rel=1.601e-06
   SIG_H_H  max|5-32|=1.667e-23 rel=4.270e-04

The 2×3 velocity mesh gives N=6, so all four matrices are 6×6. ``SIG_CX`` is strictly nonnegative on this mesh; the other three kernels retain negative entries because momentum transfer and stress projection are signed. Negative entries are not an assembly failure, and they must not be "fixed" with ``abs`` or clipping.

``Vth`` is about ``4.38e4`` m/s. Replacing the default five angular points with 32 changes ``SIG_CX`` by at most a relative ``4.56e-3`` (about 0.46%), ``SIG_H_H`` by ``4.27e-4``, while the two mixed channels change by only ``1e-7`` to ``1e-6``. This shows that the default five-point error is not equally large for every family; it also does **not** prove that 32 points have converged. The contract leaves the angular node count as an explicit convergence-check parameter, and users should refine it themselves and report the change.

What this section does not establish: matrix elements are not physical rates; they acquire collision-frequency meaning only after contraction with a distribution; there is no external cross-section experimental benchmark; it does not prove that the default angular nodes are adequate for an arbitrary mesh; and ``Tnorm`` and ``mu`` are model inputs, not quantities inferred from data.

From matrices to Alpha: Fortran order is not a detail
-----------------------------------------------------

The next layer is the per-cell matrix-vector contraction. The contract is

.. code-block:: text

   Alpha_CX[:,:,k]   = F^-1(SIG_CX   @ F(fi_hat[:,:,k] * ni[k]))
   Alpha_H_H2[:,:,k] = F^-1(SIG_H_H2 @ F(fH2[:,:,k]))
   Alpha_H_P[:,:,k]  = F^-1(SIG_H_P  @ F(fi_hat[:,:,k] * ni[k]))
   Alpha_H_H[:,:,k]  = F^-1(SIG_H_H  @ F(fH[:,:,k]))

where ``F`` / ``F^-1`` are the Fortran-order (``order='F'``) flattening and restoring of the velocity carrier. ``fi_hat`` is the normalized atomic seed distribution, and ``ni`` carries the ion density; ``fH2`` and ``fH`` are directly the density distributions of molecular and atomic neutrals. The two mixed channels use ``fi_hat * ni``, and the two neutral channels use their bare distributions.

.. code-block:: python

   import numpy as np
   from scirel.collisions import assemble_atomic_hydrogen_collision_matrices as assemble
   from scirel.kinetic import contract_atomic_hydrogen_alpha_frequencies as contract

   vr = np.array([0.5, 1.0])
   vx = np.array([-1.0, 0.0, 1.0])
   wr = np.array([1.0, 2.0])
   dx = np.ones(3)
   w = wr[:, None] * dx[None, :]
   s = assemble(vr, vx, wr, dx, 10.0, mu=1.0, n_theta=32)

   def maxwell(density, drift):
       f = np.exp(-vr[:, None]**2 - (vx[None, :] - drift)**2)
       return f * density / np.sum(w * f)

   fi = maxwell(1.0, 0.2)[:, :, None]
   fH2 = maxwell(2.0e17, -0.1)[:, :, None]
   fH = maxwell(1.0e17, 0.15)[:, :, None]
   alphas = contract(
       s["SIG_CX"], s["SIG_H_H"], s["SIG_H_H2"], s["SIG_H_P"],
       fi, np.array([1.5e17]), fH2, fH,
   )
   for name, value in alphas.items():
       print(f"{name:9s} shape={value.shape} min={value.min(): .3e} max={value.max(): .3e}")

   carrier = (fi * 1.5e17).reshape(6, order="F")
   f_order = s["SIG_CX"] @ carrier
   c_order = s["SIG_CX"] @ (fi * 1.5e17).reshape(6)
   manual = f_order.reshape(fi.shape, order="F")
   print("Fortran match:", np.array_equal(alphas["Alpha_CX"], manual))
   print(f"C-order vs Fortran max diff = {np.max(np.abs(c_order - f_order)):.3e}, rel={np.max(np.abs(c_order - f_order))/np.max(np.abs(f_order)):.3e}")

Actual output:

.. code-block:: text

   Alpha_CX  shape=(2, 3, 1) min= 7.125e-02 max= 1.024e-01
   Alpha_H_H2 shape=(2, 3, 1) min=-2.597e-03 max= 2.959e-03
   Alpha_H_P shape=(2, 3, 1) min=-1.926e-01 max= 1.294e-01
   Alpha_H_H shape=(2, 3, 1) min=-9.795e-04 max= 3.499e-04
   Fortran match: True
   C-order vs Fortran max diff = 3.244e-02, rel=3.167e-01

``fi`` is normalized so that its integral is 1, and ``ni=1.5e17`` carries the density; the integrals of ``fH2`` and ``fH`` are ``2.0e17`` and ``1.0e17`` m^-3. All four Alpha fields keep the ``(2, 3, 1)`` shape. In this example ``Alpha_CX`` is about ``0.071`` to ``0.102``; ``Alpha_H_P`` spans negative and positive values, and ``Alpha_H_H2`` and ``Alpha_H_H`` also cross zero. These are signed intermediate fields, not probability densities, and they cannot be used directly as final frequencies.

Recomputing by hand with ``order='F'`` flattening reproduces ``Alpha_CX`` bit for bit (``Fortran match: True``). If we use the default C-order flattening instead, the maximum relative difference reaches ``31.7%``; this is not rounding error, but feeding the velocity cells to the matrix in a different order. The matrix convention ``row=i+nvr*j`` and ``order='F'`` here must be used together.

What this section does not establish: the Alpha fields are not final collision frequencies; their sign alone does not determine a physical direction; negative values come from signed kernels and the contract requires them to be preserved without clipping; and this example shows only one spatial cell, with no transport iteration or time advance.

From Alpha to local frequencies: ratios, units and undefined cases
------------------------------------------------------------------

The final layer reduces Alpha inside each spatial cell to local moment-matching coefficients. Let

.. code-block:: text

   n = sum(w f)
   u = sum(w f vx) / n
   U = Vth u
   K = vr^2 - 2 (vx - u)^2
   W = sum(w f K) / n

The denominators are ``(U - U_background)/Vth`` for the mixed channels and ``W`` for the self-collision channel; ``Omega = N/d`` and ``nu = Vth * Omega``. When the denominator is zero, the contract returns ``NaN`` and ``defined=False`` but keeps the finite collision moments; negative ratios are retained and marked ``negative_no_bgk_closure``, with no floor and no clipping. The total frequency is the sum of the enabled channels, and an undefined value in any enabled channel propagates to the total.

.. code-block:: python

   import numpy as np
   from scirel.collisions import (
       assemble_atomic_hydrogen_collision_matrices as assemble,
       assemble_atomic_hydrogen_omega_frequencies as omega_reduce,
   )
   from scirel.kinetic import contract_atomic_hydrogen_alpha_frequencies as contract

   vr = np.array([0.5, 1.0])
   vx = np.array([-1.0, 0.0, 1.0])
   wr = np.array([1.0, 2.0])
   dx = np.ones(3)
   w = wr[:, None] * dx[None, :]
   s = assemble(vr, vx, wr, dx, 10.0, mu=1.0, n_theta=32)

   def maxwell(density, drift):
       f = np.exp(-vr[:, None]**2 - (vx[None, :] - drift)**2)
       return f * density / np.sum(w * f)

   fi = maxwell(1.0, 0.2)[:, :, None]
   fH2 = maxwell(2.0e17, -0.1)[:, :, None]
   fH = maxwell(1.0e17, 0.15)[:, :, None]
   a = contract(
       s["SIG_CX"], s["SIG_H_H"], s["SIG_H_H2"], s["SIG_H_P"],
       fi, np.array([1.5e17]), fH2, fH,
   )
   Vth = float(np.sqrt(s["Vth2"][0]))
   nH = np.sum(w * fH[:, :, 0])
   flow_fi = Vth * np.sum(w * fi[:, :, 0] * vx[None, :]) / np.sum(w * fi[:, :, 0])
   flow_H2 = Vth * np.sum(w * fH2[:, :, 0] * vx[None, :]) / np.sum(w * fH2[:, :, 0])
   r = omega_reduce(
       fH, np.array([nH]), a["Alpha_H_P"], a["Alpha_H_H2"],
       s["SIG_H_H"], wr, dx, vr, vx, Vth,
       np.array([flow_fi]), np.array([flow_H2]),
   )
   print(f"VxH = {r['VxH'][0]:.6f} m/s")
   print(f"Wperp_paraH = {r['Wperp_paraH'][0]:.9f}")
   for name in ("H_P", "H_H2", "H_H"):
       print(f"{name:4s} Omega={r['Omega_'+name][0]: .9f} 1/m  nu={r['nu_'+name][0]: .6f} 1/s  status={r['status_'+name][0]}")
   print(f"Omega_EL={r['Omega_EL'][0]:.9f} 1/m  nu_EL={r['nu_EL'][0]:.6f} 1/s")

   origin = vx[0]
   u_rel = np.sum(w * fH[:, :, 0] * (vx - origin)[None, :]) / nH
   u = origin + u_rel
   r0 = omega_reduce(
       fH, np.array([nH]), a["Alpha_H_P"], a["Alpha_H_H2"],
       s["SIG_H_H"], wr, dx, vr, vx, Vth,
       np.array([Vth * u]), np.array([Vth * u]),
   )
   print(f"matched flow: Omega_H_P={float(r0['Omega_H_P'][0])} defined={r0['defined_H_P'][0]} status={r0['status_H_P'][0]} moment={r0['moment_H_P'][0]:.6e}")

Actual output:

.. code-block:: text

   VxH = 5543.274344 m/s
   Wperp_paraH = -0.223070651
   H_P  Omega= 0.152986508 1/m  nu= 6696.137005 1/s  status=finite_nonnegative
   H_H2 Omega= 0.002655305 1/m  nu= 116.221279 1/s  status=finite_nonnegative
   H_H  Omega= 0.000631014 1/m  nu= 27.619145 1/s  status=finite_nonnegative
   Omega_EL=0.156272827 1/m  nu_EL=6839.977429 1/s
   matched flow: Omega_H_P=nan defined=False status=undefined_zero_denominator moment=-6.376374e-03

``VxH`` is the mean axial velocity of atomic hydrogen in this cell, about ``5.54e3`` m/s. ``Wperp_paraH`` is the selected central stress (perpendicular minus twice the axial second moment); it is signed, about ``-0.223``. A negative value does not mean the calculation failed, and it must not be interpreted as a variance.

In this example the H–H⁺ mixed channel has ``Omega`` about ``0.153`` m^-1 and ``nu`` about ``6.70e3`` s^-1; the H–H₂ and H–H channels are much smaller; the three-channel total is about ``6.84e3`` s^-1. The ``status`` of all three channels is ``finite_nonnegative``, meaning the denominator is nonzero and the ratio is nonnegative.

The last call deliberately sets the background flow velocity equal to the actual mean flow, making the mixed-channel denominator zero. The result is ``Omega_H_P = nan``, ``defined=False``, status ``undefined_zero_denominator``, but ``moment_H_P`` still returns a finite ``-6.376374e-03``. This shows precisely that "the frequency is undefined" and "the collision moment does not exist" are different statements; ``NaN`` must not be treated as zero collisions.

What this section does not establish: this is a local moment-matching reduction, not a complete Boltzmann collision operator; a finite velocity/angle mesh does not guarantee an exact Maxwellian equilibrium; a negative ratio is retained but does not constitute an acceptable nonnegative BGK relaxation; and single-cell results do not replace spatial coupling, time advance or convergence studies.

Another local question: how much stopping cross section do fast ions add?
-------------------------------------------------------------------------

Given a local neutral-beam deposition power density, an electron slowing time and the beam-particle birth direction, one can evaluate a separate fast-ion stopping increment. The chosen pitch is the cosine of that birth direction relative to the magnetic axis. It is not an angle, and no equivalence to a toroidal or full-local-field direction is inferred.

The empirical model fixes pitch diffusion at ``y=0.6``. Let ``T=te/10000`` and ``r=((E/A)/1e6)/T``. With the specified energy polynomial ``F(r)`` and pitch polynomial ``G(min(1,abs(cosine)))``, it evaluates

.. code-block:: text

   S = power_density / (E * 1.602176462e-19)
   delta_sigma = (S * slowing_time / ne) * T^(-0.9027) * F(r) * G(p) * 1e-19 m^2

Power density is in W/m^3, so ``S`` is in m^-3 s^-1 and ``S*slowing_time/ne`` is dimensionless. The call infers no volume from total power, estimates no slowing time and reconstructs no beam path or magnetic field.

.. code-block:: python

   import numpy as np
   from scirel.collisions import evaluate_fast_ion_stopping_increment

   increment = evaluate_fast_ion_stopping_increment(
       beam_mass_number=1.0,
       beam_energy_ev=100000.0,
       birth_pitch_cosine=0.5,
       electron_density_m3=1e18,
       electron_temperature_ev=10000.0,
       power_density_w_m3=1e6,
       electron_slowing_time_s=1.0,
   )
   np.testing.assert_allclose(
       increment, [[1.9645775636530587e-18]], rtol=5e-12, atol=1e-300,
   )
   print(increment.shape)
   print(increment.dtype)
   print(f"{increment[0, 0]:.17g} m^2")

Actual output:

.. code-block:: text

   (1, 1)
   float64
   1.9645775636530587e-18 m^2

This is an additional area, about ``1.96e-18`` m^2 for the seven supplied inputs; it does not supply the total cross section needed for attenuation. All-scalar calls still return a two-dimensional ``(1,1)`` array. One-dimensional inputs become rows; N-dimensional inputs align leading axes and append singleton axes on the right of lower-rank arrays.

The finite positive example is not a guarantee over the full input domain. Only the energy polynomial is overwritten with zero for ``r>pi``; equality is not cut off, and infinities or undefined values in other factors can still make the final result nonfinite. NaN pitch maps to one under the absolute-pitch cap, negative temperature can produce complex values, and zero power does not bypass division by energy. These arithmetic outcomes do not qualify physical plasma states.

The qualitative low-density/high-energy setting supplies no calibration interval, species coverage or error bound. Numerical verification of the fixed expression does not replace human scientific acceptance, which remains pending. Full coefficients, strict boundaries and evidence limits are in :doc:`../reference/generated/scirel.collisions.fast-ion-stopping-increment`.

Choosing entry points, common pitfalls, and what this chapter does not cover
----------------------------------------------------------------------------

Choosing functions along this path:

- If you only need one H+H⁺ charge-exchange cross section: :doc:`../reference/generated/scirel.collisions.atomic-hydrogen-charge-exchange-cross-section`; for molecular hydrogen use :doc:`../reference/generated/scirel.collisions.molecular-hydrogen-charge-exchange-cross-section`.
- If you want to project one cross section onto a discrete Maxwellian target: :doc:`../reference/generated/scirel.collisions.maxwellian-relative-speed-rate-average`.
- If you want the four kernel matrices: :doc:`../reference/generated/scirel.collisions.atomic-hydrogen-collision-matrices`.
- If you want Alpha from the matrices and distributions: :doc:`../reference/generated/scirel.kinetic.atomic-alpha-contraction`.
- If you want the local ``Omega`` and ``nu``: :doc:`../reference/generated/scirel.collisions.atomic-hydrogen-omega-frequencies`.

A few common pitfalls:

- Branches and endpoints: Janev and Freeman-Jones are independent fits with different energy domains and endpoints; positive energies outside the domain are silently clipped, not extrapolated.
- Beam target or thermal average: ``average_cross_section_over_maxwellian`` is the average of a monoenergetic particle over a Maxwellian target, not a thermal rate between two Maxwellians.
- Mass convention: the collision energy is constructed from ``particle_mass_amu``, not the reduced mass; do not "compensate" for model differences by changing the mass.
- Flattening order: SIG is assembled in Fortran order, and Alpha must be contracted with ``order='F'``; C order produces an observable numerical error.
- Signed intermediates: elastic kernels and some Alpha fields have negative values, and the contract requires them to be preserved; clipping changes the model.
- Undefined is not zero: a zero denominator gives ``NaN`` and ``defined=False``; negative ratios have their own status and must not be silently dropped.

Entry points not covered in this chapter, and why:

- The five elastic cross-section assets (:doc:`../reference/generated/scirel.collisions.atomic-hydrogen-elastic-cross-section`, :doc:`../reference/generated/scirel.collisions.atomic-molecular-hydrogen-elastic-cross-section`, :doc:`../reference/generated/scirel.collisions.molecular-hydrogen-elastic-cross-section`, :doc:`../reference/generated/scirel.collisions.proton-atomic-hydrogen-elastic-cross-section`, :doc:`../reference/generated/scirel.collisions.proton-molecular-hydrogen-elastic-cross-section`): their momentum-transfer/viscosity branches, output shape and 10 eV piecewise breakpoints are defined by each asset contract; H-on-H2 and H+-on-H return the input shape, and H+-on-H uses the low-energy branch for E<10 eV and the high-energy branch for E>=10 eV, including exactly 10 eV. They serve the elastic matrices, but including them would turn this chapter from one continuous path into a catalog of cross sections.
- The five rate and population assets (:doc:`../reference/generated/scirel.collisions.atomic-hydrogen-charge-exchange-rate-coefficient`, :doc:`../reference/generated/scirel.collisions.molecular-hydrogen-charge-exchange-rate-coefficient`, :doc:`../reference/generated/scirel.collisions.janev-electron-impact-ionization-rate`, :doc:`../reference/generated/scirel.collisions.atomic-hydrogen-1s-radiative-recombination-rate-coefficient`, :doc:`../reference/generated/scirel.kinetic.hydrogen-saha-equilibrium-population`): they are independent fits and Saha relations given directly in temperature/energy or density/temperature, and cannot be derived from this chapter's beam-target average or matrix contraction.
- Molecular-hydrogen matrices, Alpha and Omega (:doc:`../reference/generated/scirel.collisions.molecular-hydrogen-collision-matrices`, :doc:`../reference/generated/scirel.kinetic.molecular-alpha-contraction`, :doc:`../reference/generated/scirel.collisions.molecular-hydrogen-omega-frequencies`): the structure parallels the atomic path, but the coefficient tables, species pairings and cross-section fits differ; repeating the code would add no new methodological information.
- The three-channel sum entry point (:doc:`../reference/generated/scirel.kinetic.elastic-frequency-channels`): it is a pointwise sum of already normalized channels; this chapter's ``omega_reduce`` already returns ``Omega_EL``, so treating it separately would be repetitive.

Boundary: the numbers in this chapter correspond only to the declared normalized cylindrical mesh, the given cross-section fits, and this moment-matching reduction. Changing the distribution, species, ``Tnorm``/``mu``, angular nodes or spatial coupling means the ``Omega`` and ``nu`` here cannot be reused directly. Full signatures, parameter validation, failure behavior and the validation boundary for a larger parameter domain are in the API reference pages linked at the end of the chapter; this chapter is only responsible for explaining one computational path clearly.
