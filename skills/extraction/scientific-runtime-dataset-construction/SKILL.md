---
name: scientific-runtime-dataset-construction
description: Use when a runnable scientific source program and source runtime can generate missing inputs, predecessor state, hidden intermediate state, branch or boundary records, stochastic event history, or source-side numerical oracles needed to investigate and close a declared extraction, schema, or validation gap.
---

# Scientific Runtime Dataset Construction

## Purpose

Construct a source-backed, coverage-driven observation dataset for one declared scientific gap.
Use the real source runtime to expose the input/state/output handoff that ordinary final files omit.
Keep the dataset outside the formal asset bundle and make every captured value traceable to a
source revision, runtime, branch, and semantic termination state.

This skill defines the method for dataset qualification, case design, source instrumentation, capture integrity,
coverage accounting, split isolation, and evidence handoff. It does not choose operator/task-graph boundaries,
implement missing science, judge scientific correctness, write owner state, or accept an asset.

For hidden common-block or lifecycle state, this skill may also construct and test a candidate
typed carrier from source-backed observations. The carrier is a proposed explicit schema for the
handoff, not a captured answer and not a formal asset; the calling owner retains its boundary and
validation or review retains scientific acceptance.

- Hand a concrete evidence-bounded missing relation to `scientific-relation-implementation`.
- Hand holdout, residual, invariant, convergence, and claim evaluation to
  `scientific-computation-validation`.
- Return exact observations to the calling owner; this helper does not decide workflow completion,
  approval, public catalog inclusion, or release.

A dataset closes a named observation gap for an exact source revision and remains external evidence.
Provider or worker failures are retryable process observations, while a genuinely missing producer or
human choice must be returned with a specific reopen condition.

## Dataset Model

