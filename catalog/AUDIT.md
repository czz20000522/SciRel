# Capability audit and adversarial testing

This is the project-wide audit protocol for the catalog assets. It is not a
replacement for direct tests; it defines how a capability moves from "tests pass"
to "audited for its declared domain".

## Why this exists

Passing tests prove behavior only on the exercised cases. A decomposer can pass
source-parity tests while a later SciRel rewrite/integration introduces a new
numerical branch, conditioning failure or contract misunderstanding. The audit
must therefore test parameter envelopes and independent oracles, not just repeat
the submitted examples.

## Risk tiers

- **A (critical)**: eigen/singular/generalized pencils, roots, iterative
  convergence, equilibrium/Picard, Green inversions, adaptive quadrature,
  interpolation near discontinuities, collision/rate asymptotics, anything whose
  output feeds another scientific capability.
- **B (high)**: multi-step compositions, geometry/grid mapping, splines/basis,
  nonuniform grids, high dynamic range rates, unit/axis conversions.
- **C (ordinary)**: closed-form scalar reductions, constants, format/IO adapters
  and validation helpers.

## Per-asset audit record

Each audited asset records:

- asset_id, domain, risk tier, owner;
- declared applicability and numerical limits;
- direct tests and exactly what branches they cover;
- probe families: scaling, permutation/axis, limits, singular/defective cases,
  extreme magnitude, dtype, invalid/failure paths;
- external truth: source project, independent analytic/limit, or `NONE`;
- contract claims re-checked against observed behavior;
- residual risks and a verdict (`pass`, `pass-with-limits`, `fail`, `blocked`).

## Required checks

1. Run every `verification.tests` file and the contract example.
2. Probe at least one admissible input outside the example: scaling,
   nonuniform grid, repeated/defective spectrum, near-singular matrix, large or
   small magnitude, or a boundary/limit.
3. Test at least one declared failure path and confirm no silent fallback.
4. For tier A, compare against an external source/analytic oracle where available;
   SciRel output must never be the reference for itself.
5. Record the numerical floor (roundoff/conditioning), not only residual norms.
6. Update the contract if its evidence claim is broader than what was tested.

## Closed P0 finding

The historical `scirel.kinetic.multifluid-frequency-solve` / `fluid_solve_state`
failure at valid two-species parameters (`B0≈2.4e-3 T`, `k=0.05–0.15 m^-1`) was
fixed by the identity-inertia standard-eigenproblem correction. It is closed by
the independent external PDRF oracle regression
`tests/kinetic/test_dispersion_multifluid_oracle.py` (14 real frequencies at four
k points, rtol 2e-9, backward error <=1e-10) plus the named historical reproducer
in the same file. The external oracle, not SciRel self-consistency, is the closure
evidence. No open P0 finding remains.

## Gate

- No unresolved tier-A defect enters a release candidate.
- Every asset has an audit status and evidence link.
- A capability with a known limitation may pass only with that limitation in its
  contract and user-facing API documentation.

## Prevention at ingestion

The failures found by the audit are mostly ingestion-design failures, not isolated
coding mistakes. The receiver must not accept a candidate merely because its
submitted tests pass. Future intake requires:

1. **Declared evidence envelope** — the candidate states the tested parameter
   ranges, branches, grids, species/model regimes and known singular limits. A
   test outside that envelope is a new claim, not a regression.
2. **Oracle class** — every tier-A capability names one of: independent
   analytic/high-precision, bounded source-method parity, or self-consistency
   only. `self-consistency` is not an independent oracle and must be visible in
   `verification.evidence_ceiling`.
3. **Asset-specific direct evidence** — shared test files must state which
   asset/feature they actually validate. A file that describes itself as a plan
   or proposed gate cannot be bound as validation evidence.
4. **Adversarial probes** — at least one scaling/limit/singular/defective-case
   probe beyond the source example, plus one declared failure path. Tier A
   requires this before acceptance; tier B requires it before release.
5. **Roundoff/conditioning floor** — record the numerical floor and do not use a
   tolerance below it as a pass criterion. Growth/zero-mode claims need a
   separate precision argument.
6. **Composition evidence** — when a composition binds the capability, intake
   runs the composition as well as the leaf. Leaf tests cannot prove graph
   wiring, ordering, units or failure propagation.
7. **Independent intake rerun** — the receiver reruns the probe set in its own
   environment and may add cases that the decomposer did not know about; this is
   not a demand for receiver-specific behavior, only an adversarial test of the
   declared scientific relation.
8. **Verdict before admission** — tier A needs an audit verdict (`pass`,
   `pass-with-limits`, `blocked`); no unresolved tier-A defect enters a release
   candidate. A known limitation is allowed only when it is written into the
   contract and user-facing API documentation.

The decomposer still owns the source-faithful translation and its evidence. The
receiver owns the independent acceptance test, the declared scope and the
decision to admit. Neither side may use "tests pass" or "SciRel output matches
itself" as the final proof.

## Merge layers and exposure hold

A candidate is public when, and only when, both its implementation and its
contract land in `src/scirel/` and `catalog/examples/`. Until then it stays
under `catalog/review/`: the contract and its tests are preserved there, and it
is excluded from packaging, documentation, the capability index, the query
service and the capability matrix. A failing structural check keeps it there too,
with the failure recorded beside it.

