Distribution functions and neutral transport: from a velocity mesh to flux diagnostics
======================================================================================

This chapter answers a concrete question: **given the velocity distribution of a neutral molecule, how do we place it on a discrete velocity mesh, compute density, flow velocity, temperature and heat flux, then let the same distribution be attenuated by collisions in space, and finally read out the fluxes?**

We follow one continuous path: first build an axisymmetric cylindrical velocity mesh and its integration measure, then place a shifted Maxwellian on the mesh and reduce its moments, then assemble collision-loss frequencies into one-dimensional upwind transport coefficients, propagate one first-flight neutral generation, and finally use terminal reductions to obtain flux, pressure, temperature and heat flux. Each step includes actual run output and states which conclusions cannot be drawn from that step.

.. note::

   This chapter is a tutorial, not a contract summary. The full signature, parameter units, failure behavior and applicability of each function are in the API reference pages linked at the end of the chapter; the tutorial code calls only public SciRel functions, and every number comes from an actual execution in the current ``.venv``.

Model and conventions
---------------------

Space is one-dimensional, written ``x``, in metres. Velocity space is a two-dimensional axisymmetric cylindrical space: the radial velocity satisfies ``vr >= 0``, and the axial velocity ``vx`` may be positive or negative. The distribution function is written ``f(vr, vx, x)``, and velocity-space integrals use the cylindrical measure

.. code-block:: text

   dV_v = 2*pi*vr*dvr*dvx

After discretization, the volume weight of each velocity cell is the cell integral of ``2*pi*vr*dvr*dvx``. Every "density" and "flux" below is a sum over this measure, not a sum over an ordinary rectangular grid in ``(vr, vx)``.

This chapter treats an H2 molecule as one particle with a mass of 2 hydrogen mass units. Therefore:

- the Maxwellian seed entry point uses ``mass_amu=2.0`` and ``molecule_count=1``;
- the moment-reduction entry point uses ``isotope_mass_amu=2.0`` and ``molecularity=1``;
- the terminal-reduction entry points use ``mass_ratio=1.0`` (internally they take the molecule mass as ``2 * mass_ratio * m_H``).

This is not the only possible bookkeeping convention, but the whole set of parameters must be used together. The "Common pitfalls" section later shows how the numbers change if another set of factors is mixed in.

Velocity-mesh nodes are expressed in normalized velocity, in units of the thermal speed

.. code-block:: text

   Vth = sqrt(2*e*Tnorm / (m_amu*m_H))

where ``Tnorm`` is the mesh normalization temperature in eV. The spatial transport coefficients, however, require ``vx`` to share units with ``x`` and ``alpha``, so ``Vth`` must be multiplied back before entering spatial transport. The seed entry point does the opposite: it accepts a shift in m/s and divides by ``Vth`` internally.

Velocity mesh: nodes, measure and volume
----------------------------------------

Mesh generation and integration weights are two separate steps. ``create_adaptive_neutral_velocity_mesh`` builds a radial half-mesh ``vr`` from the ion temperature and requested energies, then mirrors it into a symmetric ``vx``. For a small temperature spread it uses a uniform base mesh on ``[0, 3.5]``; for a larger spread it uses quadratic stretching. Requested positive energies are inserted as exact nodes, and ``Tnorm`` is the mean of the "selected temperature/energy population".

``make_cylindrical_velocity_quadrature`` accepts the already given ``vr`` and ``vx`` and constructs half-cell faces, annular radial measures, cell volumes and ghosted difference coefficients. It performs no mesh adaptation and no unit conversion. The cell volume is

.. code-block:: text

   radial_measure[i] = pi*(r_right[i]^2 - r_left[i]^2)
   volume[i,j] = radial_measure[i] * dvx[j]

.. code-block:: python

   import numpy as np
   from scirel.kinetic import (
       create_adaptive_neutral_velocity_mesh,
       make_cylindrical_velocity_quadrature,
   )

   vx, vr, tnorm, ix, ir = create_adaptive_neutral_velocity_mesh(
       16, (1.0, 1.05), requested_energy_ev=(1.1,)
   )
   quad = make_cylindrical_velocity_quadrature(vr=vr, vx=vx)

   print(f"nvr = {vr.size}, nvx = {vx.size}, Tnorm = {tnorm:.3f} eV")
   print(f"vr[3:6] = {np.array2string(vr[3:6], precision=6)}")
   print(f"vr[ir] = {vr[ir]:.6f}, ix = {ix}, ir = {ir}")
   print(f"sum(volume) = {quad['volume'].sum():.6f}")
   print(f"outer face = {quad['vr_right'][-1]:.6f}")
   print(f"2*pi*R^3 = {2 * np.pi * quad['vr_right'][-1] ** 3:.6f}")
   print(f"positive first index = {quad['positive_vx_first_index']}")

