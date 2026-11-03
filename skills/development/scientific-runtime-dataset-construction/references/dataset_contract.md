# Source-Observation Dataset Contract

## Purpose and placement

Store a source-observation dataset under the external project evidence root, never inside the
formal `operators/` or `task_graphs/` tree. Give every dataset an immutable `dataset_id` and one
machine-readable `manifest.json`. Large numeric payloads may use `.npy`, `.npz`, HDF5, raw binary,
or another source-appropriate representation; the manifest owns their meaning and SHA-256.

Recommended layout:

```text
<project>_evidence/source_observation_datasets/<dataset_id>/
  manifest.json
  cases/<case_id>/...
  raw_source/...
  derived/...
  logs/...
```

`raw_source/` is immutable after capture. Put parsing, canonicalization, resampling, or
serialization-repair outputs in `derived/` and link them to their raw inputs by hash.

## Required manifest fields

Use `schema_version = "source-observation-dataset/v1"` and include:

- `dataset_id`: stable identifier;
- `purpose`: concise declared question;
- `gap`: `classifications`, `statement`, `target_mapping`, and current owner;
- `source`: project, immutable revision, source-runtime identity, probe revision, compiler/flags,
  external-data identities, and semantic completion/failure markers;
- `conventions`: units, axes, index bases, coordinates, signs, state ownership, serialization and
  tolerance rules;
- `coverage`: required, covered, and uncovered partition identifiers;
- `cases`: case records described below;
- `artifacts`: relative path, role, format, size, SHA-256, and optional source artifact lineage.

The validator enforces structural fields and hashes; it cannot judge physical correctness.

## Case record

Every case has:

- `case_id` and exactly one `split`: `extraction`, `boundary`, `holdout`, or
  `scientific_oracle`;
- `used_for_implementation`: `false` for every holdout case;
- `partition_ids`, `branch_selectors`, and `boundary_tags`;
- declared source input reference;
- genuine predecessor order/state reference, or a non-empty
  `predecessor_state_not_applicable_reason` for a pure stateless call;
- target-call input/pre-state reference;
- target output/post-state reference;
- RNG continuation, event order, rank/thread/scheduler metadata when applicable;
- process status plus `semantic_status`: `normal_completion`, `target_completed_outer_failure`,
  `expected_failure`, `source_failure`, or `capture_failure`. The target-local status requires a
  complete genuine target pre/post-state captured after the target returned and before the named
  outer failure; it may cover only that target mapping, never full-program completion.
  Such a case must also declare `claim_scope: target_local_mapping`, a non-empty
  `outer_failure_name`, and distinct `target_return_receipt_ref` and
  `outer_failure_receipt_ref` artifacts; both receipts must appear in `artifact_refs`.
- oracle/invariant references and the tolerance/metric they support;
- all referenced artifact paths.

Do not combine target input and target output in one opaque record. The source-free replay must be
able to consume the input/pre-state without reading the expected result.

## Artifact references

Each manifest artifact uses a bundle-relative, non-traversing path and a lowercase or uppercase
64-hex SHA-256. Record `role` from a small project vocabulary such as `source_input`,
`predecessor_state`, `target_input`, `target_output`, `branch_trace`, `oracle`, `log`, or
`derived_conversion`.

For a large array, record shape, dtype, axes, units, active extent, byte order, and storage order in
the artifact metadata. For Fortran arrays, state logical index base and memory/file order
separately. Never rely on filename or array shape to imply scientific identity.

## External producer payload receipt

When a case declares an external producer-to-consumer handoff, record an optional
`external_payload_receipt` in the case in addition to process and semantic status. It must state
the expected consumer contract and whether the producer emitted a consumable payload.

The receipt uses `expected_consumer_contract`, boolean `emitted`, `artifact_ref`, and boolean
`consumer_admissible`. An emitted payload also declares `declared_identity`, `type_or_schema`,
and `active_extent`. A non-emission instead declares
`classification: configuration_or_schema_need`; its `consumer_admissible` is `false` and its
`artifact_ref` identifies the absence receipt. Every `artifact_ref` also appears in the case
`artifact_refs` and the manifest artifact table.

- If `emitted` is `true`, reference the emitted artifact plus its declared identity, type/schema,
  active extent, and consumer admissibility. A successful producer process without this receipt
  does not cover consumer acceptance.
- If `emitted` is `false`, reference an absence receipt such as a post-run inventory or explicit
  producer status, set `consumer_admissible` to `false`, and classify the path as a producer
  `configuration_or_schema_need`. Keep it as a boundary record; never provide an empty, fallback,
  or unrelated file to the consumer merely to exercise the downstream path.