A tier-A asset with only self-consistency evidence cannot auto-merge. A contract
under `catalog/review/examples/` stays there until its implementation lands in
`src/`: the implementation is the truth, the contract is its derived record, and
the documentation derives from the contract. Review notes never override code.


## Structure checks

There is no status registry: what exists in `src/` and `catalog/examples/` is the
public surface, and `scripts/validate_asset_documents.py` checks only structural
consistency — required fields, schema conformance, ports that match the
implementation. It reports no scientific verdict.
`not-audited` and `blocked` are never exposed. A new asset without a reviewed
status is held rather than given a passing one. The gate needs only tracked files
and checks structure only. The claim ceiling of each capability is in its contract
`verification` block.

## Exposure hold is not an outbound handoff

Holding an asset means only that it is not exposed as a catalog capability. It
does not authorize the outbound worker to stop a user's request or to ask the
user to obtain a human review/decomposition. During a real request a held or
missing capability is a gap: mark it, try an independent public-science glue or
substitute, verify it, and continue; if that is impossible, state the concrete
missing input/fact and deliver the bounded result that remains. Never read or
import the held implementation as a hidden shortcut.

## Outbound gap and input-failure policy

These are process behaviours, tested independently of capability count:

- a missing/held/near-miss capability is an in-flow **gap**, not a user handoff;
  fill it with a public formula/exposed composition or report the concrete
  missing input and a bounded result;
- do not import/read a held implementation as a shortcut;
- classify a failure before acting: user-data/domain invalid, interface/contract
  mismatch, numerical/applicability limit, or implementation failure. Do not
  call a representation/API mismatch "invalid physics", and do not call valid
  data outside a numerical envelope "invalid user data".

## Final quarantine architecture and merge chain reaction

The import guard is a transitional stopgap. The target architecture separates
three trees:

- `src/scirel/` — only merged, admitted code; nothing held is installed or
  importable;
- `catalog/examples/` — only admitted contracts and public evidence;
- `catalog/review/` (and an optional external review tree) — candidate contracts,
  candidate code, audit verdicts and human-review records; never installed.

A candidate moves in this order:

1. stage it in the review tree, outside the package and public catalog;
2. run its contract, direct tests, adversarial probes and import-surface check
   in a review harness;
3. record the verdict; unresolved disagreement or missing owner decision keeps
   it staged;
4. on approval, merge in dependency order (leaf capability before composition);
5. regenerate the public export manifest and docs; run the dependency closure;
6. remove the staged copy only after the merged copy is green.

Avoiding a merge chain reaction:

- derive public exports, docs and capability index from the admitted manifest,
  not from a filesystem glob or hand-maintained `__all__`;
- compute the reverse-dependency closure from contract dependencies and Python
  imports before merging; a merge is a batch, never a partial file move;
- require the closure's tests, docs build and import-surface check to pass;
- if one member of a composition is held or fails, the composition is not
  exposed; do not ship a partially wired chain;
- package/wheel checks must prove that held modules and symbols are absent, not
  merely guarded at runtime.

## Complex-case replication direction (recorded, not started)

A future complex-case track is to replicate the full functionality of a
decomposed project using the current SciRel capability layer as the starting
point. That is a software-engineering workflow (dependency closure, staged
candidates, integration tests, external truth), not a single capability audit.
It is recorded as a direction, not a release gate; no coverage claim is made
until the workflow and its acceptance evidence exist.

## Outbound acceptance S1-S6 (exposed 247)

- S1 fillable gap: PASS; |B| ratio via glue matched Pleiades truth exactly.
- S2 unfillable gap: PASS; parametric/bounded CX rate, no user handoff.
- S3 held capability: PASS; independent Coulomb-log formula with checks, no held import.
- S4 input failure: PASS; negative density classified as user-data invalid, not a capability failure.
- S5 success chain: PASS; B0/peak matched Pleiades truth.
- S6 held dependency: PASS-WITH-LIMITS; held axisymmetric Picard replaced by exposed free-boundary chain with a disclosed claim ceiling.

The exposed outbound chain is usable; held capabilities remain in-flow gaps to fill
or bound, not user handoffs. The capability count is not the acceptance metric.

## Source-based decisions

Use the source tree as an oracle for **source fidelity**, not for choosing
between two physically defensible models:

- **source parity**: implementation, defaults, branches and failure semantics
  match a pinned canonical source commit; release with bounded evidence, not a
  claim of physical calibration.
- **source conflict**: two source versions/paths disagree. Choose the canonical
  archive/commit, repair the implementation and add a regression; do not let both
  versions remain unlabelled.
- **source defect**: the source itself has a silent floor, warning-only guard,
  lost branch or similar defect. A repair is allowed only when it is explicit,
  tested and labelled `source-defect repair`, never `source parity`.
- **no source / missing artifact**: keep the asset held. Do not substitute a
  plausible formula or a missing graph artifact.
- **API policy**: mask strictness, terminal ordering, fail-closed continuation or
  similar receiver policy is not source behaviour. Record it as SciRel policy,
  not as parity.

Source identity and commit hashes belong in the review verdict/evidence record,
not in the public contract body. A source-parity result never replaces an
external physical oracle or user acceptance.