Actual output:

.. code-block:: text

   nvr = 17, nvx = 34, Tnorm = 1.050 eV
   vr[3:6] = [0.875    1.023533 1.09375 ]
   vr[ir] = 1.023533, ix = [12 21], ir = 4
   sum(volume) = 295.444484
   outer face = 3.609375
   2*pi*R^3 = 295.444484
   positive first index = 17

The base mesh for ``nv=16`` has 17 nodes on ``[0, 3.5]``; after dropping 0 there are 16 radial half-nodes, and mirroring gives 32 axial nodes. Inserting the node for 1.1 eV makes that 17 radial and 34 axial nodes. ``Tnorm = 1.050`` is ``(1.0 + 1.05 + 1.1) / 3``, showing that the requested energy also enters the normalization population even though the temperature spread is still small enough to use the uniform branch. ``vr[4] = 1.023533`` is ``sqrt(1.1 / 1.05)``, not a base-mesh node.

The volume sum ``295.444484`` equals ``2*pi*R^3``, where ``R = 3.609375`` is the position of the outermost ghost face. This is volume closure under the half-cell extrapolation convention: all velocity cells exactly fill a cylinder of radius ``R`` and axial half-length ``R``. It verifies that "the measure fills the domain", not that "this mesh can accurately integrate your distribution".

What this section does not establish
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- A matching volume sum only says the cell partition closes; it does not prove that a 17×34 mesh is fine enough for a given distribution. Cold beams, high-energy tails or strongly anisotropic distributions may need more nodes.
- The outermost ghost face uses the convention "mirror the last node, then take a half cell". A different cell-face convention cannot reuse ``radial_measure``, ``dvx`` or ``volume`` here.
- Mesh nodes are normalized velocities, not m/s. Treating ``vr`` or ``vx`` directly as physical velocities when multiplying by a collision frequency produces spatial attenuation that is wrong by orders of magnitude.
- A requested energy changes ``Tnorm`` and may switch the uniform branch to the stretched branch. Do not assume that "adding one energy node" adds only one node without changing the other mesh positions.

Maxwellian seed: normalization and moments
------------------------------------------

The seed entry point constructs a shifted Maxwellian on a given mesh:

.. code-block:: text

   f(vr,vx) proportional to exp[-(vr^2 + (vx - s/Vth)^2) * molecule_count * Tnorm / T]
   sum(volume * f) = 1

It only constructs the normalized seed; it does not perform any later moment compensation. The axial shift ``s`` is given in m/s and divided by the thermal speed internally; the temperature ``T`` is a parameter of each shifted layer.

The moment-reduction entry point accepts ``f``, the velocity axes and the same ``volume``, and returns density, axial flux, flow velocity, pressure, temperature, diagonal stress and random heat flux. Density is ``sum(volume * f)``, axial flux is ``Vth * sum(volume * vx * f)``, flow velocity is flux divided by density, and temperature is pressure divided by density.

.. code-block:: python

   from scirel.kinetic import (
       build_shifted_maxwellian_seed,
       reduce_axisymmetric_neutral_moments,
   )

   seed = build_shifted_maxwellian_seed(
       vr=vr, vx=vx, tnorm_ev=tnorm,
       shifted_vx_m_s=np.array([3000.0]),
       temperature_ev=np.array([2.0]),
       mass_amu=2.0, molecule_count=1,
       cylindrical_volume=quad["volume"],
   )
   f = seed["distribution"][:, :, 0]
   mom = reduce_axisymmetric_neutral_moments(
       f[:, :, None], vx, vr, quad["volume"],
       normalization_temperature_ev=tnorm,
       isotope_mass_amu=2.0, molecularity=1,
   )

   print(f"thermal speed = {seed['thermal_speed_m_s']:.1f} m/s")
   print(f"shape = {f.shape}, integral = {np.sum(quad['volume'] * f):.12f}")
   print(f"density = {mom['density_m3'][0]:.6f} m^-3")
   print(f"flow = {mom['axial_velocity_m_s'][0]:.1f} m/s (input 3000)")
   print(f"T = {mom['temperature_ev'][0]:.4f} eV (input 2)")
   print(f"p = {mom['pressure_ev_m3'][0]:.4f} eV m^-3")
   print(f"stress_zz is stress_yy: {np.array_equal(mom['stress_zz_ev_m3'], mom['stress_yy_ev_m3'])}")

