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

`payload_files` is exactly the number of `FILES.json.files` entries.
`payload_bytes` is the sum of their actual byte lengths. Both include
`FINAL.json` and `PATH_MAP.json`; both exclude `FILES.json` and `ROOT.sha256`.
Because `FINAL.json` includes its own contribution to that sum, the producer
stabilizes its serialized length before hashing it. Producers must not guess
these values or compute them from a different JSON serialization.

Payload entries use case-sensitive relative POSIX-string sorting. The root
binding uses the fixed `FINAL.json`, `FILES.json`, `PATH_MAP.json` order defined
in [ROOT.sha256.md](ROOT.sha256.md). It does not use alphabetical sorting.

## Author a new submission

The producer needs an existing payload directory and a metadata JSON document.
Metadata supplies only `project_id`, `decomposition_scope`, `limitations`,
`claim_ceiling`, `evidence_policy`, `custody_note`, `license`, and any applicable
optional fields in `project-final.schema.json`. The producer owns `schema`,
`files`, `path_map`, `root_binding`, `payload_files`, and `payload_bytes`;
supplying these derived keys in metadata is an error.

```text
python scripts/prepare_admission.py --payload <payload-directory> --metadata <metadata.json> --output <new-FINAL-directory>
python scripts/validate_admission.py <new-FINAL-directory> --output <outside-FINAL-report.json>
```

The producer copies the payload into a new directory and generates all four
control files. It never changes the input or overwrites an existing output.
The payload root must not already contain those control files. A failed new
output is reported for inspection; it is not silently repaired or deleted.
Keep reports outside the submission so that validation cannot introduce an
unlisted file into the closed inventory.

[examples/minimal-partial](examples/minimal-partial/README.md) is a complete
format-only input, including metadata, payload and a command that generates a
valid submission. Its structural result makes no scientific qualification claim.
The same command handles a partial source slice: describe its exact scope,
limitations and unexecuted stages in the metadata and evidence. No separate
partial schema or completion flag is required.

### Stored-member aliases

`PATH_MAP.json` is an object mapping a logical relative POSIX alias to one
directly stored non-control payload member. With no aliases it is exactly
`{}\n`. To supply aliases, add `--path-map <aliases.json>` to the producer command.

An alias must not be a real stored member, a control-file name, or an identity
mapping. Its target must be an existing non-control `FILES.json` member.
Alias chains, missing targets, duplicate JSON keys and payload copies created
only to implement an alias are not admitted. Aliases denote files: one alias
cannot be nested under another file alias or any stored file, including the
outer-bound control files. Paths must be canonical portable
relative POSIX names: no drive/UNC/absolute paths, backslashes, empty/dot/parent
segments, control characters, Windows forbidden filename characters
`<>:"|?*`, reserved device names or filename normalization collisions.
The portability boundary follows the
[Windows file naming rules](https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file)
as well as the relative POSIX path constraints.
The schema is [path-map.schema.json](path-map.schema.json); target existence
and closed-inventory constraints are enforced by the validator.

## Supply the public tools to an external worker

```text
python scripts/export_admission_tools.py --output <new-tools-directory>
```

The exported directory contains these same public schemas, documentation,
example, producer and validator, with member identities. It preserves the
`scripts/` and `contracts/admission/` relative layout and runs from an unrelated
working directory with Python 3.10 or later and its standard library. It needs
no package installation or scientific runtime. It contains no scientific
library implementation, catalog, private skill, source checkout or task history.
The running party provides this bound tool directory to the worker alongside
its source and method. A worker does not need receiver-private code or a chat
answer to infer the protocol.

Before a long extraction, use the included minimal example to verify that the
actual supplied tools can prepare and validate a submission. At handoff, run
the same tools against the actual payload. Missing or conflicting interface
inputs produce a machine-readable failure or `NOT_RUN` with a concrete cause;
they do not authorize inventing a second format or claiming scientific success.

## Validate

```bash
python scripts/validate_admission.py <FINAL directory> [--emit-root] [--output report.json]
```

Exit codes: `0` all executed checks pass; `1` a check fails; `2` a required input
is absent, so the check is NOT_RUN rather than passing.

The standard-library validator reads the three supplied live schemas and
implements the finite set of keywords they declare. An unsupported keyword or
schema definition fails closed. This is a validator for this admission
interface, not a general JSON Schema implementation.

A structural pass is not scientific acceptance. After admission, SciRel's own
reception rules (`contracts/reception/`) decide overlap recording and whether
any library change happens. Stage D0-D3 standards belong to decomposition
skills; SciRel does not define or require them.
