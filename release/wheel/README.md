# SciRel wheel version line

The authoritative version is the `project.version` field in `pyproject.toml` at the Git commit being built. The canonical current receipt is [`../CURRENT.json`](../CURRENT.json); this directory is a compatibility surface only. Do not create a per-version wheel record. Git history, tags, and short release notes identify prior versions, while the generated wheel remains outside the source-of-truth path. A `*.devN` version may span several development commits; the external artifact path and manifest must include the exact commit so each build remains immutable.


The canonical tuple contains the one wheel currently bound by this checkout.
Its artifact record contains an external `manifest_ref`, the manifest digest,
exact wheel SHA-256 and byte size, source revision and selected capability closure. Older wheel files are not a required working-tree
asset: Git history is the version history, and a prior wheel must be restored
from its recorded digest or external evidence when it is needed for an audit.
Do not copy every historical wheel into the repository.

The package layout is described by [`layout.json`](layout.json). The current
wheel pointer also binds the compatible documentation record and exact
operator/task-graph/document counts. Scientific
implementations are organized by domain package, and the wheel exposes those
domain paths directly. Legacy top-level module paths are intentionally absent;
callers must import from the owning domain package. Tests, provenance,
decomposition assets, and development tooling are outside the wheel intake.

Native runtime resources have one source-side closure at
[`native-resource-closure.json`](native-resource-closure.json). It enumerates
the 117 files currently included by `package-data`, grouped by capability and
external runtime. Run `python scripts/validate_native_resource_closure.py` for
a source-only check, or add `--wheel <path>` to prove that an actual wheel has
exactly the declared native members. The closure is an inventory and future
split boundary; it does not grant a platform or scientific release claim.

The PDRK package-data binding names the five reviewed resource roots explicitly
(`current`, `examples`, `finiteN`, `legacy`, and the shared plot helper). It
does not use a catch-all `_native/**/*` pattern, so a new native file must first
be added to the reviewed closure before it can enter a wheel. The resulting
wheel still contains the same 117 resources; this only makes the source-side
split boundary fail closed.

## Reproducing the bound wheel

Build from the exact `source_revision` recorded in [`../CURRENT.json`](../CURRENT.json),
never from a dirty checkout. The reproducible procedure mirrors SciPy's ref-bound
release tooling: archive that Git ref into a clean temporary directory, then run
`uv build --wheel` there with `SOURCE_DATE_EPOCH` set to the ref's commit time.
The repository includes `scripts/build_scirel_from_ref.py`, which performs this
archive-and-build sequence and writes a stable `build-manifest.json` beside the
wheel. Its output directory must be outside the checkout so a build cannot
silently become another versioned source asset. For a POSIX shell:

```sh
ref=<40-character-source-revision>
tmp_wheels=$(mktemp -d)
python scripts/build_scirel_from_ref.py --ref "$ref" --python 3.14 --output-dir "$tmp_wheels"
```

Git-archive extraction gives the source files one stable timestamp; setting the
epoch alone in a working tree is insufficient because build backends may preserve
file mtimes. The helper also normalizes regular-file and directory modes before
building, so a host tar umask cannot change wheel ZIP permission attributes. It
records the full source revision, project version, wheel byte count and SHA-256 in
its manifest, and fixes `PYTHONHASHSEED=0` alongside `SOURCE_DATE_EPOCH` and POSIX
`umask 022`. Compare those values with the canonical tuple and run the platform
receipt against that exact file before updating `release/CURRENT.json`. Build the
source commit first and update the coordination tuple in a later commit; the
tuple cannot self-reference the commit that contains it. The logical manifest
reference is resolved only against an explicitly supplied external artifact
root; it never points into `build/releases/` inside the checkout.

The manifest also carries a `scirel.build-inputs.v1` summary for the archived
`pyproject.toml`, optional `uv.lock`, declared license files, and the exact
build helper files. When the source checkout is available, the release
validator compares those summaries with Git blobs at the recorded commit; a
dirty helper remains explicit in the receipt instead of being presented as
source-only reproducibility.

## Offline wheelhouse acceptance

The ordinary Linux receipt may install runtime dependencies from a network
resolver while preparing its clean environment. That is useful for an initial
platform smoke, but it does not prove that a consumer can reproduce the
installation without network access. For that stronger check, prepare a
platform-specific wheelhouse outside this checkout and run
`scripts/validate_offline_wheelhouse.py` against the exact wheel:

```sh
python -I scripts/validate_offline_wheelhouse.py \
  --expected-platform linux-x86_64-cp314 \
  --source-revision <40-character-source-commit> \
  --wheel /artifacts/scirel-<project.version>-py3-none-any.whl \
  --wheelhouse /artifacts/linux-x86_64-cp314-wheelhouse \
  --lockfile /path/to/uv.lock \
  --output /artifacts/linux-x86_64-cp314-offline-validation.json
```

The runner creates a temporary clean venv and invokes pip with
`--no-index --only-binary=:all: --find-links <wheelhouse>`. It then runs the
installed-wheel validator inside that venv. A passing receipt therefore binds
the wheel digest, every wheelhouse member digest, the target interpreter and
the installed scientific smoke checks. Missing or source-only dependencies
remain a failed receipt; do not turn a network-backed receipt into an offline
claim by editing its limitations. If `--source-revision` is omitted, the
receipt remains a standalone technical record. Supplying the exact commit lets
the release alignment validator verify the receipt against the current wheel.
Passing `--lockfile uv.lock` also binds the wheel's PEP 508 metadata to the
locked direct and transitive dependency closure and records platform-tag
compatibility for every wheelhouse member. A shared wheelhouse may contain the
union of core and optional-extra wheels; the receipt reports unneeded members
for each selected closure without treating that reusable superset as a failure.
For the dev9 receipt, the Linux platform receipt collected for that candidate combines the existing same-source
rebuild evidence with the offline validation result; the raw network and offline
receipts remain separate lineage records. A passing offline check still does
not establish complete scientific capability closure or release approval.
