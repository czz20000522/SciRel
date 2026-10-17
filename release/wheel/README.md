# SciRel wheel version line

The authoritative version is the `project.version` field in `pyproject.toml` at the Git commit being built. The canonical current receipt is [`../CURRENT.json`](../CURRENT.json); this directory is a compatibility surface only. Do not create a per-version wheel record. Git history, tags, and short release notes identify prior versions, while the generated wheel remains outside the source-of-truth path.


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
`umask 022`. Compare those values with the canonical
tuple and run the platform receipt against that exact file before updating
`release/CURRENT.json`. The logical manifest reference is resolved only against
an explicitly supplied external artifact root; it never points into
`build/releases/` inside the checkout.
