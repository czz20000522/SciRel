From cold plasma to the kinetic dispersion relation
=====================================================

This chapter answers one concrete question: **given plasma parameters, a background magnetic field and a wavevector, how do we decide step by step whether a wave can propagate, what its frequency is, and how strong the damping is?** We will not list entry points function by function; instead we follow one continuous computational path:

1. Convert density, temperature, mass and magnetic field into SI scales, and state the geometric convention for the wavevector.
2. Compute a local dielectric tensor with the cold-plasma model, and see what it gives and what it lacks.
3. Switch to the kinetic Maxwellian electrostatic response and evaluate the dielectric function at one complex frequency.
4. Use that response as a residual, starting from a seed, to find one complex root.
5. Sweep a range of wavenumbers, check branch continuity, and explain a common branch trap.
6. Replace the plasma dispersion function with a fixed-pole rational approximation and compare errors at different orders.
7. Assemble the magnetized kinetic dielectric tensor and compare the finite-harmonic sum with the Ronnmark pole path at the same wave point.

After reading this chapter you should be able to carry out a computation of the form "cold-model estimate -> kinetic response -> seeded root finding -> branch scan -> cross-method check" on your own, and to know the boundary of each step's conclusions.

.. note::

    This chapter is a tutorial, not a contract summary. The complete signature, parameter units, failure behavior and applicability of each function are on the API reference pages linked at the end of the chapter; the tutorial code uses only public SciRel functions.

The code blocks in this chapter run in order: later blocks reuse ``E``, ``M_E``, ``M_D``, ``scales``, ``wp`` and ``species`` defined earlier. To run one block on its own, first execute the code in "Setup: equilibrium scales and wavevector".

Conventions and route
-----------------------

This chapter uses the time convention ``exp(-i omega t)`` throughout. The cold-plasma part uses SI units; the kinetic electrostatic part uses normalized units: the plasma frequency is 1, the standard deviation of the Maxwellian thermal speed is 1, and the wavenumber is normalized by the inverse Debye length. The two unit systems must not be mixed directly; the text states explicitly where the switch happens.

A "root" in this text only means that some complex equation is satisfied numerically; it does not mean that the root is necessarily the physically most important mode, nor that it is the only root. Branch selection is always determined by the seed and the scan order supplied by the caller.

Setup: equilibrium scales and wavevector
------------------------------------------

Start with a concrete deuterium-electron plasma: background magnetic field ``B0 = 1 T``, electron and ion densities both ``1e19 m^-3``, and reference temperature ``T00 = 1000 eV``; the electron temperature equals the reference temperature and the ion temperature is ``0.5 T00``. The species scales are given by

.. code-block:: text

   v_ts      = sqrt(2 k_B T_s / m_s)
   omega_cs  = q_s B0 / m_s
   omega_ps^2 = n_s q_s^2 / (m_s epsilon_0)
   rho_cs    = sqrt(k_B T_s / m_s) / omega_cs
   k_n       = 1 / max_s |rho_cs|
   omega_n   = min_s |omega_cs|

``omega_cs`` and ``rho_cs`` both carry the sign of the charge; ``omega_n`` takes the **smallest** absolute cyclotron frequency, which in this two-species example is the ion cyclotron frequency, not the electron cyclotron frequency. ``k_n`` takes the **largest** absolute cyclotron radius, that is, the inverse of the ion cyclotron radius. This choice is the normalization convention of the later magnetized-tensor entry point, not a claim about the physically "most important scale".

.. code-block:: python

   import numpy as np
   from scirel.kinetic import derive_species_equilibrium_scales
   from scirel.geometry import project_planar_wavevector

   E = 1.602176634e-19
   M_E = 9.1093837015e-31
   M_D = 2.013553212745 * 1.67262192369e-27

   scales = derive_species_equilibrium_scales(
       ms=[M_E, M_D],
       qs=[-E, E],
       ns_unit=[1.0, 1.0],
       Ts_unit=[1.0, 0.5],
       B0=1.0, n00=1e19, T00=1000.0,
   )
   wp = np.sqrt(scales["wp2"])
   print(f"f_pe  = {wp/(2*np.pi)/1e9:.3f} GHz")
   print(f"f_ce  = {abs(scales['wcs'][0])/(2*np.pi)/1e9:.3f} GHz")
   print(f"f_ci  = {scales['wcs'][1]/(2*np.pi)/1e6:.3f} MHz")
   print(f"v_te  = {scales['vts'][0]/1e6:.3f} Mm/s")
   print(f"v_ti  = {scales['vts'][1]/1e3:.3f} km/s")
   print(f"rho_i = {scales['rhocs'][1]*1e3:.3f} mm")
   print(f"kn    = {scales['kn']:.3f} 1/m")
   print(f"wn    = {scales['wn']:.3e} rad/s")

   waves = project_planar_wavevector(k_grid=[0.5, 1.0], theta_rad=0.3)
   print("kx =", waves["kx"])
   print("kz =", waves["kz"])
   print("k  =", waves["k"])

