Electromagnetism: from one current loop to the poloidal field
======================================================================

This chapter follows one concrete question: **given the geometry and drive currents of a set of axisymmetric coils, how do we obtain the flux and magnetic field at a point in space; and if all we have is a flux grid, how do we recover the poloidal field?**

The path is continuous: first compute the Green response of one loop at a few points, then discretize a rectangular cross-section into ordered current filaments and superpose them by current, then combine a pair of coils with ``Device``, then recover ``B_R`` and ``B_Z`` from a flux grid, and finally write the response as a matrix and explain the conductor boundary correction. At the end of the chapter we explain separately why two quantities both called ``psi`` cannot simply be subtracted from one another.

.. note::

    This chapter is a tutorial, not a contract summary. The complete signature, parameter units, failure behavior and applicability of every function are on the API reference pages linked at the end of the chapter; the code uses only public SciRel functions.

Setup: coordinates, units and the Green response
----------------------------------------------------------------------

Consider axisymmetric fields in cylindrical coordinates ``(R, phi, Z)``: no quantity depends on ``phi``. Take the toroidal component of the vector potential, ``A_phi(R, Z)``, and define

.. code-block:: text

   psi = R * A_phi
   B_R = -(1/R) * dpsi/dZ
   B_Z =  (1/R) * dpsi/dR

The unit of ``psi`` is Wb/rad (flux per radian) and the unit of ``B`` is T. The "per radian" here is not an optional accounting convention: the flux through a full toroidal circuit is ``2*pi*psi``, so ``psi`` and ``Wb`` must not be mixed.

For an ideal circular current filament of radius ``R_s``, axial position ``Z_s`` and weight ``w``, the response at a target point ``(R, Z)`` is written as

.. code-block:: text

   (gpsi, gBR, gBZ)   units: Wb/rad/A, T/A, T/A

It is the response to a **unit current**; the weight is already folded into the returned values. Given the current ``I_i`` in each filament, the total field is ``sum_i I_i * g_i``. This linear relation is the basis of all the superpositions below, and it is the only "composition" that this model allows.

Coordinates are always in metres and currents in amperes. ``R=0`` is the cylindrical axis; on the axis ``B_R=0`` and ``psi=0``. An ideal current filament has no finite radius and no conductor interior; a target point lying exactly on a filament is treated by the aggregate entry as a discrete zero-self term, not as a physical self-field.

Start with one loop: response, symmetry and the on-axis limit
----------------------------------------------------------------------

Start with the smallest question: for a loop of radius 0.35 m carrying 1 A, what are its flux and magnetic field at four points?

.. code-block:: python

   import numpy as np
   from scirel.field import circular_filament_green_response

   loop = [[0.35, 0.0, 1.0]]              # R (m), Z (m), weight
   targets = np.array([[0.20, -0.10], [0.20, 0.10], [0.0, 0.0], [0.35, 0.30]])
   g = circular_filament_green_response(loop, targets)

   print("gpsi (Wb/rad/A):", np.array2string(g["gpsi"], precision=9))
   print("gBR  (T/A)     :", np.array2string(g["gBR"], precision=9))
   print("gBZ  (T/A)     :", np.array2string(g["gBZ"], precision=9))

   mu0 = 4e-7 * np.pi
   axis = mu0 * 0.35**2 / (2.0 * (0.35**2)**1.5)
   print("axis analytic BZ/A:", axis)
   print("ratio:", g["gBZ"][2] / axis)

Actual output:

.. code-block:: text

   gpsi (Wb/rad/A): [3.408844654e-08 3.408844654e-08 0.000000000e+00 3.406704663e-08]
   gBR  (T/A)     : [-5.941571148e-07  5.941571148e-07  0.000000000e+00  4.269269023e-07]
   gBZ  (T/A)     : [1.800093910e-06 1.800093910e-06 1.795195802e-06 3.220178423e-07]
   axis analytic BZ/A: 1.7951958020513107e-06
   ratio: 0.9999999999999999

The first two target points are mirror images about ``Z=0``: ``gpsi`` and ``gBZ`` are the same, while ``gBR`` changes sign. This is exactly the mirror symmetry of a loop: the axial field points the same way, while the radial field changes sign with the direction in which the field lines circulate. At the on-axis point ``gBR`` is 0, and ``gBZ`` agrees with the analytic expression

