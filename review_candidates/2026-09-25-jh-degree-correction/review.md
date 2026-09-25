# Candidate document: r58 successor — Johnson-Hinnov degree-convention correction

Status: development candidate prepared for expert review. Nothing here is
expert approval, a trusted version, or a public release. The development
integration lives on branch `codex/kn1dpy-maxwellian-rate-intake` on top of
SciRel base `f98bf5b` (r57).

## Incoming correction

An independent read-only review found that the r57 scientific descriptions
of the three Johnson-Hinnov assets (`scirel.collisions.hydrogen-jh-r-`,
`-s-`, `-alpha-coefficient`) mis-describe the executed surface as "cubic"
(三次, "source cubic order 4"). The implementation passes the value 4 to
scipy's FITPACK `bisplev` as `kx=ky`, and scipy documents `kx`/`ky` as the
spline **degree**; the executed surface is therefore degree four (quartic).

## Evidence for the correction (three independent lines)

1. scipy's own documentation: `RectBivariateSpline` — "kx, ky : Degrees of
   the bivariate spline. Default is 3"; `bisplev`'s `tck` — "the degree of
   the spline".
2. The saved coefficient-count arithmetic: for the packaged payload
   geometry (`TKnot`=16, `DKnot`=12, `order`=4, 77 coefficients), the
   degree reading `(16-5)*(12-5)=77` closes exactly while the
   order-as-degree-plus-one reading `(16-4)*(12-4)=96` does not. The saved
   validation contract itself only makes sense with 4 meaning degree.
3. A numerical witness: an independent numpy Cox-de Boor tensor-product
   evaluation at degree 4 reproduces `bisplev(kx=ky=4)` to <= 7e-15 at
   interior points and both knot endpoints.

## Disposition

**Description correction; no arithmetic change.** Every numerical output of
the three assets is bit-identical to r57; the r57 two-arm replays remain
valid (their compared bytes are unchanged). Corrections:

- Module docstrings and exact documents now state the degree convention
  explicitly: the saved `order`/`spline_order` value 4 is consumed by
  FITPACK as the spline degree, so the executed surface is degree four
  (quartic); the saved source's "cubic" label is an intended-order
  statement that does not change the executed degree.
- Three new degree-witness tests
  (`test_the_executed_surface_is_degree_four_under_fitpacks_degree_convention`,
  one per direct test file) pin the executed surface against the
  independent Cox-de Boor evaluation, including the clipped null-sentinel
  density coordinate at the right knot endpoint for the r and alpha
  branches.
- The label-vs-executed-degree discrepancy is recorded as a new
  known-limitation and open expert-review question in all three exact
  documents and below.

Not changed: executable arithmetic, validation contracts, error messages,
signatures, the r/alpha density-overwrite behavior, the s
density-consuming behavior, and the r57-scoped evidence documents (their
original bytes remain the r57 snapshot's record; this successor supersedes
the wording rather than silently rewriting it).

## Public API and dependency impact

No signature, export, or dependency change. Three exact documents change
their description fields and gain one scope bullet and one known-limitation
each; the other 93 exact documents change only in the mechanical
`implementation_version` bump. Development version moves `0.1.0.dev29` ->
`0.1.0.dev30` with one new internal wheel (docstrings are wheel-bearing
bytes); catalog `complete: 96/96`.

## Decision requested from the expert

1. Whether the degree-convention wording (degree four under FITPACK's
   convention, saved label recorded as intended-order) is the accurate
   published description for the three assets.
2. Whether the intended relation is the executed degree-four surface
   (preserved here, bit for bit) or whether a successor should repair the
   relations to a genuine degree-three surface — which would change
   outputs, invalidate the r57 replay comparisons, and require new
   evidence.
3. Whether the r/alpha no_null=1 density-overwrite question and the other
   open questions carried over from r57 remain as recorded.
