# Framework Closure Priority

Use this reference when a project has many emitted operators but the declared
framework still has open edges. Close the graph before chasing hidden runtime
state that cannot be observed or safely reconstructed.

## Edge-first closure

An emitted endpoint does not close an edge. Record each edge as:

`from.output -> to.input | transform/order/sign/units | branch selector | required state/config`

Assign exactly one terminal status for the declared path:

- `emitted_asset`: the edge is implemented by an operator or nested graph;
- `controlled_glue`: the graph contains the bounded adapter, mapping,
  schedule, or state projection needed by the edge;
- `explicit_contract`: the consumer runs from caller-owned source-backed values,
  validates the contract, and fails closed when it is absent or incompatible;
- `configuration_or_schema_need`: the transform exists but runtime values,
  shapes, axes, units, or branch selectors are not supplied;
- `validation_oracle_gap`: the path runs, but an independent source/intermediate
  oracle is still required;
- `extraction_gap`: a source-specific formula, branch, index map, row/RHS,
  boundary rule, or state transition is not emitted;
- `terminal_non_emitted`: the endpoint is intentionally outside scientific assets
  (for example final-file serialization).

Never mark an edge closed solely because both endpoint packages pass unit tests.

## Priority order

Process edges in this order:

1. Case-entry or demand-entry -> first scientific state.
2. Existing producer -> existing consumer edges with only missing binding,
   normalization, scheduling, or shape glue.
3. Edges feeding a solver, state transition, or diagnostic response, ordered by
   downstream fan-out and branch count.
4. One representative branch per source family, then a multi-branch smoke using
   the same graph entrypoint.
5. Hidden common-block/state-to-all-rows producers only when their fields are
   observable in a workcopy capture and an independent oracle exists.

After endpoint loading passes, promote any still-implicit graph metadata in the
same order: first high-fan-out edges feeding the main solver/diagnostic chain,
then branch-family edges, then leaf/support graphs. Add `from_output` and
`to_input` only when they are already named by the node `outputs`/`inputs`,
`graph.py`, or task-graph documentation. If the port cannot be identified
without inferring hidden state, leave the edge as
`configuration_or_schema_need` and record the missing schema; metadata closure
must not invent a scientific transform.

For nested task-graph edges, distinguish a real data binding from a sequencing
or adapter dependency. Add `from_output`/`to_input` only for fields named by
both sides' existing contracts; leave event structures, alignment-only inputs,
optional hidden branches, and caller-owned storage maps as explicit schema gaps
rather than manufacturing port names to make an audit count green.

If an explicit caller-owned row/state contract already composes through the
solver, it is sufficient for framework closure. Keep automatic hidden producer
parity as a separate `extraction_gap` and/or `validation_oracle_gap`; do not add
a duplicate wrapper merely to improve counts.

## Minimal closure probe

For each selected edge, run one bundle-only probe that:

1. loads assets by path with the source tree unavailable;
2. binds the declared producer output to the consumer input;
3. checks shape, finite values, index base, units/sign/normalization, and branch
   selection;
4. observes the consumer output and confirms the default path is unchanged when
   the optional port is absent; and
5. rejects missing or conflicting contracts rather than inferring hidden state.

For each source-backed probe, record the mode/initialization guards before
running it and classify a zero-state, nonterminal, crash, or abort as a
failure-boundary result. Do not retry by mutating unrelated defaults until the
guard that controls the edge is identified; a reached callsite with empty
state is evidence of a boundary, not parity.

For hidden-state instrumentation, distinguish an untriggered branch from a
failed capture. Record the semantic terminal marker, process status, build/link
status, and per-branch trace counts separately. A zero trace count is only a
capture failure when the branch was expected to execute; otherwise classify it
as an untriggered branch and keep its replay/oracle gap explicit. Compile every
probe object and ABI dependency inside the approved execution image; host-built
objects or stubs are not runtime evidence and can create false link failures.

If ordinary output omits a hidden tensor, first exercise the source program's
existing long-output/diagnostic switch (for example `long_urf`) in an isolated
workcopy, then persist the elementwise tensor as an external oracle. Replay it
in a separate source-free invocation with only `/bundle:ro` and `/oracle:ro`;
require shape, finiteness, hash, and per-element max-abs/max-rel checks. An
aggregate or synthetic tensor is not elementwise producer parity.