Actual output:

.. code-block:: text

   f_pe  = 28.397 GHz
   f_ce  = 27.992 GHz
   f_ci  = 7.571 MHz
   v_te  = 18.756 Mm/s
   v_ti  = 218.111 km/s
   rho_i = 3.242 mm
   kn    = 308.451 1/m
   wn    = 4.757e+07 rad/s
   kx = [0.1477601  0.29552021]
   kz = [0.47766824 0.95533649]
   k  = [0.5 1. ]

``f_pe`` is the total plasma frequency, obtained by adding the ``omega_ps^2`` of electrons and ions; the ion contribution is small, but the code still includes it. ``f_ce`` is about 27.99 GHz and ``f_ci`` about 7.57 MHz, a ratio of about 3700, exactly on the scale of the electron-to-ion mass ratio. ``v_te`` is about 18.8 Mm/s, the thermal speed of a 1 keV electron; ``v_ti`` is about 218 km/s. ``rho_i`` is about 3.24 mm, so ``kn`` is about 308 1/m; ``wn`` equals the ion cyclotron frequency, about ``4.76e7 rad/s``.

The wavevector projection uses ``kx = k sin(theta)`` and ``kz = k cos(theta)``, with the angle measured from ``+z`` towards ``+x``. For ``theta = 0.3 rad``, ``k = 0.5 1/m`` corresponds to ``kx = 0.148 1/m`` and ``kz = 0.478 1/m``. The ``z`` axis here is the direction of the background magnetic field; the later magnetized-tensor entry point requires the perpendicular and parallel components to be passed separately.

**What this section cannot establish.** The scales only state "which characteristic frequencies and lengths this equilibrium has"; they do not say that any wave exists, nor which mode is most important. ``wn`` and ``kn`` are normalization choices of the entry point, not mode frequencies or mode wavenumbers; with another normalization the numbers change, but the physical conclusions should not.

Cold plasma: the dielectric tensor
------------------------------------

The cold model treats each species as a fluid without thermal motion. For frequency ``omega``, background field ``B`` and a species list, the Stix scalars are

.. code-block:: text

   S   = 1 - sum_s omega_ps^2 (omega + i nu_s)
             / (omega [(omega + i nu_s)^2 - Omega_cs^2])
   D_H = sum_s Omega_cs omega_ps^2
             / (omega [(omega + i nu_s)^2 - Omega_cs^2])
   P   = 1 - sum_s omega_ps^2 / (omega (omega + i nu_s))

where ``Omega_cs = q_s |B| / m_s`` is the signed cyclotron frequency and ``nu_s`` is the collision rate. In the Cartesian basis supplied by the caller the tensor is written

.. code-block:: text

   epsilon_r = S I + (P - S) b b + i D_H [b]_x

``b`` is the unit direction of the magnetic field and ``[b]_x`` is the cross-product matrix. This expression says: the parallel direction is controlled by ``P``, the perpendicular diagonal by ``S``, and the perpendicular off-diagonal by ``D_H``.

Take ``f = 50 GHz`` with the background field along the ``z`` axis:

.. code-block:: python

   from scirel.dielectric import cold_plasma_dielectric_tensor

   species = [
       {"density_m3": 1e19, "charge_c": -E, "mass_kg": M_E},
       {"density_m3": 1e19, "charge_c": E, "mass_kg": M_D},
   ]
   eps = cold_plasma_dielectric_tensor(50e9, [0.0, 0.0, 1.0], species)
   with np.printoptions(precision=4, suppress=True):
       print(eps)
   print("max |eps - eps^H| =", np.max(np.abs(eps - eps.conj().T)))
   print("eigvals =", np.linalg.eigvalsh(eps))
   b = np.array([0.0, 0.0, 1.0])
   print("b^H eps b =", b @ eps @ b)

Actual output:

.. code-block:: text

   [[0.5302+0.j     0.    +0.2629j 0.    +0.j    ]
    [0.    -0.2629j 0.5302+0.j     0.    +0.j    ]
    [0.    +0.j     0.    +0.j     0.6774+0.j    ]]
   max |eps - eps^H| = 0.0
   eigvals = [0.26728665 0.67744724 0.79318418]
   b^H eps b = (0.6774472367611433+0j)