.. code-block:: text

   B_Z(axis) = mu0 * I * R_s^2 / (2 * (R_s^2 + Z^2)^(3/2))

which for ``I=1 A`` gives ``1.795195802e-6 T``, a ratio of 1. This is a check of the kernel and the on-axis limit, not a validation of a real coil.

The fourth point ``(0.35, 0.30)`` has ``gBZ = 3.220e-7 T/A``, about 1/5.6 of the value at ``(0.20, 0.10)``, which agrees with the intuition that the field weakens farther from the filament. But its ``gpsi`` is ``3.4067e-8 Wb/rad/A``, almost the same as at the first two points. ``psi`` is a flux function, not a field strength; two points can lie on nearby flux surfaces while their ``B`` magnitudes differ a lot.

What this section cannot establish: these numbers are responses per ampere, so a 1000 A result requires multiplying by 1000; the model has no finite filament radius, insulation layer, conductor interior or on-filament self-field. The aggregate entry treats an exactly coincident target point as a discrete zero-self term and skips it, which is not the same as the physical self-field being zero.

Discretizing a cross-section into ordered current filaments
----------------------------------------------------------------------

A real coil has a cross-section. Here we approximate a rectangular cross-section by a set of ideal circular filaments and first look only at the geometry:

.. code-block:: python

   import numpy as np
   from scirel.field import discretize_rectangular_coil

   points = discretize_rectangular_coil(
       r0=0.35, z0=0.0, nr=3, nz=3, dr=0.06, dz=0.06
   )
   print(points)

Actual output:

.. code-block:: text

   [[ 0.29 -0.06]
    [ 0.29  0.  ]
    [ 0.29  0.06]
    [ 0.35 -0.06]
    [ 0.35  0.  ]
    [ 0.35  0.06]
    [ 0.41 -0.06]
    [ 0.41  0.  ]
    [ 0.41  0.06]]

The output order is **radial index outermost, axial index innermost**: first hold ``R=0.29`` and run through ``Z=-0.06, 0, 0.06``, then move to ``R=0.35``. ``dr`` and ``dz`` are the spacings between neighbouring filaments, not half-widths of the cross-section; ``nr=3, dr=0.06`` gives a radial span of ``0.12 m``, not ``0.06 m``. The rotation is centred on ``(r0, z0)`` and the angle is in degrees.

This section has produced geometry only: no current, weights or turns. 9 filaments do not automatically mean a 9-turn coil; the function has no turn count or fill information, it is only a discrete representation of a rectangular point lattice.

What this section cannot establish: refining the lattice does not automatically mean greater accuracy. Different ``nr, nz`` are different discretizations of the same cross-section; unless you also define the functional you want to compare (for example the on-axis ``B_Z``) and run a convergence sequence, you cannot say which one is "more true".

Superposing currents: from one loop to 9 filaments
----------------------------------------------------------------------

Now distribute a total current of 1000 A over the 9 filaments, ``1000/9 A`` each, keep the weights at 1, and compare the single loop with the filament bundle at the same target points:

.. code-block:: python

   import numpy as np
   from scirel.field import (
       circular_filament_green_response,
       dense_axisymmetric_green_response,
       discretize_rectangular_coil,
       superpose_current_green_field,
   )

   targets = np.array([[0.20, -0.10], [0.0, 0.0], [0.35, 0.30]])
   points = discretize_rectangular_coil(0.35, 0.0, 3, 3, 0.06, 0.06)
   rzw = np.column_stack((points, np.ones(len(points))))
   g = dense_axisymmetric_green_response(targets, rzw)       # (target, source)

   currents = np.full(len(points), 1000.0 / len(points))      # total 1000 A
   field = superpose_current_green_field(
       currents, g["gpsi"], g["gBR"], g["gBZ"]
   )
   print("matrix shape:", g["gBZ"].shape)
   print("BZ 9-filament (T):", np.array2string(field["BZ"], precision=9))

   single = circular_filament_green_response([[0.35, 0.0, 1000.0]], targets)
   print("BZ single loop (T):", np.array2string(single["gBZ"], precision=9))

Actual output:

.. code-block:: text

   matrix shape: (3, 9)
   BZ 9-filament (T): [0.001811259 0.001774477 0.000330107]
   BZ single loop (T): [0.001800094 0.001795196 0.000322018]

