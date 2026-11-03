# Source-Free Extraction Playbook

## Purpose

Use this reference only when an extraction candidate needs source execution, hidden-state recovery, source comparison,
runtime dependency repair, or source-free replay. It supplies a generic recovery loop. Project-specific formulas,
case names, solver branches, and one-off failure recipes do not become universal extraction rules.

The delivered callable must execute from explicit inputs without the original checkout, hidden external source
state/order, captured answer arrays, network access, or host-specific paths. Attributable source implementation,
native libraries or local programs may be packaged runtime components with declared dependencies and explicit
owned/reset/isolated state lifecycle. Source probes, instrumentation and captured answers remain external evidence.
Use the [D1 source-fidelity boundary](stage_boundary_contract.md#d1-responsibility): source issues are recorded for
D2, and independent scientific-correctness research is not a prerequisite to source-free extraction.

## Bounded source/runtime loop

1. Freeze the exact source snapshot, build recipe, runtime identity, case inputs, branch selectors, and expected
   observable outputs. Keep the source workcopy disposable and separate from the formal bundle.
2. Trace the target relation statically: formulas, reads/writes, initialization, shape/extents, units, indices,
   boundary paths, termination, failure markers, and downstream consumers.
3. Run the smallest source case that reaches the target. Instrument only fields needed to answer the named
   scientific/state question. Record entry and exit state rather than collecting the entire process image.
4. Perturb one factor at a time and include applicable zero, equality, threshold, endpoint, disabled-branch, and
   second-lifecycle-state cases. A single successful trace does not establish a state contract.
5. Design the smallest typed caller-owned carrier that can reproduce the mapping. Replay from that carrier outside
   the source call sequence. Captures grade the replay; they are never copied in as active inputs.
6. Return the reconstructed ports/state to the candidate microcycle, or record the exact non-identifiable field,
   evidence ceiling, owner, and reopen condition. Do not hide an unresolved field behind a generic configuration
   object.

For repeated runs, separate build latency from target execution and reuse only verified build/runtime layers that
do not change the source or evidence identity. Keep one current result per case; replace superseded attempts.

## Hidden state and lifecycle

Treat globals, common blocks, module state, saved locals, files, RNG history, restart records, and implicit call
order as hidden-state reconstruction problems. For each required field record:

- declaration, shape, active extent, unit/normalization, and storage owner;
- genuine producer and initialization path;
- target entry/exit value and all readers/writers;
- frozen, recomputed, feedback, mutation, persistence/restart, and terminal-consumer semantics; and
- branch guards, step/epoch/mesh/axis ownership, and failure behavior.

`The source has no typed struct`, an associated pointer, a final-output file, or an inconvenient full-program run
does not prove that a typed carrier is impossible. Attempt the carrier and replay first. If a consumer would need
to infer an intermediate from a terminal value or recompute upstream science, expose the stable intermediate or
merge the proposed candidates.

Use `scientific-runtime-dataset-construction` when producing the required observations is itself a bounded task.
Its dataset remains external evidence and cannot become the scientific producer.

## Source behavior and claim ceiling

Keep these claims distinct:

- `source_behavior`: what the frozen program emits and how it terminates for a declared case;
- `source_fidelity`: the extracted callable agrees with that behavior under explicit tolerances; and
- `source_anomaly`: source behavior conflicts with an independent relation, invariant, or declared intent.

Source termination may be derived from control flow, explicit markers, bounded instrumentation, and replay even
when no external physical oracle exists. Source fidelity can support a bounded extraction claim but cannot prove
universal convergence or physical correctness. Record a source anomaly with its exact evidence, affected domain,
claim ceiling, and reopen condition; do not repair or normalize the source-backed scientific relation here.

Treat abnormal termination precisely. A source crash before stable state capture is a capture failure, not an
oracle for guessed defaults. A nonfinite producer field is not permission to sanitize it. Preserve the earliest
bad value, indices, selectors, producer context, and failure marker; reopen the actual producer, schema, or oracle
question.

## Runtime and blocker audit

Before calling a dependency or evidence gap external:

1. validate command syntax, mounts, paths, executable presence, architecture, image identity, and receipt parsing;
2. check whether the dependency is already present in the frozen source/evidence universe;
3. check the isolated runtime's package repositories or an architecture-compatible derived image;
4. enumerate every missing receipt/contract field and classify it as source-derived, runtime-derived, or supplied
   by an external owner; and
5. generate the first two classes before requesting the third.

Install missing build/runtime dependencies only inside the owned isolated environment and record the resulting
runtime identity. Do not modify the host or candidate contract to disguise an environment defect. A genuine
external gap names the exact value/schema/oracle, responsible owner, affected claim, and reopen condition. Other
independent queue items continue.

## Candidate and project gates

For an operator candidate freeze, verify:

- path-loadable callable execution with no forbidden source access;
- explicit inputs cover every required value/state/selector;
- relation-sensitive candidate tests and directly affected graph tests pass;
- contract, implementation, tests, dependency versions, and provenance bind one digest; and
- the evidence supports only the declared claim ceiling.

For a TaskGraph candidate freeze, additionally verify exact dependency versions, port bindings, order, branches,
feedback/convergence/failure behavior, and that returned fields are the actual terminal state.

Whole-project completion is stronger. It requires a frozen census, candidates plus non-candidate dispositions,
closed material branches and state lifecycles, and source-fidelity reassembly from identical explicit
case inputs to complete declared terminal outputs against one bundle revision. Use original plus additional
source-admissible cases where material uncovered behavior exists; source-defined failures belong to the comparison.
A separately sealed holdout is required only by an explicitly selected protocol/claim, not by D1 fidelity itself.
Candidate staging may happen
earlier, but this project gate remains the extraction completion condition.

Run changed-candidate and direct-dependent tests during the production loop. Run bundle-wide structure, digest,
source-free, and functional-reassembly gates once at a declared bounded delivery or project freeze. A validator
or test runner must report the exact command, discovered/executed/passed counts, runtime identity, and candidate
digest; zero collected tests are not passing evidence.

## Evidence retention

Keep raw probes, captures, large arrays, build trees, and container output under one owned run envelope. Retain only
the current evidence needed by an active candidate or extraction gate. Condense durable source anchors, case
identity, selectors, metrics, tolerance, claim, and gap/reopen facts into the candidate or project sidecars.

After the last evidence consumer completes, remove superseded attempts and run-owned disposable resources, verify
that no capture became a runtime input, and recheck the formal bundle digest. Never prune shared images/caches,
another run, or a broad parent path. Use `evidence_persistence_boundary.md` for substantial evidence or container
lifecycle work.