Here ``S = 0.5302``, ``D_H = 0.2629`` and ``P = 0.6774``. The tensor is Hermitian because both species use the default collision rate of 0; the deviation ``epsilon == epsilon^H`` is exactly 0. The three eigenvalues are ``S - D_H``, ``P`` and ``S + D_H``; ``b^H eps b`` comes back exactly as ``P``, which is the parallel response. Note that positive eigenvalues do not automatically mean a wave can propagate: the propagation condition also involves the wavevector and the Maxwell curl terms.

The cold model can also give an "electrostatic root". Set ``B = 0``; the tensor reduces to ``P I``, and ``P = 0`` requires

.. code-block:: text

   omega^2 = sum_s omega_ps^2 = omega_p^2

that is, ``omega = omega_p`` independent of wavenumber. Evaluating at ``f_pe = wp/(2 pi)``:

.. code-block:: python

   f_pe = wp / (2*np.pi)
   eps_zero = cold_plasma_dielectric_tensor(f_pe, [0.0, 0.0, 0.0], species)
   print("Re diag(eps) at f_pe, B=0 =", np.diag(eps_zero).real)
   print("max off-diagonal =", np.max(np.abs(eps_zero - np.diag(np.diag(eps_zero)))))

Actual output:

.. code-block:: text

   Re diag(eps) at f_pe, B=0 = [-4.74351987e-10 -4.74351987e-10 -4.74351987e-10]
   max off-diagonal = 0.0

The diagonal entries are not exactly 0 but about ``-4.74e-10``. This is not a new physical correction; it is the rounding residual from computing ``f_pe`` as ``sqrt(wp2)`` and multiplying by ``2 pi`` to return to angular frequency. It reminds us that **a small residual only says the value is numerically close to a root; it does not say the model gives an exact zero**.

**What this section cannot establish.** The cold model has no thermal motion, hence no Landau damping and no finite-Larmor-radius corrections; the dielectric tensor is local and cannot describe spatial dispersion or a nonlocal response. ``P = 0`` gives the electrostatic root of the cold limit and cannot be used to predict the imaginary part of a root at finite temperature. The cold model is singular at an exact cyclotron resonance; this library rejects the whole evaluation when a contributing species has an exact zero denominator, instead of returning a truncated finite value. The tensor matrix elements depend on the basis you supply; only ``b^H eps b`` and the eigenvalue structure are invariant under basis rotation.

Kinetic electrostatic response: one complex frequency point
-------------------------------------------------------------

Now switch to the kinetic model. Consider a one-dimensional, unmagnetized, collisionless electrostatic plasma with an electron equilibrium distribution

.. code-block:: text

   f0(v) = exp(-v^2/2) / sqrt(2*pi)

Using units where the plasma frequency is 1 and the thermal speed standard deviation is 1, the wavenumber ``k`` is normalized by the inverse Debye length. The longitudinal dielectric function is

.. code-block:: text

   epsilon(omega,k) = 1 + chi
   chi = (1 + z Z(z)) / k^2
   z = omega / (sqrt(2) k)
   D = k^2 epsilon

``Z`` is the plasma dispersion function. ``D`` is just ``epsilon`` multiplied by the frequency-independent ``k^2``, so ``epsilon = 0`` and ``D = 0`` are the same equation; do not treat ``D`` as an independent equation, and do not compare ``|D|`` directly with ``|epsilon|``.

First evaluate one complex frequency point ``omega = 1.2 + 0.3i`` at ``k = 0.4``:

.. code-block:: python

   from scirel.kinetic import evaluate_maxwellian_electrostatic

   omega = 1.2 + 0.3j
   k = 0.4
   response = evaluate_maxwellian_electrostatic(omega, k)
   print(f"epsilon = {response['epsilon']:.9f}")
   print(f"D       = {response['D']:.9f}")
   print(f"z       = {response['z']:.9f}")
   print(f"error   = {response['epsilon_error']:.3e}")

Actual output:

.. code-block:: text

   epsilon = 0.412798173+0.597635601j
   D       = 0.066047708+0.095621696j
   z       = 2.121320344+0.530330086j
   error   = 9.358e-14

``omega/k = 3 + 0.75i``, and dividing by ``sqrt(2)`` gives ``z = 2.121 + 0.530i``. The imaginary part of ``epsilon`` is nonzero, so this trial frequency is not on a root. ``D = 0.16 * epsilon``: both the real and the imaginary part are exactly 0.16 times those of ``epsilon``, which is the direct consequence of ``D = k^2 epsilon``.

``epsilon_error`` is a numerical error estimate, not a strict error bound. Here it is about ``9.36e-14``, small relative to ``|epsilon|``, which only says the arithmetic error of this evaluation is small, not that ``epsilon`` is close to zero.

