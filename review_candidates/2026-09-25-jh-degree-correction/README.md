# Candidate: r58 successor — Johnson-Hinnov degree-convention correction (three assets, description only)

Status: development candidate prepared for expert review, frozen as the
pending_unapproved r58 successor of r57. Nothing here is expert approval, a
trusted version, or a public release. This batch is a **description
correction with no arithmetic change**: every numerical output of the three
Johnson-Hinnov assets is bit-identical to r57.

## Base and comparison scope

- SciRel base: `f98bf5b` (r57, Johnson-Hinnov coefficient B-spline family,
  93→96 assets dev29, `pending_unapproved`).
- Trigger: an independent read-only review (Codex) established that the r57
  descriptions call the executed surface "cubic" (三次 / "source cubic
  order 4"), while the implementation passes the value 4 to scipy's FITPACK
  `bisplev` as `kx=ky`, and scipy documents `kx`/`ky` as the spline
  **degree** — so the executed surface is degree four (quartic).

## Verification of the finding (independent, this round)

1. **Library documentation.** The installed scipy's `RectBivariateSpline`
   documentation states "kx, ky : Degrees of the bivariate spline. Default
   is 3", and `bisplev`'s `tck` is documented as containing "the degree of
   the spline".
2. **Coefficient-count arithmetic.** The saved payload geometry
   (`TKnot`=16, `DKnot`=12, `order`=4) has 77 coefficients. FITPACK's
   coefficient count is `(len(knots) - degree - 1)` per axis: the degree
   reading gives `(16-5)*(12-5) = 77` (exact); an order-reading
   (degree = 4-1 = 3) would give `12*8 = 96` (false). The saved validation
   contract itself is therefore only consistent with 4 meaning degree.
3. **Numerical witness.** An independent numpy-only Cox-de Boor
   tensor-product evaluation at degree 4 (no scipy) reproduces
   `bisplev(kx=ky=4)` to <= 7e-15, including both knot endpoints.

The saved source's own label ("cubic") is an intended-order statement that
does not change the executed degree; the discrepancy originates in the
saved package's description and was carried verbatim into r57's wording.

## What changed and what did not

Changed (description only): the three module docstrings, the three exact
documents (summary/relation/definition/model/boundary/assumptions plus a
new degree-witness scope bullet and a label-discrepancy known-limitation),
the three direct test files' docstrings, and three new degree-witness tests
(`test_the_executed_surface_is_degree_four_under_fitpacks_degree_convention`
in each direct file, pinning the executed surface against the independent
Cox-de Boor evaluation). Not changed: any executable arithmetic, any
validation contract, any error message, any test numerical assertion, the
r/alpha density-overwrite behavior, and the r57-scoped evidence documents
(`review-version-2026-09-25-r57.md`, `intake-2026-09-25-jh-coefficients.md`,
`build/test-evidence-r57.md`, the r57 candidate trio and its index entries),
whose original bytes remain the r57 snapshot's record; the r57 wording
defect is superseded by this successor, not silently rewritten.

Disposition: **description correction (rework of review materials and
public contract text), not a scientific change**. The three identities,
their signatures, and the no-repair preservation stance are unchanged; the
label-vs-degree question is added to the open expert-review questions.

## Files

- `proposal/hydrogen_jh_r_coefficient.py`, `hydrogen_jh_s_coefficient.py`,
  `hydrogen_jh_alpha_coefficient.py` and their two test files each
- three `proposal/scirel.collisions.hydrogen-jh-*.json` exact documents

The proposal copies are byte-identical to the integrated files under `src/`,
`tests/` and `catalog/examples/` in the r58 freeze commit (dev30). Version
moves `0.1.0.dev29` -> `0.1.0.dev30` because committed wheel-bearing bytes
(docstrings) changed; the other 93 exact documents change only in their
mechanical `implementation_version` bump.