``dense_axisymmetric_green_response`` returns a ``(target, source)`` matrix, and ``superpose_current_green_field`` uses the same orientation contract: the first axis is the target and the second is the source, the contraction runs over source columns with the current vector, and the output preserves target order. No transpose is needed here. If the matrix is square the target and source axes have the same length, so mistakenly putting the source on the first axis does not raise an error; it silently contracts along the wrong axis. Always interpret the matrix as target-row/source-column when calling.

After spreading the current over ``R=0.29..0.41`` and ``Z=-0.06..0.06``, the on-axis ``B_Z`` changes from ``1.7952e-3 T`` to ``1.7745e-3 T``, about 1.2% lower; at ``(0.20,-0.10)`` it is about 0.6% higher; at ``(0.35,0.30)`` it is about 2.5% higher. These differences are not a "correction"; they are two different source models: the single loop puts all the current on one filament, while the bundle spreads the same total current out.

What this section cannot establish: one resolution does not prove convergence, and equal weights are also a modelling choice. A real winding has a known fill and arrangement that cannot be inferred from cross-section geometry alone. If you pass 1000 A as the current of every filament, the total current becomes 9000 A, which is one of the most common order-of-magnitude mistakes.

Combining a pair of coils with ``Device``
----------------------------------------------------------------------

A single coil is rarely used on its own. ``Device`` registers sub-sources in attribute-assignment order and evaluates the field on a shared grid. Below we place two identical coils at ``Z=+0.25`` and ``Z=-0.25``, first with the same direction and then with the lower current reversed:

.. code-block:: python

   import numpy as np
   from scirel.geometry import RectMesh
   from scirel.electromagnetism import Device, RectangularCoil

   mesh = RectMesh(rmin=0.0, rmax=0.65, nr=66, zmin=-0.4, zmax=0.4, nz=41)
   device = Device(mesh=mesh)
   device.upper = RectangularCoil(0.355, 0.25, 2, 2, 0.045, 0.03, current=250.0)
   device.lower = RectangularCoil(0.355, -0.25, 2, 2, 0.045, 0.03, current=250.0)

   def midplane(d):
       psi = d.psi().reshape(mesh.shape)
       br = d.BR().reshape(mesh.shape)
       bz = d.BZ().reshape(mesh.shape)
       iz = np.argmin(np.abs(mesh.Z[:, 0]))
       ir = np.argmin(np.abs(mesh.R[0, :] - 0.35))
       return psi[iz, ir], br[iz, ir], bz[iz, ir]

   print("children:", [type(s).__name__ for s in device.current_sets])
   print("currents:", device.current)
   psi, br, bz = midplane(device)
   print(f"same direction: psi={psi:.6e}  BR={br:.3e}  BZ={bz:.6e}")
   device.lower.current = -250.0
   psi, br, bz = midplane(device)
   print(f"opposite      : psi={psi:.6e}  BR={br:.6e}  BZ={bz:.3e}")

Actual output:

.. code-block:: text

   children: ['RectangularCoil', 'RectangularCoil']
   currents: [250. 250.]
   same direction: psi=8.656565e-05  BR=-1.271e-19  BZ=7.915351e-04
   opposite      : psi=1.482308e-21  BR=-1.145770e-03  BZ=4.659e-21

The two sub-sources appear in assignment order, and ``device.current`` returns ``[250, 250]``. ``psi()`` returns the flattened target-point order; here ``reshape(mesh.shape)`` restores the ``(nz, nr)`` grid. ``mesh.Z[:, 0]`` and ``mesh.R[0, :]`` are the axial and radial coordinate axes, respectively.

With the same direction, the central ``B_Z`` on the midplane adds to ``7.915e-4 T``, and ``B_R`` cancels through mirror symmetry to the ``1e-19`` level; with opposite currents, ``B_Z`` cancels to ``5e-21`` while ``B_R`` adds to ``-1.146e-3 T``. This is the difference between a "same-direction pair" and an "opposite-direction pair": the former gives an axial field at the centre, the latter a radial field. Calling the opposite pair a quadrupole field is a useful analogy, but here only one point has been computed, so we cannot claim that the whole field is a quadrupole field.

After changing ``device.lower.current``, the sub-source cache is invalidated and the next call recomputes the response; an old ``psi`` array saved earlier does not update automatically.