**What this section cannot establish.** A response at one complex frequency is not a root; a small ``epsilon`` is not the same as "a wave exists". This model is a one-dimensional, unmagnetized, collisionless Maxwellian electrostatic model with fixed ions; changing the distribution, adding a magnetic field or collisions, or changing species requires a different entry point or model. ``epsilon_error`` is not an interval certificate and cannot be used to prove that a root does not exist.

From response to a root: seed and residual
--------------------------------------------

When finding roots, SciRel does not claim to find "the physically most important root" automatically; starting from the seed you provide, it finds the root on **this branch** and checks the normalized residual before returning. The normalized residual is approximately

.. code-block:: text

   r_norm = (|epsilon| + epsilon_error) / (1 + |chi|)

which accounts for the relative sizes of the vacuum term and the polarization term, avoiding the ``k^2`` scaling that would affect ``|D|`` directly. Accepting a root requires that the solver succeeds, the function-evaluation budget is not exceeded, ``r_norm`` is below the tolerance, and the error term itself is below one quarter of the tolerance.

.. code-block:: python

   from scirel.kinetic import solve_maxwellian_electrostatic_mode

   solved = solve_maxwellian_electrostatic_mode(
       k=0.4,
       initial_omega=1.45 - 0.1j,
   )
   print(f"omega = {solved['omega']:.12f}")
   print(f"|epsilon| = {abs(solved['epsilon']):.3e}")
   print(f"normalized residual = {solved['normalized_residual']:.3e}")
   print(f"residual error gate = {solved['normalized_residual_error']:.3e}")
   print(f"evaluations = {solved['evaluations']}")

   other = solve_maxwellian_electrostatic_mode(
       k=0.4,
       initial_omega=-1.3 - 0.1j,
   )
   print(f"other = {other['omega']:.12f}")
   print(f"other normalized residual = {other['normalized_residual']:.3e}")

Actual output:

.. code-block:: text

   omega = 1.285056969654-0.066127958691j
   |epsilon| = 2.221e-15
   normalized residual = 1.110e-15
   residual error gate = 2.963e-13
   evaluations = 15
   other = -1.285056969654-0.066127958691j
   other normalized residual = 1.122e-15

The real part of ``omega`` is the oscillation frequency, and a negative imaginary part means decay in time under the ``exp(-i omega t)`` convention. The first root starts from ``1.45 - 0.1i`` and the second from ``-1.3 - 0.1i``; their real parts have opposite signs and their imaginary parts are the same, with normalized residuals of about ``1e-15``. This shows that at this real wavenumber both the positive and the negative real-frequency branch can be valid roots of the equation. **A small residual only says "this number really is a root of the equation"; it cannot distinguish which branch is the mode you want.**

``evaluations = 15`` is the number of function evaluations used by MINPACK. ``residual error gate = 2.96e-13`` is below one quarter of the default tolerance, so this acceptance is not because "the residual happened to be small" but because the error gate also passed.

**What this section cannot establish.** The root finder does not prove uniqueness, does not guarantee the lowest damping and does not guarantee the globally most unstable mode. A different seed may land on another branch, or even fail to converge; this is a branch-selection issue, not the solver "computing wrongly". The residual is a backward error, not a physical damping rate and not a frequency error.

Scanning a branch: continuity and a branch trap
-------------------------------------------------

Fix the default seed strategy and scan ``k = 0.2, 0.4, 0.6, 0.8, 1.0``:

.. code-block:: python

   from scirel.kinetic import scan_gpdf_roots, evaluate_gpdf_small_k

   scan = scan_gpdf_roots(
       "langmuir",
       k_values=[0.2, 0.4, 0.6, 0.8, 1.0],
   )
   for kk, om, res in zip(scan["k"], scan["omega"], scan["dielectric_residual"]):
       print(f"k={kk:4.2f}  omega={om:.9f}  |res|={abs(res):.2e}")

   asym = evaluate_gpdf_small_k(0.2)
   print(f"asymptotic real = {asym['omega_real']:.6f}")
   print(f"asymptotic imag = {asym['omega_imag']:.6e}")

Actual output:

.. code-block:: text

   k=0.20  omega=1.063984341-0.000055107j  |res|=2.88e-14
   k=0.40  omega=1.285056970-0.066127959j  |res|=2.22e-15
   k=0.60  omega=1.545706755-0.264110338j  |res|=6.41e-16
   k=0.80  omega=1.799899318-0.534552362j  |res|=6.21e-16
   k=1.00  omega=2.045904866-0.851330459j  |res|=6.75e-16
   asymptotic real = 1.060000
   asymptotic imag = -6.513542e-05

