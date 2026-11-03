Numerical geometry and field sampling: from an R-Z grid to a flux surface
=========================================================================

This chapter answers one concrete question: **given an axisymmetric field sampled at the nodes of an ``R-Z`` grid, how do you evaluate it at arbitrary points, accumulate arc length and ``dl/B`` along a flux surface, and then map the result onto a Cartesian solver grid?**

After reading it you should be able to judge three things: when node values can be interpolated to points, when a contour that "looks closed" is in fact not closed, and which points are merely clamped to the boundary after mapping the field to the solver grid and therefore cannot be treated as known physics. The whole chapter follows one continuous path: grid queries → contours and field lines → path integrals → Cartesian mapping.

.. note::

   This chapter is a tutorial, not a contract summary. Full signatures, failure behavior and applicability for every entry point are on the API reference pages linked at the end of the chapter. The code accumulates in order; if you copy a single section, keep the model definitions that precede it.

Model: an analytic field with circular flux surfaces
----------------------------------------------------

To keep geometry questions separate from equilibrium solves, this chapter uses a hand-constructed axisymmetric field. Take ``B0 = 2 T``, ``R0 = 1.5 m`` and ``r_s = 0.4 m``, and define

.. code-block:: text

   psi(R,Z) = B0/(2*R0) * ((R-R0)^2 + Z^2)
   B_R(R,Z) = -B0*Z/(R*R0)
   B_Z(R,Z) =  B0*(R-R0)/(R*R0)
   |B|(R,Z) =  B0/(R*R0) * sqrt((R-R0)^2 + Z^2)

``psi`` has units of ``Wb/rad``, the magnetic field is in ``T`` and lengths are in ``m``. Lines of constant ``psi`` are circles centered at ``(R0, 0)`` with radius ``r``; on the flux surface ``r = r_s``, ``|B| = B0*r_s/(R*R0)``.

This field is a **manufactured field**: it makes the flux surfaces exactly circular, which makes it easy to check every step against analytic values; it is not a solution of the Grad–Shafranov equation and does not correspond to a real device.

Two coordinate conventions need to be remembered up front:

- ``sample_rectilinear_field`` indexes grid arrays as ``[Z, R]``, while query points are ordered as ``[R, Z]``;
- ``map_axisymmetric_equilibrium_to_cartesian_grid`` stores equilibrium field arrays as ``[R, Z]`` and returns a three-dimensional vector on an ``(x, y, z)`` grid.

Querying on the grid: exact at nodes, inexact inside cells
----------------------------------------------------------

First build a regular grid with ``R in [0.9, 2.1] m`` and ``Z in [-0.8, 0.9] m``, place the analytic ``psi`` on its nodes, and query it with the bilinear sampler. To see the interpolation error, sample at nodes, at cell centers, and at three resolutions.

.. code-block:: python

   import numpy as np
   from scirel.geometry import sample_rectilinear_field

   B0, R0, rs = 2.0, 1.5, 0.4

   def psi_analytic(R, Z):
       return B0/(2*R0)*((R-R0)**2 + Z**2)

   def grid(nr, nz):
       r = np.linspace(0.9, 2.1, nr)
       z = np.linspace(-0.8, 0.9, nz)
       return np.meshgrid(r, z)

   def bilinear_error(nr, nz):
       R, Z = grid(nr, nz)
       psi = psi_analytic(R, Z)
       rc = 0.5*(R[0, :-1] + R[0, 1:])
       zc = 0.5*(Z[:-1, 0] + Z[1:, 0])
       RC, ZC = np.meshgrid(rc, zc)
       points = np.column_stack([RC.ravel(), ZC.ravel()])
       sampled = sample_rectilinear_field(R, Z, psi, points)['samples']
       return np.max(np.abs(sampled - psi_analytic(RC, ZC).ravel()))

   for nr, nz in ((17, 11), (33, 22), (65, 43)):
       print(f"nr={nr:3d} nz={nz:3d}  max error = {bilinear_error(nr, nz):.3e}")

   R, Z = grid(49, 34)
   psi = psi_analytic(R, Z)
   nodes = np.array([[R[10, 20], Z[10, 20]], [R[28, 4], Z[28, 4]]])
   print("node samples =", sample_rectilinear_field(R, Z, psi, nodes)['samples'])
   print("node analytic =", psi_analytic(nodes[:, 0], nodes[:, 1]))

   mid = np.array([[(R[10, 20] + R[10, 21])/2, (Z[10, 20] + Z[11, 20])/2]])
   sample = sample_rectilinear_field(R, Z, psi, mid)['samples'][0]
   exact = psi_analytic(mid[:, 0], mid[:, 1])[0]
   print("midpoint sample =", round(sample, 8))
   print("midpoint analytic =", round(exact, 8))
   print("midpoint error =", sample - exact)

   try:
       sample_rectilinear_field(R, Z, psi, [[2.2, 0.0]])
   except ValueError as exc:
       print("outside ->", exc)