``Device`` also accepts a whole-device override: a scalar current applies to every sub-source, and a vector current maps one-to-one in sub-source order. The latter is the most direct way to check "which sub-source receives which current".

What this section cannot establish: this is a linear superposition of vacuum, ideal filaments in axisymmetry; there is no plasma response, conducting shell, coil box or three-dimensional geometry. The zero at the centre is a consequence of a specific symmetry, not a global field null.

Recovering the poloidal field from a flux grid
----------------------------------------------------------------------

``Device`` can already return ``B_R`` and ``B_Z`` directly. But in many workflows the flux is the quantity that is solved for or stored, and the field must be recovered from a ``psi`` grid. Below we use the same two coils with both currents in the same direction, and compare the direct field with the field obtained by differencing ``psi``:

.. code-block:: python

   import numpy as np
   from scirel.geometry import RectMesh
   from scirel.electromagnetism import Device, RectangularCoil
   from scirel.field import compute_poloidal_field_magnitude, poloidal_field_from_flux

   mesh = RectMesh(rmin=0.0, rmax=0.65, nr=66, zmin=-0.4, zmax=0.4, nz=41)
   device = Device(mesh=mesh)
   device.upper = RectangularCoil(0.355, 0.25, 2, 2, 0.045, 0.03, current=250.0)
   device.lower = RectangularCoil(0.355, -0.25, 2, 2, 0.045, 0.03, current=250.0)

   psi = device.psi().reshape(mesh.shape)
   bz = device.BZ().reshape(mesh.shape)
   br = device.BR().reshape(mesh.shape)
   rec = poloidal_field_from_flux(mesh.R, mesh.Z, psi)

   window = (mesh.R >= 0.15) & (mesh.R <= 0.25) & (np.abs(mesh.Z) <= 0.10)
   print("max |dBZ| in window (T):", np.abs(rec["B_Z"] - bz)[window].max())
   print("max |dBR| in window (T):", np.abs(rec["B_R"] - br)[window].max())

   iz = np.argmin(np.abs(mesh.Z[:, 0]))
   for r0 in (0.0, 0.15, 0.30, 0.45):
       ir = np.argmin(np.abs(mesh.R[0, :] - r0))
       print(f"R={r0:4.2f}  direct BZ={bz[iz, ir]:.6e}  recovered={rec['B_Z'][iz, ir]:.6e}")

   mag = compute_poloidal_field_magnitude(rec["B_R"], rec["B_Z"])
   print(f"B0_default = {mag['B0_default']:.6e} T")
   print(f"max |B|    = {mag['B'].max():.6e} T")

Actual output:

.. code-block:: text

   max |dBZ| in window (T): 1.821192022434786e-06
   max |dBR| in window (T): 2.2966746331177005e-06
   R=0.00  direct BZ=1.931877e-03  recovered=1.931621e-03
   R=0.15  direct BZ=1.790702e-03  recovered=1.789815e-03
   R=0.30  direct BZ=1.131914e-03  recovered=1.130874e-03
   R=0.45  direct BZ=2.094011e-04  recovered=2.096862e-04
   B0_default = 1.689570e-03 T
   max |B|    = 7.481667e-03 T

``poloidal_field_from_flux`` requires ``R``, ``Z`` and ``psi`` to be equal-shaped two-dimensional arrays on a strictly rectilinear grid with at least 3 points per axis. It evaluates ``dpsi/dZ`` and ``dpsi/dR`` with stable local differences and then divides by ``R``. On the ``R=0`` column, ``B_R`` is set to zero and ``B_Z`` uses the even-function limit ``2*(psi[:,1]-psi[:,0])/R[1]**2``.

In the selected smooth window the maximum absolute error in ``B_Z`` is ``1.82e-6 T`` and in ``B_R`` is ``2.30e-6 T``; the maximum ``B_Z`` in the window is about ``2e-3 T``, so the relative error is about ``0.1%``. The on-axis value ``1.931877e-3`` differs from the recovered ``1.931621e-3`` by about ``0.013%``. These differences come from finite-difference truncation, not from two different physical models.

Points close to the coils are outside this window. There the field varies rapidly, and the local-difference error in ``psi`` grows significantly. Do not use the recovered field directly on the winding surface, and do not use it to judge "the peak near the coil".