Actual output:

.. code-block:: text

   thermal speed = 10028.8 m/s
   shape = (17, 34), integral = 1.000000000000
   density = 1.000000 m^-3
   flow = 3009.1 m/s (input 3000)
   T = 1.9888 eV (input 2)
   p = 1.9888 eV m^-3
   stress_zz is stress_yy: True

``integral = 1`` is the volume-weighted normalization performed by the entry point itself; a density of 1 is another reading of the same fact. The flow velocity 3009.1 m/s is 0.3% above the input 3000, and the temperature 1.9888 eV is 0.56% below 2 eV. These differences come from the finite mesh: the velocity box extends only to ``±3.5 Vth``, there are only 17 radial nodes, the high-energy tail of the distribution is truncated, and the discrete sum is not an exact integral. They are not solver tolerances and not a physical "flow-velocity offset".

``p = 1.9888 eV m^-3`` agrees with ``n*T = 1 * 1.9888`` because temperature here is pressure divided by density. ``stress_zz`` is an independent copy of ``stress_yy``; that is the cylindrical-symmetry identification declared by the relation, not evidence that an independent ``zz`` stress calculation exists.

Repeating the same construction on finer meshes shows the differences shrinking directly:

.. code-block:: python

   for nv_check in (8, 16, 32):
       vx_c, vr_c, tn_c, _, _ = create_adaptive_neutral_velocity_mesh(
           nv_check, (1.0, 1.05), requested_energy_ev=(1.1,)
       )
       quad_c = make_cylindrical_velocity_quadrature(vr=vr_c, vx=vx_c)
       seed_c = build_shifted_maxwellian_seed(
           vr=vr_c, vx=vx_c, tnorm_ev=tn_c,
           shifted_vx_m_s=np.array([3000.0]),
           temperature_ev=np.array([2.0]),
           mass_amu=2.0, molecule_count=1,
           cylindrical_volume=quad_c["volume"],
       )
       mom_c = reduce_axisymmetric_neutral_moments(
           seed_c["distribution"], vx_c, vr_c, quad_c["volume"],
           normalization_temperature_ev=tn_c,
           isotope_mass_amu=2.0, molecularity=1,
       )
       print(
           f"nv={nv_check:2d}: u={mom_c['axial_velocity_m_s'][0]:.1f} m/s, "
           f"T={mom_c['temperature_ev'][0]:.4f} eV"
       )

Actual output:

.. code-block:: text

   nv= 8: u=3149.2 m/s, T=2.0193 eV
   nv=16: u=3009.1 m/s, T=1.9888 eV
   nv=32: u=2989.3 m/s, T=1.9844 eV

At ``nv=8`` the flow velocity is 5% high; at ``nv=32`` it drops to about -0.4%. This shows that the 0.3% in the previous paragraph is mainly discretization error, but it is still not an error bound and does not prove that ``nv=32`` is enough for other distributions.

What this section does not establish
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- The seed entry point returns a "normalized seed without moment compensation", not the physical distribution of any particular device. Its normalization and ``Tnorm`` are artificial conventions.
- Small differences between the computed and input flow velocity and temperature are discretization results; they change with the mesh. The 3009.1 m/s value is not the "true flow velocity" of the distribution, and 1.9888 eV is not a model-error estimate.
- The part of the distribution outside the mesh never enters the integral. A distribution with significant weight at ``|vx| > 3.5 Vth`` cannot be extrapolated from these numbers.
- Temperature is a centred second moment; it is not the ``temperature_ev`` parameter of the seed entry point unless mass, molecule count and normalization temperature all follow the same convention. Mixing factors systematically changes ``u`` and ``T``.
- ``stress_zz = stress_yy`` is a declaration of the relation, not a physical conclusion independently verified by one moment calculation.

Loss frequency and upwind coefficients
--------------------------------------

Neutral particles are lost in space through charge exchange, elastic collisions and finite duct walls. The total loss frequency is assembled as

.. code-block:: text

   alpha(vr,vx,x) = [Alpha_CX] + base_loss + Omega_EL + 2*vr/D

where the wall term applies only to a positive duct diameter ``D``; ``D = 0`` means wall loss is disabled, not that "the wall is at infinity". ``Alpha_CX`` is an optional channel and must be supplied explicitly as a nonnegative field of the same shape when enabled.