Actual output:

.. code-block:: text

   nr= 17 nz= 11  max error = 5.754e-03
   nr= 33 nz= 22  max error = 1.327e-03
   nr= 65 nz= 43  max error = 3.316e-04
   node samples = [0.06075911 0.44180594]
   node analytic = [0.06075911 0.44180594]
   midpoint sample = 0.0504027
   midpoint analytic = 0.04985623
   midpoint error = 0.0005464684726048316
   outside -> diagnostic point lies outside the R-Z grid

Samples at nodes agree bit-for-bit with the analytic values, because bilinear interpolation at a corner is the node value itself; at cell centers an error of ``5.46e-4`` appears. Doubling the grid reduces the maximum error to roughly a quarter (``5.75e-3 → 1.33e-3 → 3.32e-4``), the empirical signature of second-order convergence coming from the quadratic variation of ``psi`` inside a cell.

The query at ``R = 2.2 m`` lies outside the closed grid, so the entry point rejects it outright without clamping or extrapolating. This differs from the Cartesian mapping in the next section: the sampler chooses "reject", while the mapping chooses "clamp and report".

**What this section does not establish**: second-order convergence is only an observation for this quadratic field on this sequence of grids, not an error bound for arbitrary fields; exact node values do not mean that the space between nodes is known; the ``Z`` grid deliberately uses 34 points and avoids ``(R0, 0)``, because ``|B| = 0`` there and the downstream inverse-field integral rejects nonpositive field strengths.

From contours to closed field lines: selection, closure and arc length
----------------------------------------------------------------------

With the ``psi`` grid in hand, the next step is to take a contour. In a real workflow the ``contourset`` usually comes from a contour extractor; here we construct a minimal object containing only ``levels`` and ``allsegs`` directly from the analytic circle, so that attention stays on SciRel's selection, orientation and arc-length computation.

.. code-block:: python

   from types import SimpleNamespace
   from scirel.geometry import get_fieldlines, FieldLine, get_fieldline_distance

   psi_s = B0*rs**2/(2*R0)
   theta = np.linspace(0.0, 2*np.pi, 64, endpoint=False)
   circle = np.column_stack([R0 + rs*np.cos(theta), rs*np.sin(theta)])
   circle = np.vstack([circle, circle[:1]])

   contours = SimpleNamespace(levels=[psi_s], allsegs=[[circle]])
   selected = get_fieldlines(contours, psi_s, clockwise=False)
   line = FieldLine(psi_s, selected)

   print("psi_s =", psi_s)
   print("vertices =", selected.shape[0],
         " closed =", bool(np.all(selected[0] == selected[-1])))
   print("polyline length =", get_fieldline_distance(selected)[-1])
   print("spline length   =", line.get_length())
   print("exact 2*pi*rs   =", 2*np.pi*rs)
   print("spline error    =", line.get_length() - 2*np.pi*rs)

   q = (line.verts[:, 0] - R0)/rs
   dq = line.d_ds(q)
   print("dq/ds range =", dq.min(), dq.max(), " 1/rs =", 1/rs)

Actual output:

.. code-block:: text

   psi_s = 0.10666666666666669
   vertices = 65  closed = True
   polyline length = 2.512264925563802
   spline length   = 2.513269177501545
   exact 2*pi*rs   = 2.5132741228718345
   spline error    = -4.945370289277662e-06
   dq/ds range = -2.4999845232953835 2.4999845232953284  1/rs = 2.5

