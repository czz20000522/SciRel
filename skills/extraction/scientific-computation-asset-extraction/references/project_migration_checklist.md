# Project Migration Checklist

Use this checklist when applying the extraction method to a project that is not the project used to develop the method. Do not inherit defaults, tolerances, branch names, or completion claims from the previous project.

## Freeze and map

- Record source snapshot, workcopy boundary, Docker image/runtime identity, and a source-access counter.
- Rebuild source in the target image from a clean workcopy; discard host object files, close every makefile/link dependency (including stubs and historical auxiliary sources), disable permissive unresolved-symbol linking, and fail the source gate before running a probe when format, architecture, or link closure is wrong.
- Reuse or establish the source-backed candidate census before deep extraction; derive the final `program_framework_map.md` at handoff. For every important edge record `from.output -> to.input`, hidden state, transforms, shapes, axes, units, selectors, and branch conditions.
- Mark each candidate as package, support kernel, rework, rejected, or a canonical gap. Do not let an unprocessed candidate disappear from the queue.
- Create a branch/oracle matrix before deep extraction. Keep one row per physical mode or boundary family, including selectors, producer chain, hidden state, caller contract, oracle provenance, source-free demand, and canonical gap. Do not use branch count as a package quota.
- Create a capability evidence matrix for every named requirement, capability, branch, artifact, invariant, and gate. Use concrete selectors and bind each row to an executable demand, external source-free evidence, and a canonical gap or proven status; use the matrix template rather than a package-count summary.

## Extract by producer stages

For each public tensor or solver input, capture the chain `producer terms -> scale/normalization -> boundary/post-transform -> scatter/public output`. Preserve source-specific signs, index maps, row/RHS rules, ghost/edge state, and velocity-zero behavior. If final outputs omit required state, declare a caller-owned runtime-state contract; never infer hidden state from the final file.

When a solver boundary is assembled in a branch-heavy producer, instrument the producer immediately before normalization and capture raw branch terms, row identity, columns, raw RHS, and normalization scale. Replay at least two independent branches/cases from those captures before emitting a reusable producer operator; keep final-row aggregation as a separate consumer. This distinguishes a reconstructable raw-term contract from an unsupported dense-output inference.

Before fitting any final-output diagnostic adapter, compare hidden-to-public ratios across species, surfaces, time, and enabled branches. Masked or omitted tensors and non-stable ratios are evidence of a missing normalization/geometry contract, not permission to add a scalar correction.

For multi-species outputs, record the public tensor axis order and validate species-specific energy/velocity grids. Bind per-species weights or an explicit mass/relativistic transform; never reuse species-0 energy weights by default.

## Prove the bundle

- Each package has its required contract, implementation, and executable test.
- Execute and count tests per package directory when suites reuse generic module names; treat aggregate collection mismatches as infrastructure evidence, never as package failures or proof of coverage.
- Keep probes, parsers, captures, JSON, logs, and Docker reports outside `operators/` and `task_graphs/`.
- Run a source-free fixed-image gate: stable digest before/after, zero source access, zero static findings, and recorded image/runtime identity.
- Run at least one bundle-only case or custom-demand composition across multiple emitted graphs, then perform an edge-driven closure sweep.
- For branches that enter initialization/solver but fail before finite output, preserve the last runtime marker, solver status, partial output schema, and non-finite/masked counts; classify the branch contract/oracle gap instead of treating process exit code as scientific success.

## Classify and stop

Use only `extraction_gap`, `configuration_or_schema_need`, `ai_completable_glue`, `validation_oracle_gap`, and `cannot_complete`. Stop only when the census has no unprocessed package-worthy candidate and all remaining gaps have evidence, missing-field lists, and a reproducible capture route. Otherwise label the run `partial_extraction` and keep the queue visible.

## Completion audit

Before claiming the project goal is complete, make a requirement-to-evidence table for every named capability, branch, artifact, and gate. Re-run the relevant source-free composition at the same scope as the claim; a package gate, entrypoint smoke, final-output parser, or passing subset is not evidence of full-core parity. Keep the goal `partial_extraction` while any required `extraction_gap`, `validation_oracle_gap`, or unverified branch remains, and recompute the bundle digest after changing formal sidecars.