The upwind coefficients assemble ``alpha``, the spatial nodes ``x``, the axial velocity ``vx`` and the source distribution into six fields. For the positive-velocity branch, the forward recursion uses ``Ak`` and the diagonal source term ``Fk``; for the negative-velocity branch, the backward recursion uses ``Ck`` and ``Gk``. ``Bk`` and ``Dk`` are source coefficients used by the other "scattered generation" path. This section follows only the first-flight path, with the source set to zero, so the recursion actually uses ``Ak``, ``Ck`` and zero source terms.

.. code-block:: python

   from scirel.kinetic import (
       assemble_neutral_total_collision_frequency,
       assemble_neutral_upwind_transport_coefficients,
   )

   x = np.linspace(0.0, 2.0, 21)
   nx = x.size
   shape = (vr.size, vx.size, nx)

   base = np.full(nx, 1500.0)
   elastic = np.full(nx, 500.0)
   diameter = np.full(nx, 0.2)
   cx = np.full(shape, 2000.0)
   alpha = assemble_neutral_total_collision_frequency(
       vr, vx, base, elastic, diameter, cx
   )

   vx_phys = vx * seed["thermal_speed_m_s"]
   coef = assemble_neutral_upwind_transport_coefficients(
       x, vx_phys, alpha, np.zeros(shape)
   )

   print(f"alpha shape = {alpha.shape}")
   print(f"alpha(vr={vr[0]:.3f}, vx=+3.5) = {alpha[0, -1, 0]:.1f} s^-1")
   print(f"alpha(vr={vr[-1]:.3f}, vx=+3.5) = {alpha[-1, -1, 0]:.1f} s^-1")
   print(f"Ak(vr={vr[0]:.3f}, vx=+3.5) = {coef['Ak'][0, -1, 0]:.9f}")
   print(f"Ak(vr={vr[-1]:.3f}, vx=+3.5) = {coef['Ak'][-1, -1, 0]:.9f}")
   print(f"Ck(vr={vr[0]:.3f}, vx=-3.5) = {coef['Ck'][0, 0, 1]:.9f}")
   print(f"Fk all zero = {np.all(coef['Fk'] == 0.0)}")

Actual output:

.. code-block:: text

   alpha shape = (17, 34, 21)
   alpha(vr=0.219, vx=+3.5) = 4002.2 s^-1
   alpha(vr=3.500, vx=+3.5) = 4035.0 s^-1
   Ak(vr=0.219, vx=+3.5) = 0.988662699
   Ak(vr=3.500, vx=+3.5) = 0.988570280
   Ck(vr=0.219, vx=-3.5) = 0.988662699
   Fk all zero = True

At the lowest radial velocity ``alpha = 4002.2 s^-1``; at the highest it is ``4035.0 s^-1``. The difference of 32.8 s^-1 comes from the wall term: as ``vr`` goes from 0.21875 to 3.5, ``2*vr/D`` goes from 2.1875 to 35.0; charge exchange 2000, base loss 1500 and elastic 500 sum to 4000. Axial velocity does not affect ``alpha``, so the positive and negative branches have the same coefficient at the same ``vr``, and ``Ck`` equals ``Ak`` on mirrored nodes.

``Ak = 0.98866`` is the surviving fraction per 0.1 m cell. With ``dx = 0.1``, ``v = 35100.95 m/s`` and ``alpha = 4002.2``, the estimate is ``dx*alpha/(2v) = 0.00570``, so ``Ak`` is close to ``1 - 0.01134``, consistent with the output. ``Fk`` is all zero because this section sets the source distribution to zero; that does not mean the first-flight path never has source terms, only that this numerical experiment observes only attenuation after boundary injection.

What this section does not establish
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- ``alpha`` is an externally supplied loss frequency, not a self-consistent result computed from cross sections, density and temperature. Changing ``base``, ``elastic``, ``cx`` or the duct diameter changes the result; the 4002.2 here is not a "standard value" for any gas.
- ``Ak < 1`` only says that this combination of ``dx``, ``vx`` and ``alpha`` attenuates at each step; it does not prove that the scheme is stable for arbitrary step sizes or frequencies. The upwind scheme also has numerical diffusion, which a coarse mesh can mix into the physical attenuation.
- ``D = 0`` disables the wall term; it does not mean there is no wall. The shape of ``alpha`` is ``(nvr, nvx, nx)``, but ``base``, ``elastic`` and ``diameter`` in this section vary only with ``x``, and ``cx`` is a constant field. Velocity- or space-dependent fields require rechecking every cell.
- Coefficient assembly does not check physical resolution conditions such as "is the collision frequency smaller than ``v/dx``"; it checks only the input domain and finiteness.

