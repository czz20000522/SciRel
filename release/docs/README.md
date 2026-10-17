# SciRel documentation selection

Documentation is generated from the same Git commit as the candidate wheel. The current checkout and its exact documents are the source of truth; Git history, tags, and short release notes carry prior wording and API history. The canonical handbook source is [`../../tools/docs/handbook.json`](../../tools/docs/handbook.json); a smaller release selection is projected in memory during the external build. The canonical current binding is [`../CURRENT.json`](../CURRENT.json). Its `selection_id` identifies the selected document set; it is not a second package version. Do not copy a complete documentation tree or add a per-version documentation record just to record a candidate.


Documentation evidence is maintained separately from wheel evidence so wording,
examples, and navigation can be reviewed independently while remaining in the
same Git candidate. The current documentation pointer must bind one exact wheel
version and its complete document closure: the selected records, handbook asset
IDs, and operator/task-graph counts must equal the wheel record. Any documentation
change that is carried forward requires a new Git-bound candidate and refreshed
receipt; the wheel bytes may remain identical, but the source revision and
document selection must be explicit. Git history records revisions instead of
keeping duplicate copies of the same document set.

The current tuple stores a logical external documentation `manifest_ref`, its
manifest digest, and the snapshot digest/byte count. The rendered snapshot and
its nested manifest are validated only when
`validate_release_alignment.py --artifact-root <root>` is given; the Git tree
does not retain a generated per-version documentation directory.

Build a snapshot from an exact source ref with
`scripts/build_scirel_docs_from_ref.py`. It archives the ref, invokes the
archived `scripts/scirel_docs.py` with the explicit source revision, and writes
the snapshot plus `build-manifest.json` outside the checkout. A dirty checkout,
an unbound snapshot, or a candidate invocation without `--selection` is
rejected. The helper verifies each selected record digest and implementation
version, filters the archived Chinese reader bundles to the same asset set,
and materializes the exact set only in its temporary build directory.
Its manifest uses the same `scirel.build-inputs.v1` binding as the wheel build:
the archived project metadata, lock file, license set, and both documentation
build helpers are summarized alongside the snapshot. This keeps wheel and
documentation outputs tied to one Git source without copying a versioned
handbook into the repository.
The `--documents` path remains authoritative when `--selection` is supplied:
selection records may use a path relative to that directory or a full
repository-relative path, but records outside the requested directory are
rejected.
Use an absolute interpreter path when selecting a virtual environment so the
archived build retains that environment's documentation dependencies:

```sh
python scripts/build_scirel_docs_from_ref.py \
  --ref "$ref" \
  --selection provenance/selections/scientific-core-documents-20261017-dev9.json \
  --output-dir "$tmp_docs"
```