For fixed-form Fortran probes, keep generated `WRITE`/`FORMAT` statements within
the source line-width contract (use continuation lines rather than relying on
column-72 truncation). Choose probe values in the model's meaningful numerical
range before judging a table or kernel as zero; record the selected energy/scale
and distinguish a true zero branch from an under-range input.

When a semantic-terminal intermediate capture contains a complete, source-backed
branch family of row/state contracts, replay that family through the emitted
consumer before attempting to reconstruct its producer. Record the selected
subfamily count, source anchor, per-row finite/convergence result, and numeric
delta. This can close a consumer edge without implying that the hidden
common-block producer, scheduler, or full source trajectory has been extracted;
keep those producer/oracle gaps separate.

For direct-solver parity, instrument the disposable source workcopy immediately
after its factor/solve call (when the source solution vector is authoritative),
and capture the complete matrix row contract plus the solved vector for one
matrix instance. Replay the rows through the emitted assembly graph and the
same storage class (dense or band) in a source-free invocation, then compare
solution `max_abs`, `max_rel`, `l2_rel`, and solver residual. A passing matrix
instance is representative solver parity only; it does not close all time
steps, hidden producer reconstruction, or ordinary-output inversion. If the
source solution vector or matching row contract is absent, classify the result
as `validation_oracle_gap` rather than reconstructing it from final output.

A complete terminal row/state capture (including columns, coefficients, RHS,
normalization, branch indices, and auxiliary fields) is an independent oracle,
not automatically a reusable producer. Promote it to a producer only when the
bundle can derive the same fields from its declared caller state and branch
selectors without replaying the source or relying on the captured rows.

For public netCDF or final-file adapters, use a real caller-owned fixture when
one exists and separate public-axis projection from hidden-state requests.
Validate the exposed axes/values and finiteness, then fail closed for omitted
solver tensors, RHS, or duplicate/missing axis selectors. A successful public
projection is an output contract only; it must not be used to reverse-engineer
common-block state or dense solver rows.

If a public fixture is intentionally fed into an explicit row contract and then
through a dense/band direct-solve graph, record this as a consumer-chain closure:
public projection -> caller-owned rows/RHS -> emitted assembly -> solve -> state
scatter. Require row completeness, residual, convergence, and missing-row
fail-closed checks. This demonstrates configurable downstream assembly, not
`source_solver_parity`, automatic RHS/row production, or hidden common-block
reconstruction; keep those producer/oracle claims separate.

For very large row captures, separate coverage from solver replay. Parse and
validate every row for equation continuity, family counts, finite metadata,
columns, coefficients, and RHS; then direct-solve only a bounded representative
sample per family (first/interior/last plus boundary variants). Do not spend a
probe turn solving hundreds of thousands of one-row systems when the claim is
row-contract coverage. Record `complete_row_count` and `replayed_rows`
separately, and keep full producer/all-row numeric parity as an explicit gap.

When a source run emits only one solver matrix, extend the evidence without
inventing a second timestep: verify one-based equation continuity, finite row
contracts, row ordering, and the observed family histogram (for example
`nvar`/boundary stencil families) together with the caller metadata ranges.
Record this as row-schedule/family coverage, not as additional solver parity;
keep `second_matrix_or_time_step=false` and retain producer, configuration, or
oracle gaps until an independent multi-step row/solution oracle exists.

When a runtime contract carries a physical invariant (for example positivity,
monotonicity, conservation, or boundedness), keep the invariant threshold
explicit during parameter sweeps. A sweep may identify caller-owned
configuration regions that satisfy the invariant, but it must not silently
relax a failed check because a violation is numerically small. Record the
near-boundary value and classify the result as a configuration/oracle boundary
until an independently justified tolerance or signed-value policy exists.

For scheduled producers, test recomputation policy and actuator/pulse gating as
separate dimensions. Include a case where recomputation is allowed while the
explicit pulse is off; otherwise a shared source schedule can appear correct
only because both gates happen to skip the same step. Preserve the producer
snapshot while recording the skipped consumer event and its reason.