First-flight generation: boundary injection and attenuation
-----------------------------------------------------------

``propagate_neutral_generation`` advances one neutral generation with the upwind recursion. For the first-flight path, at ``x=0`` it writes only the positive-velocity branch of ``incoming_boundary`` into the initial state and then recurses forward along the positive-velocity direction:

.. code-block:: text

   g[k+1] = Ak[k]*g[k] + Fk[k]

The negative-velocity branch recurses backward from the right boundary, but its right-boundary initial value stays zero and the source term ``Gk`` is also zero, so the entire negative branch stays zero.

.. warning::

   The ``incoming_boundary`` of ``first_flight`` acts only on the positive ``vx`` branch; the negative ``vx`` branch is not injected from the right boundary. If the physical problem requires injection from both ends, one first-flight call cannot be used to claim that both boundaries are handled.

To make the picture "incident from ``x=0``" self-consistent, we zero the negative-velocity half of the Maxwellian and keep only the positive half as the boundary. The volume integral of this boundary is then no longer 1 but about 0.623.

.. code-block:: python

   from scirel.kinetic import propagate_neutral_generation

   boundary = f.copy()
   boundary[:, vx < 0.0] = 0.0
   gen = propagate_neutral_generation(
       vx_phys, coef["Ak"], coef["Bk"], coef["Fk"],
       coef["Ck"], coef["Dk"], coef["Gk"],
       generation_kind="first_flight", incoming_boundary=boundary,
   )

   print(f"shape = {gen.shape}, finite = {np.all(np.isfinite(gen))}")
   print(f"negative-vx max = {np.abs(gen[:, vx < 0.0, :]).max():.1e}")
   for k in (0, 10, 20):
       print(f"n(x={x[k]:.1f}) = {np.sum(quad['volume'] * gen[:, :, k]):.6f} m^-3")

   j = np.argmax(vx)
   ratio = gen[0, j, :] / boundary[0, j]
   exact = np.exp(-alpha[0, j, 0] * x / vx_phys[j])
   print(f"fastest bin ratio(2 m) = {ratio[-1]:.9f}")
   print(f"exp(-alpha*L/v) = {exact[-1]:.9f}")
   print(f"max relative difference = {np.max(np.abs(ratio / exact - 1.0)):.2e}")

Actual output:

.. code-block:: text

   shape = (17, 34, 21), finite = True
   negative-vx max = 0.0e+00
   n(x=0.0) = 0.622978 m^-3
   n(x=1.0) = 0.333689 m^-3
   n(x=2.0) = 0.212893 m^-3
   fastest bin ratio(2 m) = 0.796091494
   exp(-alpha*L/v) = 0.796093461
   max relative difference = 2.47e-06

For the fastest velocity cell (smallest ``vr``, ``vx = +3.5 Vth``), the maximum relative difference between the recursion and the continuous exponential attenuation ``exp(-alpha*x/v)`` is ``2.47e-6``. This confirms that, with no source term and an ``alpha`` constant along ``x``, the first-flight recursion really implements the first-order discretization of "exponential attenuation along a characteristic" cell by cell. This check covers only one velocity cell and cannot replace a check of the whole distribution.

The integrated density drops from ``0.622978`` to ``0.212893``, a ratio of ``0.342``; it is clearly smaller than the fastest cell's ``0.796`` because slow particles attenuate much faster. After 2 m the surviving distribution has been velocity-filtered and is no longer the original Maxwellian. Treating ``0.342`` as "an exponential attenuation rate" is misleading: it is neither ``exp(-alpha L/v)`` for a single velocity nor enough to infer a unique ``alpha``.

What this section does not establish
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- This is not a self-consistent neutral-transport solution. There is no volume source, no recombination, no wall reflection, no second boundary, and no coupling to a plasma background; ``alpha`` is still externally supplied.
- A zero negative-velocity branch is a direct consequence of the first-flight boundary-injection scheme, not evidence that "there are no backward neutral particles physically". Filling the negative branch requires a volume source or boundary treatment at the other end.
- Agreement of a single cell with ``exp(-alpha*x/v)`` validates only the discretization along that one characteristic; it does not validate the integrated density, other velocity cells or a spatially varying ``alpha``.
- The first-order upwind scheme has numerical diffusion, and at ``dx = 0.1 m`` this diffusion may mix with the true gradient; no mesh-convergence study is performed here.
- The output is a distribution value, not a density or flux. ``gen`` must be used with the same ``volume``; a different measure cannot be compared directly.