``compute_poloidal_field_magnitude`` returns ``B = hypot(B_R, B_Z)`` and clips the magnitude floor to ``1e-30``; ``B0_default`` is the median of these magnitudes, not the central field and not an automatically applied normalization factor. This floor is part of the numerical contract and does not mean the physical field is really nonzero.

What this section cannot establish: the recovered field is not an independent measurement, it is only the derivative of the same ``psi``; grid resolution and the difference stencil determine its accuracy. ``B0_default`` is only a descriptive reference value.

Response matrices, zero self terms and boundary correction
----------------------------------------------------------------------

Writing the response as a matrix makes the axes of the linear superposition clearer. ``get_gpsi`` returns a ``(target, source)`` flux matrix on the given ``R,Z`` nodes, while ``green_response_matrices`` allows the target and source to be two different point sets:

.. code-block:: python

   import numpy as np
   from scirel.electromagnetism import get_gpsi, green_response_matrices
   from scirel.field import circular_filament_green_response

   R, Z = np.meshgrid([0.2, 0.35, 0.5], [-0.3, 0.0, 0.3])
   G = get_gpsi(R, Z)
   print("G shape:", G.shape)
   print("diagonal:", np.diag(G))
   print("symmetry error:", np.max(np.abs(G - G.T)))

   sources = np.array([[0.355, 0.25, 1.0], [0.355, -0.25, 1.0]])
   targets = np.array([[0.15, 0.0], [0.30, 0.10], [0.50, -0.05]])
   gpsi, gbr, gbz = green_response_matrices(targets, sources)
   currents = np.array([250.0, 250.0])
   print("matrix shapes:", gpsi.shape, gbr.shape, gbz.shape)
   print("BZ via matrix:", np.array2string(gbz @ currents, precision=9))

   single = circular_filament_green_response(sources, targets)
   print("BZ via kernel:", np.array2string(single["gBZ"] * 250.0, precision=9))

Actual output:

.. code-block:: text

   G shape: (9, 9)
   diagonal: [0. 0. 0. 0. 0. 0. 0. 0. 0.]
   symmetry error: 4.1359030627651384e-24
   matrix shapes: (3, 2) (3, 2) (3, 2)
   BZ via matrix: [4.487214325e-04 3.466000653e-04 7.971540153e-07]
   BZ via kernel: [4.487214325e-04 3.466000653e-04 7.971540153e-07]

``G`` is ``9x9``: target rows and source columns, with the node-to-itself entries set to zero by the discrete zero-self convention. Its symmetry error is ``4.1e-24``; this same-node matrix differs from the mutual-inductance matrix of coaxial loops only by a ``2*pi`` factor (what is stored here is flux per radian); but **a zero diagonal is not physical self-inductance**. This model does not provide the self-inductance of a finite-cross-section conductor, and using the zero diagonal in an inductance calculation will give a wrong result.

``green_response_matrices`` returns a triple; ``dense_axisymmetric_green_response`` and ``circular_filament_green_response`` return ``scirel._result.Result`` mappings. A ``Result`` still supports dictionary-style key lookup and also exposes fields as attributes. The two interface families have different return types, so read the code carefully. The matrix contraction is written ``gbz @ currents`` and agrees with the per-filament kernel sum.

The matrix can also be used for a boundary correction. The example below has only 3 field points and 2 boundary samples; it is a linear-algebra demonstration, not a conducting-wall model:

.. code-block:: python

   import numpy as np
   from scirel.field import correct_ideal_conductor_boundary_flux

   psi = np.array([3.0, -1.0, 2.0])          # uncorrected flux at 3 field points
   S = np.array([[1.0, 0.0, 0.0], [0.0, 0.5, 0.5]])  # 2 boundary samples
   Gbb = np.diag([2.0, 4.0])                 # boundary -> boundary
   Gbf = np.array([[2.0, 0.0], [-1.0, 3.0], [1.0, 5.0]])  # boundary -> field points

   out = correct_ideal_conductor_boundary_flux(psi, S, Gbb, Gbf)
   print("corrected flux:", out["corrected_field_flux"])
   print("boundary currents:", out["boundary_currents"])
   print("singular values:", out["singular_values"])
   print("effective rank:", out["effective_rank"])
   print("residual:", out["residual"], "norm:", out["residual_norm"])

Actual output:

.. code-block:: text

   corrected flux: [ 0.     0.125 -0.125]
   boundary currents: [-1.5   -0.125]
   singular values: [4. 2.]
   effective rank: 2
   residual: [0. 0.] norm: 0.0