``get_fieldlines`` requires the requested contour level to appear exactly in ``contours.levels``; it then takes the segment with the most vertices and orients it according to ``clockwise``. We constructed a counter-clockwise circle, so we pass ``clockwise=False``; with the default ``clockwise=True``, the orientation implementation would reverse the path, the reversed last point would no longer equal the first, and ``closed`` would become false.

Closure itself has traps. With ``np.linspace(0, 2*pi, 64)`` the ``Z`` coordinate of the last point is ``-9.8e-17`` rather than ``0``, the first and last coordinates are not bit-for-bit equal, ``is_closed()`` returns false, and the downstream spline parameterization no longer treats the path as periodic. Here we first generate 64 distinct points with ``endpoint=False`` and then explicitly copy the first point to the end, which is what gives a genuinely closed polyline.

The polyline length ``2.5122649 m`` is slightly smaller than the analytic circumference ``2.5132741 m``; this is the discretization error of replacing the arc with 64 chords. After spline reparameterization the length ``2.5132692 m`` is closer to the analytic value, with a residual of about ``-4.95e-6 m``. ``q = (R-R0)/r_s`` equals ``cos(theta)`` on the circle, so its derivative with respect to the polar angle ranges over ``[-1, 1]``; differentiating with respect to arc length requires dividing by ``r_s`` again, giving the range ``[-2.5, 2.5]``. The two differ by a geometric factor, so ``dq/dtheta`` must not be mistaken for ``dq/ds``.

**What this section does not establish**: contour extraction is not performed inside SciRel; ``closed=True`` only says that the first and last coordinates are equal, not that the line is a complete physical flux surface; a small spline-length error applies only to this smooth circle — sharp corners or open curves must be checked again.

Inverse-field measure and weighted average along a flux surface
---------------------------------------------------------------

Now perform two path reductions along this closed path: ``integral(dl/B)`` and the ``B``-weighted average of the scalar ``Q = 1/R``. The integrand comes from ``|B|`` on the grid, and the path points come from the previous section.

.. code-block:: python

   from scirel.geometry import compute_flux_surface_inverse_field_average

   r_axis = np.linspace(0.9, 2.1, 49)
   z_axis = np.linspace(-0.8, 0.9, 34)
   R, Z = np.meshgrid(r_axis, z_axis)
   B = B0/(R*R0)*np.hypot(R-R0, Z)
   Q = 1.0/R

   for n in (17, 33, 65, 129, 257):
       th = np.linspace(0.0, 2*np.pi, n, endpoint=False)
       path = np.column_stack([R0 + rs*np.cos(th), rs*np.sin(th)])
       path = np.vstack([path, path[:1]])
       res = compute_flux_surface_inverse_field_average(R, Z, B, path, Q)
       print(f"n={n:3d}  dl/B={res['dl_B']:.9f}  <1/R>={res['flux_surface_average']:.9f}")

   print("exact dl/B =", 2*np.pi*R0**2/B0)
   print("exact <1/R> =", 1/R0)

Actual output:

.. code-block:: text

   n= 17  dl/B=7.028420845  <1/R>=0.666666690
   n= 33  dl/B=7.057912219  <1/R>=0.666666663
   n= 65  dl/B=7.065832624  <1/R>=0.666666664
   n=129  dl/B=7.067885629  <1/R>=0.666666664
   n=257  dl/B=7.068408285  <1/R>=0.666666664
   exact dl/B = 7.0685834705770345
   exact <1/R> = 0.6666666666666666

The analytic values can be computed directly. Along the path, ``dl = r_s dtheta`` and ``B = B0 r_s/(R R0)``, so

.. code-block:: text

   integral(dl/B) = integral((R*R0)/(B0*r_s) * r_s dtheta)
                  = (R0/B0) * integral(R dtheta) = 2*pi*R0^2/B0

For ``Q = 1/R``, the numerator is ``integral((R0/(B0*r_s)) * r_s dtheta) = 2*pi*R0/B0``, and dividing by ``integral(dl/B)`` gives exactly ``1/R0``. In the table, ``dl/B`` approaches ``7.068583471`` monotonically as the path points are refined, with the error dropping from ``4.02e-2`` to ``1.75e-4``; ``<1/R>`` is already very close to ``2/3`` on a rather coarse path, because the weight of ``Q`` and the ``1/R`` dependence of ``B`` largely cancel in this special geometry.