Terminal diagnostics: flux and heat flux
----------------------------------------

The terminal-reduction functions turn a selected terminal distribution into spatial profiles. They accept normalized velocity axes, an explicit thermal speed, the distribution, radial weights and axial widths:

- ``reduce_terminal_molecular_flux_velocity`` returns axial flux and mean velocity;
- ``reduce_terminal_molecular_pressure_temperature`` returns pressure and temperature;
- ``reduce_terminal_molecular_heat_flux`` returns random heat flux and total heat flux.

All three entry points allow zero-width cells as long as each spatial slice has a positive integrated density. With positive weights they share the same discrete definitions as the moment reduction:

.. code-block:: text

   density = sum(volume*f)
   flux = Vth*sum(volume*vx*f)
   u = flux/density
   T = p/density

Positive ``radial_measure`` and ``dvx`` are used here, so these functions should agree term by term with the moment reduction on the overlapping fields.

The preceding ``gen`` is a normalized distribution with density about 1 m^-3. To obtain readable physical magnitudes, we multiply by a number density ``n0 = 1e20 m^-3``. Because ``alpha`` is externally supplied and does not depend on density, this scaling changes only the absolute diagnostic values, not the propagation result.

.. code-block:: python

   from scirel.kinetic import (
       reduce_terminal_molecular_flux_velocity,
       reduce_terminal_molecular_pressure_temperature,
       reduce_terminal_molecular_heat_flux,
   )

   n0 = 1.0e20
   f_phys = n0 * gen
   mom_phys = reduce_axisymmetric_neutral_moments(
       f_phys, vx, vr, quad["volume"],
       normalization_temperature_ev=tnorm,
       isotope_mass_amu=2.0, molecularity=1,
   )
   flux = reduce_terminal_molecular_flux_velocity(
       vx, seed["thermal_speed_m_s"], f_phys,
       quad["radial_measure"], quad["dvx"],
   )
   pt = reduce_terminal_molecular_pressure_temperature(
       vr, vx, 1.0, seed["thermal_speed_m_s"], f_phys,
       quad["radial_measure"], quad["dvx"],
   )
   hf = reduce_terminal_molecular_heat_flux(
       vr, vx, 1.0, seed["thermal_speed_m_s"], f_phys,
       quad["radial_measure"], quad["dvx"],
   )

   for k in (0, 20):
       print(f"x={x[k]:.1f} m:")
       print(f"  n = {mom_phys['density_m3'][k]:.6e} m^-3")
       print(f"  flux = {flux['flux_profile_m2_s'][k]:.6e} m^-2 s^-1")
       print(f"  u = {flux['mean_velocity_profile_m_s'][k]:.6e} m/s")
       print(f"  p = {pt['pressure_profile_ev_m3'][k]:.6e} eV m^-3")
       print(f"  T = {pt['temperature_profile_ev'][k]:.6f} eV")
       print(f"  q_rand = {hf['random_heat_flux_profile_w_m2'][k]:.6e} W m^-2")
       print(f"  q_total = {hf['total_heat_flux_profile_w_m2'][k]:.6e} W m^-2")

   rel_flux = np.max(
       np.abs(flux["flux_profile_m2_s"] - mom_phys["axial_flux_m2_s"])
       / np.abs(mom_phys["axial_flux_m2_s"])
   )
   rel_p = np.max(
       np.abs(pt["pressure_profile_ev_m3"] - mom_phys["pressure_ev_m3"])
       / np.abs(mom_phys["pressure_ev_m3"])
   )
   rel_q = np.max(
       np.abs(hf["random_heat_flux_profile_w_m2"] - mom_phys["random_heat_flux_w_m2"])
       / np.abs(mom_phys["random_heat_flux_w_m2"])
   )
   print(f"relative mismatch: flux {rel_flux:.2e}, p {rel_p:.2e}, q_rand {rel_q:.2e}")

Actual output:

.. code-block:: text

   x=0.0 m:
     n = 6.229784e+19 m^-3
     flux = 5.671956e+23 m^-2 s^-1
     u = 9.104579e+03 m/s
     p = 9.934682e+19 eV m^-3
     T = 1.594707 eV
     q_rand = 2.409290e+04 W m^-2
     q_total = 3.945699e+05 W m^-2
   x=2.0 m:
     n = 2.128927e+19 m^-3
     flux = 2.781894e+23 m^-2 s^-1
     u = 1.306712e+04 m/s
     p = 3.357300e+19 eV m^-3
     T = 1.576992 eV
     q_rand = 5.230610e+03 W m^-2
     q_total = 2.244745e+05 W m^-2
   relative mismatch: flux 1.68e-15, p 9.17e-16, q_rand 4.22e-14