These five points lie on the same continuous branch: as the wavenumber increases, the real frequency rises and the damping rate grows. At small wavenumber the damping is very weak, close to a collisionless Langmuir wave; by ``k`` near 1 the damping is no longer negligible. This is also the difference between the cold model and the kinetic model: the cold limit gives ``omega = 1`` in normalized units, independent of ``k``, while the kinetic root at ``k = 0.2`` is ``1.063984 - 5.5107e-05 i``; its real part already carries a Bohm-Gross shift of about 6.4%, and its imaginary part is Landau damping, which the cold model does not have at all. As an independent check, the small-wavenumber asymptotics give

.. code-block:: text

   omega_r = 1 + 1.5 k^2
   omega_i = -sqrt(pi/8) exp(-1/(2k^2) - 1.5) / k^3

At ``k = 0.2`` this gives ``1.060000 - 6.513542e-05 i``, while the numerical root is ``1.063984 - 5.5107e-05 i``. The real parts differ by only about 0.4%, while the imaginary parts differ by about 18%; this is the difference between the leading asymptotic expression and the full residual, not solver error. That the two are of the same order makes them useful as a check, but they cannot replace one another.

Now consider a branch trap that must be watched. Sweep ``k = 0.1`` directly with the default seed:

.. code-block:: python

   bad = scan_gpdf_roots("langmuir", k_values=[0.1])
   print(bad["omega"])
   print(f"scan residual = {bad['dielectric_residual'][0]:.3e}")

Actual output:

.. code-block:: text

   [-1.01519753+8.57692635e-15j]
   scan residual = 2.015e-13

This result is still a valid root of the equation, but it lies on the negative real-frequency branch. More noteworthy: if instead you use ``solve_maxwellian_electrostatic_mode`` and pass the initial value as a **frequency** ``omega``, the same ``k = 0.1`` can find the positive root:

.. code-block:: python

   positive = solve_maxwellian_electrostatic_mode(
       k=0.1,
       initial_omega=1.0 - 0.01j,
   )
   print(f"omega = {positive['omega'].real:.6f} + {positive['omega'].imag:.1e}j")
   print(f"normalized residual = {positive['normalized_residual']:.3e}")

Actual output:

.. code-block:: text

   omega = 1.015198 + 1.6e-17j
   normalized residual = 4.547e-13

Both the positive and the negative root exist, with residuals below ``1e-12``. The difference comes from the seed: the ``initial_guess`` of ``scan_gpdf_roots`` is a **phase** ``x = omega/(sqrt(2) k)``, not a frequency ``omega``; the default phase seed ``1 - 0.1j`` corresponds at ``k = 0.1`` to a frequency seed of only about ``0.141 - 0.014i``, so it lands on the negative real-frequency branch. The default scan grid also happens to contain ``k = 0.1``, so plotting the default results directly as a curve shows a "jump" at the first point. This is not "the physical wave suddenly propagating backwards"; it is branch selection caused jointly by the seed unit, the solver basin and the scan order.

**What this section cannot establish.** One scan does not enumerate all roots and does not automatically select the physically most important branch; a small residual cannot rule out another branch with an equally small residual. The small-wavenumber asymptotic expression is not a root solver and cannot be extrapolated to ``k`` near 1. A scan failure rejects the whole scan and returns no partial result; this is not "some points could not be computed", it is a failure the caller must handle.

Fixed-pole approximation: replacing Z with a rational form
------------------------------------------------------------

The Ronnmark path of the kinetic tensor replaces the plasma dispersion function with a fixed-order rational approximation:

.. code-block:: text

   Z_J(z) = sum_{j=1}^{J} b_j / (z - c_j)

The poles ``c_j`` and residues ``b_j`` come from a preset table. ``evaluate_maxwellian_jpole`` supports ``J = 8, 12, 16, 24``; the upper half-plane uses the direct sum, and the lower half-plane uses the reflection relation

.. code-block:: text

   Z(z) = conj(Z(conj(z))) + 2 i sqrt(pi) exp(-z^2),   Im(z) < 0

to preserve the analytic continuation. Compare the approximation with the exact ``Z``:

.. code-block:: python

   from scirel.kinetic import evaluate_maxwellian_jpole, evaluate_plasma_dispersion

   z = np.array([0.2 + 0.7j, 1.0 + 0.5j, 2.0 + 0.5j, -0.5 - 0.3j])
   exact = evaluate_plasma_dispersion(z)["Z"]
   print("z       =", z)
   for order in (8, 16, 24):
       approx = evaluate_maxwellian_jpole(z, order=order)["Z"]
       err = np.abs(approx - exact) / np.abs(exact)
       print(f"J={order:2d}  " + "  ".join(f"{e:.2e}" for e in err))