For feedback edges, distinguish static per-step inputs from a sequential
feedback loop. A path is only a true feedback closure when the producer input
at step `t+1` is derived from the observed consumer state at step `t`. Run a
two-step perturbation probe: change the step-0 consumer state, then verify that
the step-1 producer input changes and that the graph executes the producer
after the step-0 state update. If producer arrays are materialized before the
trajectory, classify the edge as an explicit caller-owned/static composition
and keep `configuration_or_schema_need + validation_oracle_gap`; do not
claim dynamic feedback or add a duplicate wrapper. If a sequential projection
is emitted, record its shape/axis/unit contract and test both the changed
step-1 input and the unchanged default path.

For solver-owned hidden history (for example LSODE `rls`/`ils`), first use a
nonlinear caller-owned field so a segmented run cannot pass by linearity alone.
Compare one-shot integration with terminal-state-only segmented re-entry for
each supported method/branch, record the state delta and finiteness, and mark
`internal_history_export=false` when history arrays are not part of the
contract. This proves a reusable state-only seam/configuration boundary; it
does not close exact restart parity or hidden scheduler reconstruction without
an independent history oracle.

When the graph deliberately leaves feedback ownership to the caller, prove the
reusable external-reentry seam with two bundle-only invocations: pass the
finite `f_next` (or equivalent state snapshot) from invocation `t` into the
`previous_state` contract of invocation `t+1`, and exercise an orthogonal
actuator gate (for example beam on/off). Record state shape/finiteness, event
counts, skipped-event reason, and graph order for both calls. Classify this as
caller-owned sequential orchestration (`ai_completable_glue` plus any schema or
oracle gaps); do not add an in-graph callback or call a precomputed array a
feedback loop.

For customized demands, vary at least two independent caller-owned axes in one
bundle-only chain (for example species/surface binding plus actuator gate plus
diagnostic mask). Record selected indices, injected/skipped events and reasons,
mask policy, graph order, finiteness, and the physical invariant or numeric
oracle. Keep each axis explicit and mutually compatible; do not copy the source
case shell or infer a hidden common-block field from a changed output. Classify
missing values/shape/selector as `configuration_or_schema_need`, missing generic
dispatch as `ai_completable_glue`, and missing independent comparison as
`validation_oracle_gap`.

During incremental closure, run one demand-level chain from the case entry to a scientific output
or state transition. This is edge evidence, not final extraction acceptance. Before final closure,
run the extraction/validation functional-reassembly hard gate: identical source/bundle explicit
inputs, source-free execution, semantic completion, complete terminal scientific output/state
comparison, one canonical case, one sealed holdout, and coverage of every material branch. Keep
probes and JSON evidence outside `operators/` and `task_graphs/`.

## Persistence boundary

Write a newly proven operator, graph edge contract, branch/index rule, or bounded
oracle immediately. Defer only recomputable caches, counts, digests, matrices,
and report roll-ups until the checkpoint/final sweep. Remove runtime caches once
at final delivery, not after every probe.

If the formal-tree digest includes project sidecars, keep the authoritative
current digest in an external gate/matrix attachment rather than embedding it in
the hashed report or ledger; otherwise each digest update changes its own input.
Historical checkpoints may remain in sidecars, but the current digest must have
one external source of truth.
### Periodic/banded storage mapping

Downstream matrix assembly must consume explicit logical equation columns; band slots are storage coordinates and must not replace the caller-owned column contract.

For radial transport, an extracted explicit recurrence or solver (such as a transport-mesh update) does not close its upstream profile, target-density, or common-block feedback producer. Keep coefficient/profile/target arrays caller-owned unless their source-backed mapping and oracle are independently emitted; classify automatic feedback reconstruction as `configuration_or_schema_need` plus `validation_oracle_gap`, not as generic glue.

When a branch writes a logical transport row into periodic or compact-band storage, keep the caller-owned logical row index (`lsbtopr`/`lsprtob` result) separate from the one-based band slot (`lower`, `diagonal`, `upper`). Emit the bounded/periodic slot formula as a small reusable mapping only when its storage width and special endpoint rows are source-backed; never derive the mapping from `l`/surface position or silently invent ghost/permutation state. Missing row identity or permutation state is `configuration_or_schema_need`, while a generic adapter is `ai_completable_glue`.