The density drops to ``0.342`` of its original value, while the flux drops to ``0.490``: they differ because the mean velocity rises from 9.10 km/s to 13.07 km/s. Slow particles are lost preferentially, and the surviving distribution carries a higher flux per particle. Flux is not "density times a constant velocity"; it is the profile of ``n*u`` and must be read together with density and velocity.

Pressure drops to ``0.338``, while temperature changes only from ``1.5947`` to ``1.5770`` eV (about ``0.989``). Temperature is a centred second moment, so density and pressure can fall substantially while temperature stays nearly unchanged; here "nearly" is not conservation. Note that the boundary temperature is no longer the seed parameter 2 eV: we kept only the positive-velocity half, and the centred second moment of a half-Maxwellian differs from that of a full Maxwellian. The 1.59 eV is a property of the filtered boundary distribution.

The random heat flux falls from ``2.41e4`` to ``5.23e3`` W/m², and the total heat flux from ``3.95e5`` to ``2.24e5`` W/m². At ``x=0`` the total heat flux is about 16.4 times the random heat flux because it also contains the bulk kinetic-energy flux and the enthalpy flux; the random heat flux describes only fluctuations relative to the mean flow. They answer different questions and are not interchangeable.

The last line's relative differences ``1.68e-15``, ``9.17e-16`` and ``4.22e-14`` show that the terminal reduction and the moment reduction really consume the same discrete distribution on the same positive weights. They are algebraic consistency checks, not independent physical validation, and not error bounds.

What this section does not establish
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- These profiles correspond to only one boundary distribution, one ``alpha`` model and one mesh. They are not a conservation proof, and they do not cover wall reflection, volume sources, recombination or feedback with a plasma.
- ``n0 = 1e20`` is a demonstration scaling. Heat flux, flux and pressure all scale linearly with ``n0``; if ``alpha`` actually depended on density, this scaling would no longer be consistent with the propagation.
- A nearly unchanged temperature does not mean thermal equilibrium or energy conservation. The total-heat-flux expression contains several terms; changing the definition or the reference frame changes the reading.
- The terminal entry points allow zero-weight cells; this example does not trigger that branch. The behavior of zero-weight cells cannot be extrapolated from these positive-weight results.
- Agreement at the ``1e-15`` level does not mean physical accuracy; it only says the two post-processing paths perform the same discrete sum. The real error sources are the mesh, ``alpha``, the boundary distribution and velocity truncation.

Common pitfalls
---------------

**Normalized vs physical velocity.** The mesh ``vx`` is dimensionless, ``alpha`` is in s^-1, and ``x`` is in m. ``Vth`` must be multiplied in before entering the upwind coefficients; otherwise ``dx*alpha/vx`` is not dimensionless and the attenuation is wrong by orders of magnitude. The seed entry point instead accepts a shift in m/s and divides by ``Vth`` internally. The two entry points use opposite conventions, so do not guess units from parameter names.

**Use the mass factors as a set.** The H2 bookkeeping in this chapter is ``mass_amu=2``, ``isotope_mass_amu=2``, ``molecularity=1`` and terminal ``mass_ratio=1``. If the same distribution is kept but the moment reduction is changed to ``isotope_mass_amu=1`` and ``molecularity=2``, the thermal speed and molecule mass change their factors together, and the same distribution gives a flow velocity of about ``4453.6 m/s`` and a temperature of ``4.0385 eV`` instead of the 3009.1 m/s and 1.9888 eV above. That is inconsistent bookkeeping, not a physical change.

**Requested energy changes ``Tnorm``.** This chapter sets ``requested_energy_ev`` to ``(1.1,)``, so ``Tnorm`` is 1.050 eV and the temperature spread still follows the uniform branch. Setting it to ``(5.0,)`` changes ``Tnorm`` to 2.35 eV and switches the mesh to the stretched branch; the same ``nv`` no longer produces the nodes above. Adding an energy node is not "just one more node".

**First-flight boundary fills only the positive-velocity branch.** The ``incoming_boundary`` of ``first_flight`` writes only positive ``vx`` at ``x=0``; the negative branch recurses backward from a zero right-boundary value, with no boundary injection. For two-sided incidence, one first-flight call cannot be treated as a two-boundary problem.

