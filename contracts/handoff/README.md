# Receiving external decomposition results

## Authority: `decomposition/FINAL/FINAL.json`

The only authoritative external handoff is a project's `decomposition/FINAL/`
directory, described by `scirel.project-final.v1`:

```text
<project>/decomposition/FINAL/
  FINAL.json        # authoritative description and bounded claim
  FILES.json        # payload membership manifest: every payload file + sha256
  PATH_MAP.json     # stored-member aliases; no duplicate payload copy
  ROOT.sha256       # binds FINAL.json + FILES.json + PATH_MAP.json
  d0/ d1/ d2/ d3/   # stage payloads (layout may vary by project)
  evidence/ recovery/   # retained evidence and recovery material
```

`FINAL.json` declares `files`, `path_map`, `root_binding`, `payload_files`,
`payload_bytes`, `decomposition_scope`, `limitations`, `claim_ceiling`,
`evidence_policy` and `custody_note`; it may also carry `identity`,
`stage_evidence`, `capabilities`, `operators`, `task_graphs`, `license` and
`platform_boundaries`.

The contract is defined and validated by the external decomposition-method
bundle (`contracts/project-final.schema.json`, `contracts/files.schema.json`,
`contracts/ROOT.sha256.md`, `scripts/validate_final.py`). SciRel accepts only
this FINAL contract for a new external delivery; older project-specific FINAL
schemas are historical evidence, not accepted successors.

### Self-binding

The manifest binds bytes, and the control files bind the manifest:

```text
FILES.json      lists every payload file and FINAL.json + PATH_MAP.json
ROOT.sha256     binds FINAL.json, FILES.json and PATH_MAP.json
FINAL.json      binds FILES.json and PATH_MAP.json by fixed names
```

A receiver must verify all three directions. `FILES.json` alone is not
sufficient: changing `FINAL.json` would otherwise leave every payload digest
intact.

### Licence records

Open-source sourcing removes the redistribution gate, but not attribution.
Each FINAL records `license.spdx`, the retained notice paths and the licence
bytes; licence files are ordinary payload members in `FILES.json`.

## Receiving procedure (SciRel side)

1. Run the external `validate_final.py` on the FINAL directory (structure,
   payload bytes, control-file binding). Record `NOT_RUN` when that validator or
   a required payload is unavailable; a structural pass is not scientific
   acceptance.
2. Compare each delivered capability with the current catalog and write an
   **overlap record**. This is a record of overlap, not an admission or merge
   decision.
3. A library change, if any, is a separate usage-side decision with its own
   implementation, tests, contract and evidence. It is not part of accepting the
   decomposition result.

### Overlap record

`overlap-record.schema.json` records, per incoming capability:

```json
{
 "incoming_capability_id": "acme.transport.foo",
 "overlap": "same-relation | convention-only | wider-coverage | none",
 "matched_asset_ids": ["scirel.kinetic.foo"],
 "difference_note": "same relation; naming and units differ; no new coverage",
 "evidence": ["contract comparison", "numeric probe"]
}
```

Rules: `none` has no matches; the other three require matches. Convention-only
differences (units, weights, names, failure wording with the same numerical
relation) are recorded, never treated as defects. The record makes no
`capability_gain` claim and carries no `required_changes` or merge
authorization.

`scripts/validate_overlap_record.py <record.json>` validates the record shape
and the match/overlap consistency.

## Optional internal stage records

`d0-package.schema.json` … `d3-package.schema.json` remain as optional internal
records for producers that want layer-level traceability. They are **not** the
handoff interface and are not required for a FINAL delivery. Real FINAL
deliveries use the project's own stage reports; absence of these layer packages
is not a nonconformance. `scripts/validate_handoff.py` validates them only when
a producer chooses to emit them.

## User-facing boundary

The user sees only the installable SciRel package, its tests and the bilingual
manual. FINAL records, overlap records, stage reports and merge decisions never
enter the package or the manual.