The call first samples the boundary flux ``S @ psi``, solves ``Gbb @ I = -S @ psi`` (with relative singular-value truncation ``rcond=1e-10``), and then adds ``Gbf @ I`` back to the field points. Here ``S @ Gbf`` happens to equal ``Gbb``, so after the correction the boundary samples are zero, the residual is zero and the effective rank is 2.

Real systems are not necessarily this tidy: a truncated SVD may leave a nonzero residual, and the function returns the residual together with the effective rank instead of claiming that "an ideal conductor always cancels the flux completely". What this section cannot establish: zero residual is a construction property of this small system, not evidence of physical correctness; the shapes and values of ``S``, ``Gbb`` and ``Gbf`` still have to come from the concrete problem.

Two kinds of ``psi`` cannot be subtracted directly
----------------------------------------------------------------------

Here is another easy trap: although both are called ``psi``, the direct Green response and the radial integration use different reference points. Below we compute both on a grid of 121 radial points and 7 axial points:

.. code-block:: python

   import numpy as np
   from scirel.field import circular_filament_green_response, integrate_filament_vacuum_field

   filaments = [[0.355, 0.25, 250.0], [0.355, -0.25, 250.0]]
   r_grid, z_grid = np.meshgrid(
       np.linspace(0.05, 0.6, 121), np.linspace(-0.3, 0.3, 7)
   )
   integ = integrate_filament_vacuum_field(r_grid, z_grid, filaments)
   direct = circular_filament_green_response(
       filaments, np.column_stack((r_grid.ravel(), z_grid.ravel()))
   )
   psi_direct = direct["gpsi"].reshape(r_grid.shape)

   diff = integ["psi"] - psi_direct
   print("max variation within a row:", np.abs(diff - diff[:, :1]).max())
   print("offset (first row):", diff[0, 0])
   print("offset (middle row):", diff[3, 0])
   print("max |BZ difference|:", np.abs(integ["b_z"] - direct["gBZ"].reshape(r_grid.shape)).max())

Actual output:

.. code-block:: text

   max variation within a row: 1.3331215369254684e-08
   offset (first row): -6.283337877550199e-07
   offset (middle row): -6.025826977395476e-07
   max |BZ difference|: 0.0

``integrate_filament_vacuum_field`` evaluates ``B_R`` and ``B_Z`` with the same Green kernel, then performs a cumulative trapezoidal integration of ``R*B_Z`` and takes the first radial node as ``psi=0``. The ``psi`` of the direct Green response instead uses the cylindrical axis as its zero. The difference between them is a constant along each row, equal to ``-psi_direct(R0)``; on this grid the within-row variation is only ``1.3e-8``, and the remaining difference is quadrature error.

The maximum difference in ``B_Z`` is 0 because both use the same kernel; if you look only at ``B_Z``, you would think the two results agree completely, and then subtracting the two ``psi`` values directly gives an offset that varies with ``Z``. The correct procedure is first to subtract each one's own reference value, or to state from the start where the zero of "this ``psi``" lies.

Neither ``psi`` contains a ``2*pi``. The flux through a full toroidal circuit is ``2*pi*psi``; treating Wb/rad as Wb is off by a ``2*pi``. What this section cannot establish: the radial integration is a numerical quadrature, not a new physical model; its accuracy depends on the radial grid, and the first node is only a reference point, not a physical boundary condition.

Which function to use
----------------------------------------------------------------------