**Density attenuation is not a single exponential.** The fastest cell follows ``exp(-alpha*x/v)``, but the integrated density ratio 0.342 is the result of velocity filtering. Do not fit an "effective attenuation rate" to the integrated density and use it to infer ``alpha``; different velocities attenuate at different rates.

**Random heat flux is not total heat flux.** The former is the heat flow carried by centred fluctuations; the latter also includes the transport of bulk kinetic energy and enthalpy. In this chapter the two differ by about a factor of 16 at ``x=0``. When quoting a "heat flux", always say which one.

**Consistency checks are not error estimates.** Agreement at the ``1e-15`` level between the terminal and moment reductions only says the sums agree under the same discrete measure; it does not tell you whether the mesh is fine enough, whether ``alpha`` is right, or whether the boundary distribution is physical.

When to use which function
--------------------------

- To build a velocity mesh: use :doc:`../reference/generated/scirel.kinetic.adaptive-neutral-velocity-mesh`. Pay attention to the temperature-spread threshold, requested-energy insertion and the definition of ``Tnorm``.
- To construct an integration measure from existing ``vr`` and ``vx``: use :doc:`../reference/generated/scirel.kinetic.cylindrical-velocity-quadrature`. It does not generate a mesh and does not convert units.
- To build a shifted Maxwellian seed: use :doc:`../reference/generated/scirel.kinetic.shifted-maxwellian-seed`. It performs no moment compensation, and its normalization depends on the ``cylindrical_volume`` you supply.
- To obtain density, flow velocity, temperature, stress and random heat flux from a distribution: use :doc:`../reference/generated/scirel.kinetic.axisymmetric-neutral-moments`. Note the empty-slice policy and the ``stress_zz`` alias convention.
- To assemble the total loss frequency: use :doc:`../reference/generated/scirel.kinetic.neutral-total-collision-frequency`. When charge exchange is enabled, the frequency field must be supplied explicitly; ``D = 0`` disables the wall term.
- To assemble one-dimensional upwind coefficients: use :doc:`../reference/generated/scirel.kinetic.neutral-upwind-transport-coefficients`. The first-flight and scattered paths consume different coefficients, so choose ``generation_kind`` first.
- To propagate one neutral generation: use :doc:`../reference/generated/scirel.kinetic.neutral-generation-propagation`. First flight uses only the positive-velocity boundary; the scattered path requires ``scattered_source_distribution``.
- To read flux and flow velocity from a terminal distribution: use :doc:`../reference/generated/scirel.kinetic.terminal-flux-velocity-reduction`; for pressure and temperature use :doc:`../reference/generated/scirel.kinetic.terminal-pressure-temperature-reduction`; for random and total heat flux use :doc:`../reference/generated/scirel.kinetic.terminal-heat-flux-reduction`.
- If the source has a spatial shape rather than entering from a boundary, first look at :doc:`../reference/generated/scirel.kinetic.spatial-source-shape-normalization`, then decide whether to use the scattered generation. This chapter does not cover that path.

Applicability and validation boundaries
---------------------------------------

The numbers in this chapter correspond only to this model: one-dimensional space, two-dimensional axisymmetric velocity, H2 mass bookkeeping, externally supplied ``alpha``, and first-flight boundary injection. It does not cover:

- magnetized or two-/three-dimensional spatial transport;
- a solve self-consistently coupled to plasma density, temperature and potential;
- wall reflection, internal molecular degrees of freedom, vibrational/rotational levels and chemical reaction networks;
- nonlinear Boltzmann right-hand sides, multi-generation accumulation and convergence criteria;
- cross-species mesh interpolation.

These capabilities have their own entry points and contracts; do not extrapolate the scripts in this chapter. Parameter validation, exception types, complete input/output fields and the applicability of each function are in the API reference pages linked at the end of the chapter; they are generated from contracts and are a different layer of evidence from the actual run numbers in this chapter.

The validation boundary of this chapter is: the scripts really ran in order in the current ``.venv``; every output block comes from that execution; the single-cell exponential attenuation and the terminal/moment consistency are two independent numerical checks. They do not constitute validation over the full parameter domain, and they do not approve the physical applicability of ``alpha``, the boundary distribution or the mesh.

.. seealso::

   If you are more interested in frequency-domain roots and initial-value evolution of the kinetic equation, continue with :doc:`/tutorials/kinetic-initial-value`; if you need to choose entry points in another domain, return to :doc:`/user-guide/index`.
