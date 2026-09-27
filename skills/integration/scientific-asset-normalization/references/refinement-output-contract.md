# Normalization output contract

`scientific-asset-normalization` prepares expert-reviewable candidate material outside the maintained SciRel
baseline. This is a logical output contract, not a database schema or release record.

## Required review unit

For each proposed scientific identity, produce:

1. **Candidate document**: incoming and current behavior, proposed disposition, material scientific differences,
   normalized relation and public API, dependencies, applicability, provenance, evidence ceiling, known limits, and
   the exact expert decision requested.
2. **Candidate code**: the smallest proposed implementation/patch, or an explicit no-code rationale when the
   disposition is reuse, duplicate, or documentation-only.
3. **Candidate tests**: relation-sensitive, boundary, failure, adapter, and composition checks appropriate to the
   claim, with commands and results actually observed.

When the proposal adds or changes a public asset, the document includes a proposed
`scirel.asset-document.v1` exact document. Do not add it to the maintained catalog before approval.

## Comparison inventory

Account for every input with an evidence-bounded relationship to an existing or proposed SciRel identity. Useful
dispositions include:

- reuse or exact duplicate with preserved lineage;
- semantic-equivalence proposal;
- subsumes or overlaps;
- parameterized variant;
- lossless adapter;
- composition;
- new capability;
- conflict; or
- unresolved.

The inventory is navigation for the batch, not a second registry or a substitute for the candidate document. A
larger TaskGraph does not automatically make a smaller graph redundant, and partial node overlap is not duplication.

## Candidate handling

Record the SciRel baseline and unpublished-candidate view used for comparison. Keep candidate files excluded from
public imports, catalog generation, and wheels.

Before upload, a draft may be edited, merged, replaced, or withdrawn. Upload records the exact initial
document/code/test version for each review item; the workbench does not run a model that rewrites queued content.
After upload, only explicit human edits under an item lease create content versions. Later AI rework is a separate
preparation task whose result the uploader must explicitly submit or link.

When this work enters the SciRel workflow, encode the final units in
`contracts/standardization-submission-dev.schema.json`. The schema fixes the reviewed content and its input
bindings; it does not constrain the comparison method, temporary probes, or candidate workspace layout.

See [human review handoff](human-review-handoff.md) for the upload boundary and approval consequences.

## Evidence and completion

Inherited source parity, scientific, numerical, port, lifecycle, and composition claims keep their original limits.
Changed candidates receive fresh evidence for the changed behavior; an old pass is not copied by name. Unknown or
conflicting facts remain explicit rather than being normalized away.

The normalization run is complete when every in-scope input has a disposition, every proposed change has a coherent
document/code/test review unit, dependencies and lineage are resolvable, and unresolved questions are visible. This
completion only means the candidate is ready for expert consideration; it does not approve, integrate, or release it.