- You want the response of a single loop or a small set of weighted filaments at points: :doc:`../reference/generated/scirel.field.circular-filament-green`.
- You want the triple response from ``compute_greens`` directly (it raises when a target exactly coincides with a positive-radius source): :doc:`../reference/generated/scirel.electromagnetism.circular-filament-green`.
- You already have filament positions and currents and want to contract source columns into a matrix: :doc:`../reference/generated/scirel.field.current-green-superposition`; when you need an explicit matrix, use :doc:`../reference/generated/scirel.field.dense-axisymmetric-green`.
- You only want to turn a rectangular cross-section into ordered points: :doc:`../reference/generated/scirel.field.rectangular-coil-filaments`; when you need a source object carrying current and grid, use :doc:`../reference/generated/scirel.electromagnetism.rectangular-coil`.
- You want to pass a set of rectangular coil records and obtain the grid field in one call: :doc:`../reference/generated/scirel.field.multi-coil-vacuum-field`.
- You want to register several named sub-sources, share a grid and override the current as a whole: :doc:`../reference/generated/scirel.electromagnetism.device`; for arbitrary point sources use :doc:`../reference/generated/scirel.electromagnetism.arbitrary-points`.
- You want to recover the poloidal field and its magnitude from a ``psi`` grid: :doc:`../reference/generated/scirel.field.poloidal-field-from-flux`, :doc:`../reference/generated/scirel.field.poloidal-field-magnitude`.
- You want a same-node flux matrix or a target-source response matrix: :doc:`../reference/generated/scirel.electromagnetism.loop-flux-matrix`, :doc:`../reference/generated/scirel.electromagnetism.green-response-matrices`.
- You want a boundary correction based on a truncated SVD: :doc:`../reference/generated/scirel.field.ideal-conductor-boundary`.
- You want to build a plasma flux response matrix on a mirror-symmetric Z grid: :doc:`../reference/generated/scirel.field.mirror-plasma-green`.
- You want the elliptic-integral branch and to inspect the modulus, ``K``, ``E`` and closed forms yourself: :doc:`../reference/generated/scirel.field.coil-green-geometry`, :doc:`../reference/generated/scirel.field.complete-elliptic-integrals-approx`, :doc:`../reference/generated/scirel.field.filament-coil-green-field`.
- You want a ``psi`` whose zero is the first radial node, obtained by radial integration: :doc:`../reference/generated/scirel.field.filament-vacuum-field`.
- You want a magnet ring or device with a fixed geometry: :doc:`../reference/generated/scirel.electromagnetism.magnet-ring`, :doc:`../reference/generated/scirel.field.permanent-ring-filaments`, :doc:`../reference/generated/scirel.electromagnetism.trex-coil`, :doc:`../reference/generated/scirel.electromagnetism.brb`, :doc:`../reference/generated/scirel.electromagnetism.wham`. These are geometry and filament arrangements, not material magnetization or experimental calibration.

Common misuses and boundaries
----------------------------------------------------------------------

- **Units**: ``R,Z`` are in metres. If you pass centimetres as metres, the field and flux will be off by orders of magnitude, and nothing will raise.
- **Total current versus per-filament current**: ``current`` is the current of each filament (or each sub-source); ``weights`` are dimensionless weights. Decide first how the total current is divided, then pass the currents. Passing the total current to every filament multiplies the total current.
- **Axis order**: ``dense_axisymmetric_green_response`` and ``green_response_matrices`` are both ``(target, source)``; ``superpose_current_green_field`` contracts the second axis (source columns) with the current vector and preserves target rows. Do not transpose the response matrix.
- **Zero diagonal**: the zero self terms of ``get_gpsi`` and the aggregate entry are discrete conventions, not the self-inductance of a finite conductor. Do not use them to compute inductance or near-filament fields.
- **Coincident points**: ``compute_greens`` raises ``ValueError`` when a target exactly coincides with a positive-radius source; ``circular_filament_green_response`` skips such a point as a zero-self term. These are not the same failure convention.
- **Flux zero point**: the direct Green ``psi`` and the radially integrated ``psi`` use different reference points; align the zeros before comparing.
- **``B0_default``**: it is the median of the magnitude array, not an automatic normalization; the ``1e-30`` floor is a numerical contract, not a physical field.
- **Boundary correction**: ``correct_ideal_conductor_boundary_flux`` is a linear-algebra correction based on a truncated SVD; zero residual does not mean a real conducting wall is correct.
- **Fixed geometry**: ``MagnetRing`` is a signed filament approximation, not a magnetization model; ``TREXCoil``, ``BRB`` and ``WHAM`` preserve geometry constants and provide no experimental device calibration.

The model boundary of this chapter is: vacuum, axisymmetry, ideal circular current filaments and linear superposition. It does not include finite filament radius, conductor interior, magnetic cores, plasma response, three-dimensional geometry, coil boxes, forces or energy. When you need those, return to the concrete function page to confirm the model instead of extrapolating the numbers here.

.. seealso::

   If the next question is how flux connects to plasma equilibrium or diagnostic quantities, return to :doc:`/user-guide/index` and choose a domain first; each function page gives the complete signature, failure behavior and verification boundary.