This is not a coincidence and it does not generalize: it relies on ``B ∝ 1/R`` and a circular path. Internally the function interpolates ``B`` and ``Q`` at the path points with ``RectBivariateSpline`` and then integrates along the polyline arc length with the trapezoidal rule; the error therefore comes from both the spline interpolation of ``B`` and the polyline approximation of the path.

**What this section does not establish**: a small ``dl/B`` only says that the discrete integral converges; it does not prove that this path is a complete flux surface, nor does it provide a flux-surface volume normalization. ``B`` must be strictly positive both on the grid and at the interpolated path points, and zeros near the magnetic axis are rejected; the path must lie entirely inside the grid, and adjacent points must not coincide.

Mapping an axisymmetric equilibrium to a Cartesian solver grid
--------------------------------------------------------------

The final step moves the same ``(R, Z)`` field onto the ``(x, y, z)`` grid of a three-dimensional solver. ``map_axisymmetric_equilibrium_to_cartesian_grid`` requires equilibrium field arrays stored as ``[R, Z]``, with strictly increasing one-dimensional input axes.

.. code-block:: python

   from scirel.geometry import map_axisymmetric_equilibrium_to_cartesian_grid

   equilibrium = {
       'r_m': r_axis, 'z_m': z_axis,
       'psi_wb_per_rad': psi_analytic(R, Z).T,
       'br_t': (-B0*Z/(R*R0)).T,
       'bz_t': (B0*(R-R0)/(R*R0)).T,
   }
   x = np.linspace(-2.0, 2.0, 21)
   y = x.copy()
   z = np.linspace(-0.8, 0.9, 9)
   mapped = map_axisymmetric_equilibrium_to_cartesian_grid(equilibrium, x, y, z)

   covered = mapped['covered_mask']
   print("grid points =", covered.size, "covered =", covered.sum(),
         "fraction =", round(covered.mean(), 4))
   print("radially clamped =", mapped['radially_clamped_point_count'])
   print("axially clamped =", mapped['axially_clamped_point_count'])

   xx, yy = np.meshgrid(x, y, indexing='ij')
   print("planar points with R <", r_axis[0], "=",
         np.count_nonzero(np.hypot(xx, yy) < r_axis[0]))

   Bvec = mapped['magnetic_flux_density_t']
   i = np.argmin(np.abs(x - 1.4)); j = np.argmin(np.abs(y)); k = np.argmin(np.abs(z - 0.05))
   print("B(1.4,0,0.05) =", np.round(Bvec[i, j, k], 6),
         "|B| =", round(float(np.linalg.norm(Bvec[i, j, k])), 6))
   i0 = j0 = np.argmin(np.abs(x))
   print("B(0,0,0.05) =", np.round(Bvec[i0, j0, k], 6))

Actual output:

.. code-block:: text

   grid points = 3969 covered = 2520 fraction = 0.6349
   radially clamped = 828
   axially clamped = 0
   planar points with R < 0.9 = 69
   B(1.4,0,0.05) = [-0.047619 -0.       -0.095238] |B| = 0.106479
   B(0,0,0.05) = [ 0.        0.       -0.888889]

Of the ``3969`` Cartesian points, ``2520`` fall inside the original ``R-Z`` map box, a fraction of ``63.49%``. ``828`` points have ``R > 2.1 m`` and are clamped radially to the outer boundary; another ``69`` planar positions (times 9 axial layers, ``621`` grid points in total) have ``R < 0.9 m`` and are clamped to the inner boundary, but they are **not** included in ``radially_clamped_point_count`` — that counter only counts the side above the upper bound. To decide which points are genuinely covered, read ``covered_mask`` directly rather than adding the two counters.

At ``(1.4, 0, 0.05)`` the analytic formula gives ``B_R = -2*0.05/(1.4*1.5) = -0.047619`` and ``B_Z = 2*(1.4-1.5)/(1.4*1.5) = -0.095238``, matching the output, with ``|B| = 0.106479``. At ``(0, 0, 0.05)``, ``R = 0`` and the radial direction is undefined, so both radial components are set to zero; but here ``B_Z = -0.888889`` comes from the boundary value clamped to ``R = 0.9 m``, not from the physical field at the magnetic axis.