Actual output:

.. code-block:: text

   z       = [ 0.2+0.7j  1. +0.5j  2. +0.5j -0.5-0.3j]
   J= 8  3.18e-11  3.76e-09  4.41e-07  1.03e-11
   J=16  2.65e-14  1.66e-14  7.90e-15  9.09e-15
   J=24  7.41e-14  5.51e-14  1.89e-13  6.71e-14

``J = 8`` has a relative error of about ``4.4e-7`` at ``z = 2 + 0.5i``, two orders of magnitude larger than at the first two points; ``J = 16`` pushes all four points down to the ``1e-14`` level; ``J = 24`` is in fact slightly worse than ``J = 16``. The fourth point ``z = -0.5 - 0.3i`` lies in the lower half-plane and goes through the reflection relation, with an error of the same order as the first three points. This is not a general rule that "more poles are less accurate"; it is the combined result of coefficient conditioning, rounding and truncation error at finite precision. The choice of pole table is approximation metadata, not a global accuracy certificate.

**What this section cannot establish.** Small errors at these four points do not prove that the approximation is good over the whole complex plane; near a pole, in a strongly damped region or deeper in the lower half-plane it needs a separate check. That ``J = 24`` is worse than ``J = 16`` does not mean ``J = 16`` is better everywhere. A fixed-order approximation cannot replace a convergence study, and a root computed with ``J = 8`` must not be treated as a physical mode just because it was computed.

Magnetized tensor: two paths at the same wave point
-----------------------------------------------------

Finally, assemble the magnetized kinetic dielectric tensor. Summing over species gives

.. code-block:: text

   K_ij = delta_ij - sigma_ij / (i omega epsilon_0)

Add the Maxwell curl terms:

.. code-block:: text

   n_x = c k_x / omega,   n_z = c k_z / omega
   D_xx = K_xx - n_z^2
   D_yy = K_yy - (n_x^2 + n_z^2)
   D_zz = K_zz - n_x^2
   D_xz = D_zx = K_xz + n_x n_z
   det(D) = 0 gives the eigenmodes

Signed ``kz`` interpretation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For a static, drift-free, isotropic Maxwellian, ``kz`` is a signed parallel wavenumber. The causal response obeys ``K(kx,-kz)=P K(kx,kz) P`` with ``P=diag(1,1,-1)``; ``D`` has the same reflection and the determinant is invariant. Internally the resonance denominators use ``|kz|`` and the four mixed components recover their signs; ``n_z`` still uses the caller's signed ``kz``. The conventional finite-harmonic path keeps its existing ``|kz|<1e-10`` clamp to ``+1e-10``, so zero and near-zero cases remain that path's numerical convention.

.. code-block:: python

   plus = evaluate_kinetic_dispersion_relation(..., kz=159.0, kx_frac=0.5)
   minus = evaluate_kinetic_dispersion_relation(..., kz=-159.0, kx_frac=0.5)
   P = np.diag([1.0, 1.0, -1.0])
   assert np.allclose(minus["K_sum_n"], P @ plus["K_sum_n"] @ P)
   assert np.allclose(minus["D_ronnmark"], P @ plus["D_ronnmark"] @ P)
   assert minus["determinant_sum_n"] == pytest.approx(plus["determinant_sum_n"])

This reflection is a coordinate symmetry. It does not write ``abs(kz)`` back to the returned ports and does not change charges, gyro signs, harmonic indices or ``kx``. It covers only the declared static Maxwellian condition; complex frequency, drift, anisotropy and other near-zero branches require separate validation.

``evaluate_kinetic_dispersion_relation`` computes both paths on the same equilibrium snapshot: the finite-harmonic sum (``lmx = 5``) and the Ronnmark fixed-pole approximation with ``J = 8``. It accepts SI species parameters, ``T00`` in eV, the dimensionless frequency ratio ``omega_frac``, the dimensionless perpendicular wavenumber ratio ``kx_frac``, and the **absolute** parallel wavenumber ``kz``. ``omega`` and ``kx`` are derived internally from ``wn`` and ``kn``; the caller must not pass absolute values and ratios at the same time.

Take ``omega_frac = 1000``, ``kx_frac = 0.5`` and ``kz = 159 1/m``:

