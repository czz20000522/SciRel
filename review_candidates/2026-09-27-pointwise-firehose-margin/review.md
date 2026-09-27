# Candidate: pointwise firehose-margin relation (one operator)

Status: development candidate prepared for expert review, to be frozen as the
pending_unapproved r73 successor of r72. Nothing here is expert approval, a
trusted version, or a public release.

## Base and comparison scope

- SciRel base: `c1f7fcd` (r72-v3 frozen, 147 assets dev47, snapshot
  `build/verification/review-2026-09-27-r72-cross-node-leaves-v3`). r73
  increments the catalog to 148 exact documents, version
  `0.1.0.dev47` -> `0.1.0.dev48`.
- Unpublished candidate pool: re-checked by relation — none exists; no
  pending batch under `review_candidates/` contains a firehose, mirror or
  anisotropic-pressure margin relation (the firehose hits in the 2026-09-24
  pool snapshot are the already-migrated Pleiades development samples).
- Incoming source: none. This batch consumes no L1, no saved bundle and no
  qualified delivery root (re-checked empty at batch start). The relation is
  an independent SciRel-maintained decomposition of an already-maintained
  SciRel relation, motivated by outbound evaluation evidence.

## Origin: independent evaluation of the 2026-09-27 outbound holdouts

Two fresh uncoached outbound runs (development records in the sibling main
SciRel checkout, `docs/evaluations/outbound-progressive-projects/
results-2026-09-27-state-json.md` and `results-2026-09-27-flat-b.md`, with
digest-bound manifests and raw trace/archive evidence) each showed the same
selection failure: an autonomous solver facing one-sample or all-equal-B
pressure states still invoked the combined SciRel diagnostic
`scirel.diagnostics.firehose-mirror-margins` per state — 3 invocations with
`run_evidence.json` itself recording `mirror_branch_applicable=false` (flat-b),
and 2 invocations whose CSV carried positive degenerate mirror margins
`B^2/mu0 > 0` with `mirror_sample_flag=True` softened only by a
`mirror_criterion_evaluated=False` column (state-json). The solver's final
prose withheld the stability verdict both times; the program layer did not.

## Scientific-semantics assessment (independent, against current bytes)

- The combined diagnostic's exact document and implementation are mutually
  consistent and internally honest: the one-sample/all-equal-B zero-derivative
  convention is documented (`_derivative_with_respect_to_field` sets the
  derivative to zero for a nondegenerate-range failure), the mirror branch is
  set-dependent by construction, and the assumptions section already puts
  criterion selection on the caller. The asset itself is not wrong.
- The mirror margin `B^2/mu0 - B*d(p_perp)/dB` presupposes p_perp sampled
  along a genuine B-value scan coordinate. On a one-sample state the
  convention degenerates the value to `B^2/mu0` — numerically finite,
  physically meaningless as a mirror criterion — and the aggregate
  `mirror_stable` flag then reports strict positivity of that degenerate
  value. That shape (a positive number plus a True flag with the true premise
  visible only as a caveat) is what the two holdout runs surfaced.
- The failure mode is therefore a relation-shape problem, not a wording
  problem: a caller needing only the pointwise quantity must invoke an asset
  that simultaneously computes a set-dependent branch and aggregate flags.
  Multiple narrowed skill revisions did not remove it (flat-b failed after
  the final method revision). The evidence ceiling of the existing document
  is correct but does not change the callable's shape.
- Conclusion: a separate relation exposing ONLY the pointwise algebraic
  margin is scientifically justified as the contract-level remedy. The
  alternative remedies were considered and rejected: (a) removing the
  one-sample zero-derivative convention from the combined asset would break
  its documented contract and prior numeric tests without fixing the
  selection problem; (b) an applicability flag in the combined asset's
  return would still return degenerate numbers and was exactly what the
  state-json run demonstrated as insufficient.

## Proposed identity

- `scirel.diagnostics.pointwise-firehose-margin`
  (`compute_pointwise_firehose_margin`) — pointwise
  `firehose_margin = B^2/mu0 + p_perp - p_parallel` in Pa, elementwise, with
  no derivative, no mirror branch, no minimum reduction and no stable flag.
  A single sample and all-equal B are ordinary in-domain inputs.

## Deduplication judgment

- Versus `scirel.diagnostics.firehose-mirror-margins`: that asset bundles the
  pointwise firehose field WITH the set-dependent mirror branch, sampled
  minima and two aggregate stable flags — a different relation with a
  different direction and output signature. The new asset is the pointwise
  sub-relation with the cross-sample and flag machinery deliberately absent;
  its direct tests pin bit-identical equality of the shared field so no
  numeric contract forks. No consolidation.
- Versus `scirel.equilibrium.anisotropic-force-balance`: its
  `firehose_margin` is the dimensionless `1 - mu0*(p_parallel - p_perp)/B^2`
  with B floored at `tiny` — a different quantity in different units (the
  domain draft already records that these two are not the same port). No
  overlap.
- Versus `scirel.diagnostics.parallel-pressure-residual` and the mirror
  kinetic family: different relations (B-value derivative residuals; mirror
  total pressure); no overlap.

## Contract decisions and registered divergences (vs. nothing — new identity)

1. **Output contains exactly one field** `firehose_margin`; the test suite
   asserts the absence of `mirror_margin`, `mirror_stable`, `firehose_stable`,
   `min_firehose_margin` and `min_mirror_margin` as a contract, not an
   implementation accident.
2. **No stability semantics**: positive values are returned unchanged; a test
   pins faithful negative-margin return; the document states that positivity
   is never labeled or interpreted.
3. **One-sample and all-equal-B are in-domain**: explicit tests, mirroring
   the holdout inputs (810/740 kPa at 0.93 T; 650/820/990 kPa at 1 T).
4. **Registered fail-closed gates** (consistent with the r71/r72 hardening
   line): empty sample sets rejected (the combined asset fails only later at
   its minimum reduction); nonfinite margin (B^2/mu0 float64 overflow)
   rejected with `errstate` suppression of the intermediate warning; and,
   from review, **non-scalar mu0 rejected before arithmetic** — a 1-element
   array mu0 would silently broadcast the output shape to (1,).
5. **Same numeric identity as the combined asset's firehose field**: exact
   array equality test over randomized finite inputs, so the pointwise
   relation cannot drift from the established contract.

## Evidence

- 10 direct tests: elementwise closed form on unsorted arrays; one-sample and
  all-equal-B validity; bit-identical equality with the combined diagnostic's
  firehose field; output-key contract (no mirror, no flags); faithful
  negative margin; shape/empty/nonfinite/mu0 rejections; non-scalar mu0
  rejection (list, tuple, 1-D and 2-D arrays); overflow gate; 0-d scalar
  shape/dtype; mu0 override arithmetic.
- No saved-source replay applies: this batch consumes no external source, so
  the source-mapping digest table of previous batches is replaced by an
  explicit "no incoming source" statement.
- Composition: the new asset has no TaskGraph consumers (verified against the
  r72 catalog reverse-dependency index); the composition evidence is the
  cross-asset equality test plus the public-surface import test.

## Files

- `proposal/pointwise_firehose_margin.py`
- `proposal/test_pointwise_firehose_margin.py`
- `proposal/scirel.diagnostics.pointwise-firehose-margin.json`

## Version and impact

Version `0.1.0.dev47` -> `0.1.0.dev48`; catalog 147 -> 148 exact documents.
The other 147 documents change only in the mechanical
`implementation_version` bump. No existing asset's scientific contract
changes; the combined diagnostic's bytes, document semantics and tests are
untouched.