For D1 select `source_fidelity` under the [stage boundary](../scientific-computation-asset-extraction/references/stage_boundary_contract.md#d1-responsibility).
Capture original examples or self-constructed source-admissible inputs, genuine initial/predecessor state,
outputs/post-state and termination/failure markers needed for differential comparison. Preserve the exact
source/runtime and raw observations. Record source issues with trigger, source location, observation and
impact for D2; do not repair the source or route to scientific correction merely because capture reveals a defect.
For this mode, use the workflow's capture/integrity steps and return fidelity observations; scientific-oracle
splits, independently sealed holdout and independent scientific promotion gates below are not D1 prerequisites.
Any selected manifest validator retains its actual structural contract; do not fabricate split/seal facts.
Owned/initialized/isolated native state may be preserved internally when the package can reproduce its lifecycle;
construct a typed carrier only where a reusable call boundary actually needs one, not for every internal field.
Undefined source behavior or a crash without observable stable state remains a limitation, not a guessed value.

The scientific-oracle, controlled-repair and scientific-promotion requirements below apply only to separately
requested later-stage scientific claims. Capture itself grants neither stage completion nor scientific validity.

Treat one case as a complete observation tuple:

```text
declared source input
+ genuine predecessor state and order
+ target-call input/pre-state
+ branch, boundary, index, unit, axis and ownership metadata
+ target output/post-state
+ semantic completion or failure marker
+ oracle/invariant references
```

A final output alone is not a runtime-state dataset. A probe that calls a target routine without
its genuine predecessor state is not a valid source observation.

Keep four roles distinct:

1. `extraction`: visible while identifying the mapping and contract.
2. `boundary`: covers endpoints, threshold sides, invalid/fail-closed behavior, and state edges.
3. `holdout`: hidden from implementation decisions until replay evaluation.
4. `scientific_oracle`: independent analytic, residual, invariant, refinement, or external data.

Source parity from any split proves source behavior only. It does not prove that the source or the
extracted relation is scientifically correct.

When observations expose a scientific contradiction, preserve the genuine failure and load
`scientific-relation-implementation`, including its `references/scientific-correction.md` material.
Do not normalize away the failure or designate known wrong source values as the correction oracle.
Keep original and repaired observations distinct; extraction/implementation repairs the usable asset,
validation tests the corrected relation independently, and read-only review assesses the new revision.

## Source-behavior oracle and repair evidence

If the declared gap is a missing physical oracle, split it before probing. Capture source-defined
termination semantics (normal/failure marker, check-before/after-update order, iteration bound,
terminal fields, and call-site interpretation) as a source-behavior oracle. Record process status and
semantic status separately, and prove the marker on normal plus applicable boundary/failure cases.
This evidence can unblock source mapping or source-free parity, but it must be handed to validation
as `source_behavior_verified`; it never upgrades physical or numerical correctness.

If the source run exposes a reproducible shape, index, allocation, or producer/consumer mismatch,
preserve the immutable raw failure and create a controlled repair receipt rather than silently
normalizing the capture. The receipt must name producer and consumer extents, index/axis contract,
source-intent anchors, minimal patch delta, unaffected-domain parity, repaired-boundary cases, and a
sealed holdout. Do not invent a reshape, truncate, pad, clamp, or zero default. Keep
`legacy_exact`, `source_repaired`, `scientifically_corrected`, and `validation_oracle_gap` distinct;
the dataset is evidence and never the repaired producer or a scientific oracle by itself.

## Hidden-state reconstruction gate

`source has no typed payload` is not a stopping condition. When a declared gap concerns common
blocks, module globals, saved locals, file-backed history, restart state, feedback, or implicit
call order, first build a finite probe matrix and attempt to make the consumed state explicit.
Capture the declaration and storage owner of every candidate field, its writer and reader, active
extent, axes, units, selectors, and lifecycle phase. Use a genuine predecessor chain, then apply
one-factor perturbations and material boundary cases. For iterative or restart behavior, capture
at least two distinguishable states and the serialization/reload transition when reachable.

From those observations, write a minimal typed-carrier candidate and replay the literal target
and its declared downstream consumer from that carrier. The carrier may be newly designed by the
extractor, but every field must have a source declaration/call-boundary or source-defined
derivation anchor. Keep the raw observations and carrier proposal external to the formal bundle.

Only after the matrix is integrity-valid and the carrier replay has been attempted may the gap be
terminally classified. A valid negative result must state which fields, branches, lifecycle phases,
and serialization paths were covered, what remained non-identifiable or unreachable, and why the
missing fact cannot be recovered from the source runtime under the declared scope. “No struct,”
“common block is implicit,” “the full run is expensive,” and “a prior static audit saw no payload”
are not negative proof.

## Workflow

1. **Qualify the declared gap.** Require a named target mapping or framework edge and current gap
   classification. Use this skill only when missing observations can materially distinguish the
   contract, producer, branch, state transition, or oracle. Do not generate data merely to increase
   sample count.
2. **Freeze the evidence universe.** Record immutable source revision, project-specific source
   runtime image/digest, compiler and flags, external-table identities, probe revision, input
   configuration, RNG/scheduler policy, and normal semantic completion marker. Instrument only a
   disposable workcopy; keep the original source snapshot read-only.
3. **Design the coverage matrix before running.** Partition only by a scientific branch, selector,
   boundary rule, state lifecycle, index/axis convention, or stochastic/parallel mode that the
   declared target mapping actually consumes. If source order forces a condition inactive at the
   target, or a later consumer alone uses it, assign that condition to the later mapping rather
   than leave it as a false uncovered partition here. Assign every case to exactly one primary
   split. Read `references/boundary_coverage.md` for the required boundary and holdout rules.
4. **Probe the real handoff.** Capture only after the actual predecessor chain has initialized the
   consumed state and the target branch has accepted the event/call. Anchor capture to that declared
   target-call or producer event and record its lifecycle phase; do not use a global time/iteration
   label as the capture trigger. Capture pre-state and output separately. Capture branch selection and consumption/ownership controls independently of
   coefficient or field values: a present or nonzero coefficient does not prove that the current
   mode/event consumed it. Version self-describing state streams and reject unsupported versions,
   undeclared trailing bytes, or missing axis/type declarations. Never reconstruct a missing
   intermediate state from a final diagnostic.
5. **Generate source observations.** Run only in the project-specific source runtime. Require both
   process status and semantic termination/failure status. A routine-level record may use
   `target_completed_outer_failure` only when the genuine target call returned, its complete
   pre/post-state was captured before the later outer-program failure, and the manifest names that
   failure. It covers only that local mapping, never full-program completion or trajectory parity.
   Preserve raw source records; any
   canonicalization or serialization conversion creates a derived attachment with its own hash
   and declared tolerance. When a captured container also includes inactive, padded, or scratch
   storage, record its active extent and consumer access range before comparing it: evaluate the
   declared scientific mapping on the consumed extent, report raw-storage residue separately, and
   capture predecessor workspace, initialization, and iteration order only if byte-exact storage
   replay is a declared target. If a replay intentionally restricts modes, rays, surfaces, events,
   or rows, derive a coherent slice contract for every coupled axis and count field before running;
   compare only with an oracle reduced over that same domain. A whole-domain accumulated output is
   not an oracle for a subset replay, and a mismatch must not be hidden by tolerance relaxation.
   For an external producer-to-consumer handoff, receipt payload emission, identity/schema, and
   consumable extent separately: a normal process or semantic terminal does not prove the declared
   payload exists. Record non-emission as a producer configuration/schema boundary; never pass an
   empty, fallback, or unrelated output to the consumer. For a deterministic, self-contained
    source subroutine whose required state can be initialized explicitly, use the bounded routine
    microprobe protocol in `references/method_feedback_protocol.md` rather than over-instrumenting
    a full program run. When a source script can clear wrapper state or writes a relative output,
    preserve its native writer and copy the completed raw output from the disposable work directory
    to a versioned external attachment before teardown; never make a wrapper variable a hidden
    source dependency.
6. **Validate dataset integrity.** Check case identity, split ownership, coverage accounting,
   relative paths, artifact hashes, required state fields, and holdout isolation. Read
   the bundled `scripts/validate_dataset_manifest.py` from this skill package; if executable validation is needed,
   run that exact file against `<manifest.json> --check-files`
   before handoff. Reading the material alone is not execution evidence.
7. **Evaluate promotion readiness.** A dataset may close a missing fixture/oracle or reveal a
   stable producer. It never becomes the producer itself. Require an unseen replay and an
   independent scientific/numerical gate before upgrading a reusable scientific capability.
8. **Hand off and reclassify.** Record what the dataset proves, what it does not prove, the exact
   remaining fields/branches, and the next owner. Keep `extraction_gap`,
   `configuration_or_schema_need`, `ai_completable_glue`, `validation_oracle_gap`, and
   `cannot_complete` distinct.

## Promotion Rules

Promote a discovered relation toward extraction or implementation only when all applicable items
hold:

- the source reaches a stable semantic terminal for the declared input domain, or the declaration
  is a bounded local target mapping recorded as `target_completed_outer_failure` with its complete
  target receipt before the outer failure;
- the observation comes from the genuine call boundary and includes required predecessor state;
- units, axes, index base, selectors, active extents, and state ownership are explicit;
- for a hidden-state/lifecycle gap, the probe matrix is integrity-valid, a typed-carrier attempt is
  recorded, and source replay from that carrier either succeeds or yields a specific
  non-identifiability/unreachable-boundary result;
- the candidate recomputes outputs from declared inputs instead of reading captured answers;
- holdout and boundary cases pass without changing the contract or tolerance after inspection;
- at least one independent relation, residual, invariant, limit, or refinement gate applies;
- source-free replay succeeds in the fixed asset runtime without source access;
- the dataset remains external evidence rather than a formal operator/task-graph dependency.

If only a captured array can be replayed, classify it as an explicit fixture/schema path. Do not
claim that its upstream producer has been extracted.

## Hard Boundaries

- Do not infer an algorithm uniquely from input/output samples when source/equation semantics do
  not determine it.
- Do not terminally classify a hidden-state or lifecycle gap merely because the source has no
  typed struct. Complete the hidden-state reconstruction gate and attempt a source-backed typed
  carrier first.
- Do not use synthetic inputs to claim experimental or device fidelity. They can prove algorithms,
  boundaries, or numerical behavior only.
- Do not turn undefined source behavior, uninitialized state, a crash-before-capture, or an
  invented clamp into legacy parity. Route a corrected relation separately if its science is known.
- Do not treat one seed or one parallel run as arbitrary stochastic/MPI equivalence. Capture RNG
  continuation and event history; keep scheduler/reduction semantics as separate contracts.
- Do not leak holdout target outputs into implementation fixtures, documentation examples, or
  generated operator tests before evaluation.
- Do not place probes, parsers, dataset manifests, large arrays, or gate JSON under `operators/`
  or `task_graphs/`.

## Reference Routing

- Read `references/dataset_contract.md` when creating the manifest, case layout, provenance, or
  serialization contract.
- Read `references/boundary_coverage.md` when designing deterministic, iterative, stochastic,
  parallel, table, matrix/RHS, or failure-path cases.
- Read `references/method_feedback_protocol.md` for the bounded routine microprobe protocol.

## Final Report

Report the dataset path, manifest identity, source/runtime provenance, case/split counts, covered
and uncovered partitions, semantic failures, integrity-validator result, strongest earned claim,
remaining gap classification, and next method or decision owner. The dataset is evidence; it is never a formal
scientific asset by itself.