**What this section does not establish**: ``covered_mask`` being true only says that the point lies inside the map box, not that the field there has been validated; clamping turns outside points into boundary values and must not be used to extrapolate the real field; the mapping only moves geometry and does not include material classification, PML/PEC boundaries or an equilibrium solve. If the equilibrium field arrays keep the sampler's ``[Z, R]`` layout, they fail the shape check with ``must have shape (49, 34)`` and must be transposed first.

Which layer to use when
-----------------------

- Evaluate a two-dimensional real field at points inside a closed rectangular domain: :doc:`../reference/generated/scirel.geometry.bilinear-grid-sampling`.
- Sort, deduplicate and linearly interpolate a one-dimensional flux profile: :doc:`../reference/generated/scirel.geometry.flux-surface-profile`.
- Compute ``dl/B`` and a weighted average along an existing ``R-Z`` polyline: :doc:`../reference/generated/scirel.geometry.flux-surface-inverse-field-average`.
- Select, orient and truncate a segment from a contour level: :doc:`../reference/generated/scirel.sampling.select-fieldline` and :doc:`../reference/generated/scirel.sampling.parse-segment`.
- Accumulate polyline arc length: :doc:`../reference/generated/scirel.sampling.path-distance`.
- Reparameterize a field line with a spline and compute arc-length derivatives: :doc:`../reference/generated/scirel.fieldline.fieldline` and :doc:`../reference/generated/scirel.fieldline.arclength-derivative`.
- Map an axisymmetric equilibrium onto an ``(x, y, z)`` solver grid: :doc:`../reference/generated/scirel.geometry.axisymmetric-equilibrium-grid-mapping`.
- For three-dimensional complex-field interpolation masks, nearest-point/scattered sampling, material-support classification or polynomial/spline bases: see the coverage boundary at the end of this chapter.

Pitfalls and boundaries
-----------------------

- **Do not mix the three layouts.** The two-dimensional sampling grid ``quantity[Z, R]``, the sampling points ``[R, Z]`` and the equilibrium mapping field ``[R, Z]`` are three different conventions; a missing transpose produces either a shape error or silently swapped physical quantities.
- **Closure must be bit-for-bit.** When a circle is generated with trigonometric functions, ``sin`` at ``theta = 2*pi`` is not exactly zero; ``FieldLine.is_closed()`` checks that the first and last coordinates are exactly equal, not merely geometrically close.
- **Orientation changes closure.** The default ``clockwise=True`` may reverse the path you constructed; for a closed contour, confirm the construction direction first, or pass a ``clockwise`` value consistent with it explicitly.
- **The magnetic axis is the singularity of this manufactured field.** ``|B|`` is zero at ``(R0, 0)`` and the inverse-field integral requires a strictly positive field strength; a real device has a toroidal field, so this zero must not be treated as a general physical conclusion.
- **Clamping is not extrapolation.** The mapping entry point clamps out-of-box queries to the boundary and counts them, whereas the sampler rejects out-of-domain points outright; the two strategies are not interchangeable, and a clamped result must not be treated as the field outside the domain.
- **A counter is not coverage.** ``radially_clamped_point_count`` only counts the outer-boundary side; points clamped below the inner radius must be read from ``covered_mask``.
- **Splines have a support domain.** ``RectBivariateSpline`` requires at least four points per axis; ``FieldLine.interpolate_onto`` returns invalid values outside the support, while the inverse-field average entry point rejects out-of-range paths outright.

Three-dimensional complex-valued interpolation, nearest-point/scattered/rectangular-spline sampling, material-support classification, chord geometry, coordinate rotation, parametric splines and dense pseudoinverses are other paths in the same domain and are not covered in this chapter. Their units and failure modes are on the corresponding API reference pages; do not apply this chapter's two-dimensional bilinear interpolation, circular flux surfaces and positive-field assumptions to them directly.

.. seealso::

   To continue with "how predictions at observation points enter inversion", read :doc:`diagnostics-and-inference`; to return to the domain introduction, read :doc:`/user-guide/index`.