.. code-block:: python

   from scirel.kinetic import evaluate_kinetic_dispersion_relation

   result = evaluate_kinetic_dispersion_relation(
       ms=[M_E, M_D], qs=[-E, E], ns_unit=[1.0, 1.0], Ts_unit=[1.0, 0.5],
       B0=1.0, n00=1e19, T00=1000.0,
       omega_frac=1000.0, kz=159.0, kx_frac=0.5,
   )
   ds = result["determinant_sum_n"]
   dr = result["determinant_ronnmark"]
   C = scales["c"]
   print(f"omega = {result['omega']:.6e} rad/s")
   print(f"kx    = {result['kx']:.6f} 1/m")
   print(f"n_x   = {C*result['kx']/result['omega']:.3f}")
   print(f"n_z   = {C*159.0/result['omega']:.3f}")
   print(f"det_sum      = {ds:.6e}")
   print(f"det_ronnmark = {dr:.6e}")
   print(f"relative difference = {abs(ds - dr)/abs(dr):.3e}")
   print(f"max |K_yx + K_xy| = {abs(result['K_ronnmark'][1,0] + result['K_ronnmark'][0,1]):.1e}")
   print(f"max |det(D) - det| = {abs(np.linalg.det(result['D_ronnmark']) - dr):.3e}")

Actual output:

.. code-block:: text

   omega = 4.757179e+10 rad/s
   kx    = 154.225641 1/m
   n_x   = 0.972
   n_z   = 1.002
   det_sum      = 2.348809e+02-1.121402e-11j
   det_ronnmark = 2.348827e+02-3.879698e-04j
   relative difference = 8.160e-06
   max |K_yx + K_xy| = 0.0e+00
   max |det(D) - det| = 1.421e-13

``omega = 4.757e10 rad/s`` corresponds to about 7.57 GHz; ``kx_frac = 0.5`` times ``kn = 308.45 1/m`` gives ``154.23 1/m``; ``kz = 159 1/m`` is an absolute wavenumber, not a ratio. The refractive indices ``n_x = 0.972`` and ``n_z = 1.002`` are close to the vacuum light-speed scale, but the determinant is not close to zero: ``det_sum`` is about ``234.88`` and ``det_ronnmark`` about ``234.88 - 3.88e-4 i``. So this wave point **is not a root**; this call only evaluates the determinant and does not find roots. ``n_x`` and ``n_z`` close to 1 only say the phase velocity is on the light-speed scale, not that the determinant is zero; ``det`` is determined by all tensor components together.

The relative difference between the two paths at this point is about ``8.2e-6``; ``det(D)`` differs from the returned Ronnmark determinant by about ``1.4e-13``, and the antisymmetry relation ``K_yx = -K_xy`` holds exactly (0). The difference is small, but this is only a consistency check at one point.

Sweep ``kx_frac`` from 0.25 to 4 while fixing ``omega_frac`` and ``kz``:

.. code-block:: python

   for kx_frac in (0.25, 0.5, 1.0, 2.0, 4.0):
       r = evaluate_kinetic_dispersion_relation(
           ms=[M_E, M_D], qs=[-E, E], ns_unit=[1.0, 1.0], Ts_unit=[1.0, 0.5],
           B0=1.0, n00=1e19, T00=1000.0,
           omega_frac=1000.0, kz=159.0, kx_frac=kx_frac,
       )
       a = r["determinant_sum_n"]
       b = r["determinant_ronnmark"]
       print(f"kx_frac={kx_frac:4.2f}  det_ron={b:.6e}  rel={abs(a-b)/abs(b):.3e}")

Actual output:

.. code-block:: text

   kx_frac=0.25  det_ron=2.125622e+02-3.698001e-04j  rel=1.847e-06
   kx_frac=0.50  det_ron=2.348827e+02-3.879698e-04j  rel=8.160e-06
   kx_frac=1.00  det_ron=3.452823e+02-4.605834e-04j  rel=1.464e-02
   kx_frac=2.00  det_ron=1.124469e+03-7.499993e-04j  rel=3.133e+00
   kx_frac=4.00  det_ron=9.624153e+03-1.891206e-03j  rel=2.031e+01

As ``kx_frac`` grows from 0.25 to 0.5, the relative difference is only between ``1.8e-6`` and ``8.2e-6``; at ``kx_frac = 1`` it is already about 1.5%, and at ``kx_frac = 2`` the relative difference exceeds 300%, and the two paths may even differ in sign. The two paths are not "the same answer" that can be silently interchanged: the finite-harmonic sum is affected by the ``lmx = 5`` truncation, and the Ronnmark path is affected by the ``J = 8`` pole approximation, so their domains of validity differ. This function performs no convergence verification and does not judge which path is closer to reality; it returns the two results side by side for the caller to cross-check.