The receipt proves only this handoff for the declared producer configuration. It does not extract
the producer, establish arbitrary-input schema compatibility, or replace a consumer-side invalid-
input boundary case.

## Active extent and raw-storage residue

A captured buffer may contain both a declared logical result and bytes that no declared consumer
reads: alignment padding, inactive grid points, reused workspace, or uninitialized storage. The
case record and every relevant artifact must distinguish them.

- Declare the logical active extent and the consumer's access rule (for example an index range,
  mask, valid length, or selector-dependent slice).
- Compare the extracted relation to source values on that consumed extent. Preserve a separate
  raw-byte metric for the whole storage object; a mismatch outside the consumed extent is neither
  scientific parity nor automatically a defect.
- If byte-exact storage is a declared target, capture the predecessor workspace, initialization
  semantics, and source iteration/scheduling order as target-call input. An undefined or omitted
  predecessor is a `configuration_or_schema_need` or `cannot_complete` boundary, never an
  implicit asset input.
- Do not use a captured inactive residue as a fixture, a default value, or a reconstructed
  scientific producer. It remains evidence of a storage ABI only.

## Holdout isolation

Keep holdout case identity and input domain visible for coverage accounting, but do not expose its
target output to implementation work. If filesystem access cannot be isolated, enforce procedural
isolation: record the implementation freeze hash before revealing holdout outputs, then evaluate
without modifying the relation or tolerance. Any post-reveal change invalidates the old holdout;
generate a new holdout case.

## Minimal manifest example

```json
{
  "schema_version": "source-observation-dataset/v1",
  "dataset_id": "project-target-branch-v1",
  "purpose": "Recover the declared target-call state transition",
  "gap": {
    "classifications": ["configuration_or_schema_need", "validation_oracle_gap"],
    "statement": "Target pre-state is absent from ordinary final output",
    "target_mapping": "N4.state -> N4.rows_rhs",
    "owner": "scientific-runtime-dataset-construction"
  },
  "source": {
    "project": "project",
    "revision": "immutable-revision",
    "runtime": "source-image@sha256:digest",
    "probe_revision": "probe-revision",
    "semantic_markers": ["NORMAL_END"]
  },
  "conventions": {
    "units": {"state": "declared"},
    "axes": {"state": ["row", "column"]},
    "index_base": {"row": 1},
    "coordinates": {},
    "state_ownership": {"target_input": "source predecessor"},
    "serialization": "exact binary unless declared otherwise"
  },
  "coverage": {
    "required_partitions": ["interior", "lower_boundary", "upper_boundary"],
    "covered_partitions": ["interior", "lower_boundary"],
    "uncovered_partitions": ["upper_boundary"]
  },
  "cases": [
    {
      "case_id": "interior-001",
      "split": "extraction",
      "used_for_implementation": true,
      "partition_ids": ["interior"],
      "branch_selectors": {"mode": "interior"},
      "boundary_tags": [],
      "source_input_ref": "input-001",
      "predecessor_state_ref": "pre-001",
      "predecessor_state_not_applicable_reason": null,
      "target_input_ref": "target-in-001",
      "target_output_ref": "target-out-001",
      "process_exit_code": 0,
      "semantic_status": "normal_completion",
      "oracle_refs": ["target-out-001"],
      "artifact_refs": ["input-001", "pre-001", "target-in-001", "target-out-001"]
    }
  ],
  "artifacts": [
    {
      "artifact_id": "input-001",
      "path": "cases/interior-001/source_input.json",
      "role": "source_input",
      "format": "json",
      "size_bytes": 128,
      "sha256": "0000000000000000000000000000000000000000000000000000000000000000"
    },
    {
      "artifact_id": "pre-001",
      "path": "cases/interior-001/predecessor_state.npy",
      "role": "predecessor_state",
      "format": "npy",
      "size_bytes": 1024,
      "sha256": "0000000000000000000000000000000000000000000000000000000000000000"
    },
    {
      "artifact_id": "target-in-001",
      "path": "cases/interior-001/target_input.npy",
      "role": "target_input",
      "format": "npy",
      "size_bytes": 1024,
      "sha256": "0000000000000000000000000000000000000000000000000000000000000000"
    },
    {
      "artifact_id": "target-out-001",
      "path": "cases/interior-001/target_output.npy",
      "role": "target_output",
      "format": "npy",
      "size_bytes": 1024,
      "sha256": "0000000000000000000000000000000000000000000000000000000000000000"
    }
  ]
}
```

Replace the example sizes and hashes with captured values. Keep manifest-only planning drafts
outside this executable schema; the validator requires at least one captured case.
