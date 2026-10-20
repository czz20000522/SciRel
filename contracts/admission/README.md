# SciRel admission standard

This directory is the **only external interaction surface** of SciRel. It is the
equivalent of a repository's pull-request interface: a decomposition result is
not received because it is scientifically interesting, but because its submitted
bytes satisfy this standard.

## Submission

A submission is one project's:

```text
<project>/decomposition/FINAL/
  FINAL.json        # scirel.project-final
  FILES.json        # scirel.final-files: every payload member + bytes + sha256
  PATH_MAP.json     # stored-member aliases; no duplicate payload copy
  ROOT.sha256       # binds FINAL.json, FILES.json and PATH_MAP.json
  d0/ d1/ d2/ d3/   # stage payloads (layout is the producer's choice)
  evidence/ recovery/
```

FINAL.json carries `project_id`, `decomposition_scope`, `limitations`,
`claim_ceiling`, `files`, `path_map`, `root_binding`, `payload_files`,
`payload_bytes`, `evidence_policy`, `custody_note` and `license`.
The license record is `spdx` plus retained NOTICE reference paths; attribution
bytes are payload members and must appear in FILES.json.

There is no version suffix in the schema identifiers. The contract evolves by
Git history and breaking changes; do not mint `scirel.project-final.v1`-style
names. Existing artifacts with version-suffixed schemas are not admitted.

## Binding

```text
FILES.json     lists every payload member + FINAL.json + PATH_MAP.json
ROOT.sha256    binds FINAL.json, FILES.json and PATH_MAP.json
FINAL.json     binds FILES.json and PATH_MAP.json by fixed names
```

`FILES.json` does not list itself or `ROOT.sha256`; the outer binding covers
them. All three directions are checked by the admission validator.

## Validate

```bash
python scripts/validate_admission.py <FINAL directory> [--emit-root] [--output report.json]
```

Exit codes: `0` all executed checks pass; `1` a check fails; `2` a required input
is absent, so the check is NOT_RUN rather than passing.

A structural pass is not scientific acceptance. After admission, SciRel's own
reception rules (`contracts/reception/`) decide overlap recording and whether
any library change happens. Stage D0-D3 standards belong to decomposition
skills; SciRel does not define or require them.