**What this section cannot establish.** Evaluating a determinant is not finding a root; a nonzero ``det`` does not mean "there is no wave", it only means this wave point is not a root; a ``det`` close to zero does not automatically give a mode identity either. That the two paths agree at one small ``kx_frac`` cannot be extrapolated to larger wavenumbers, nor does it prove the absolute accuracy of either. Tensor components depend on the basis; both the finite-harmonic truncation and the pole order need independent convergence checks. This entry point provides no automatic mode identification, no global root enumeration, and no physical-validity certificate.

Which layer to use
--------------------

- You only need equilibrium scales and a wavevector projection: use :doc:`../reference/generated/scirel.kinetic.species-equilibrium-scales` and :doc:`../reference/generated/scirel.geometry.planar-wavevector-projection`.
- You only need a quick estimate of the anisotropic dielectric response in an RF background and do not care about kinetic damping: use :doc:`../reference/generated/scirel.dielectric.cold-plasma-tensor`.
- You want to check the Maxwellian electrostatic response at one complex frequency: use :doc:`../reference/generated/scirel.kinetic.maxwellian-electrostatic-mode`.
- You already have a frequency seed and want one root with a residual check: use :doc:`../reference/generated/scirel.kinetic.maxwellian-electrostatic-solver`.
- You want to scan several wavenumbers along the same branch: use :doc:`../reference/generated/scirel.kinetic.generalized-root-scans`.
- You want to use the small-wavenumber asymptotics as an independent check: use :doc:`../reference/generated/scirel.kinetic.generalized-small-k`.
- You want to evaluate the dispersion function repeatedly with a fixed-pole approximation: use :doc:`../reference/generated/scirel.kinetic.evaluate-maxwellian-jpole`; when you need an exact reference, use :doc:`../reference/generated/scirel.kinetic.plasma-dispersion-function`.
- You want to compare the finite-harmonic and Ronnmark paths on the same magnetized equilibrium snapshot: use :doc:`../reference/generated/scirel.kinetic.kinetic-dispersion-relation`.

This chapter does not cover ion-acoustic waves, beams, arbitrary velocity distributions, Vlasov initial-value problems, multi-fluid spectral methods or complex-wavenumber root scans. These topics have their own entry points and normalizations; do not carry the same seeds, the same units or the same "root equals mode" assumption over to them because the ``langmuir`` scan in this chapter runs.

Complete parameters, failure behavior and verification boundaries
-------------------------------------------------------------------

This chapter has shown only one representative point on each path. Complete parameters, array shapes, exception types and validation over a larger parameter domain are on the API reference pages; here we list only a few of the easiest boundaries to trip over.

- The cold tensor requires a finite, strictly positive frequency and a magnetic field of shape ``(..., 3)``; the species are mappings containing ``density_m3``, ``charge_c`` and ``mass_kg``. A zero magnetic field is supported and the tensor reduces to an isotropic one; an exact cyclotron resonance is rejected as a whole (``ColdPlasmaResonanceError``), and unrepresentable intermediate quantities raise ``ColdPlasmaOverflowError`` instead of returning NaN.
- The electrostatic root solver accepts ``xtol``, ``residual_tolerance`` and ``max_evaluations``; accepting a root requires the solver to succeed, the budget not to be exceeded, and both the normalized residual and the error gate to pass. A failure raises ``RuntimeError`` and returns no partial result; the error estimate is not a strict upper bound.
- A root scan rejects the whole scan if any point fails; the order of ``k_values`` is preserved, and the unit of ``initial_guess`` depends on the family (phase for Langmuir, frequency for generalized), so do not mix them. A scan does not guarantee uniqueness, the lowest damping, or automatic mode identification.
- The fixed-pole entry accepts only ``order = 8, 12, 16, 24``; other orders raise ``ValueError``. The lower half-plane uses the reflection relation and the approximation is singular at the poles; finite-order accuracy is not uniform. The choice of pole table is not itself an accuracy certificate.
- The magnetized tensor entry requires SI species parameters, with ``T00`` passed in eV; ``kz`` is an absolute wavenumber, while ``kx_frac`` and ``omega_frac`` are ratios relative to ``kn`` and ``wn``. Finite-harmonic truncation, complex-wavenumber support and near-zero-wavenumber handling differ among entry points, so confirm the model and normalization before switching entry points.
- All numbers in this chapter come from one representative example; they only show that these calls run in the current environment and give interpretable magnitudes. They do not constitute physical validation over an arbitrary parameter domain, nor do they replace the verification boundaries in the contracts.

.. seealso::

   If you care about how a "root" varies continuously with parameters rather than about a single scan, you can continue with the reference pages on complex-wavenumber roots and scans. If you care about how the kinetic tensor behaves for a more general distribution or magnetized geometry, enter the concrete function pages from this chapter's API reference, confirm units, sign conventions and applicability, and then build a new example.
