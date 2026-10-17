# SciRel documentation selection

Documentation is generated from a Git commit that is explicitly bound to a candidate
wheel. The current checkout and its exact documents are the source of truth; Git
history, tags, and short release notes carry prior wording and API history. The
canonical handbook source is [`../../tools/docs/handbook.json`](../../tools/docs/handbook.json);
a smaller release selection is projected in memory during the external build. The
canonical current binding is [`../CURRENT.json`](../CURRENT.json). Its `selection_id`
identifies the selected document set; it is not a second implementation version. Do
not copy a complete documentation tree or add a per-version documentation record just
to record a candidate.


Documentation evidence is maintained separately from wheel evidence so wording,
examples, and navigation can be reviewed independently while remaining in the
same Git candidate. The current documentation pointer must bind one exact compatible
wheel version and its complete document closure: the selected records, handbook asset
IDs, and operator/task-graph counts must equal the wheel record. Every selected record's
`implementation_version` remains the exact compatible wheel version.

The wheel and documentation share a public `major.minor` release line. The wheel's
patch/development suffix identifies the implementation candidate; documentation may
carry a separate `documentation.version` editorial revision on the same line. A wording, navigation, or
translation correction can therefore create a new documentation revision while the
wheel implementation version and resulting bytes remain unchanged. The wheel is still
rebuilt/rebound from the new Git commit, and the record must retain `compatible_wheel`,
that exact source revision, and both selection/snapshot digests. This is a documentation
release, not a new implementation release.

Any change to a scientific contract, public API, default, failure behavior,
applicability, dependency, or graph composition requires a new wheel candidate and a
new document selection from the same source revision. Such a change cannot be hidden
in an editorial document revision, and a documentation revision cannot add a capability
that is absent from the wheel closure.

Any documentation change that is carried forward requires a new Git-bound document
receipt. The wheel bytes may remain identical only under the editorial rule above; the
new source revision and document selection must still be explicit. Git history records
revisions instead of keeping duplicate copies of the same document set.

The wheel itself may also advance by a patch or development maintenance revision on the
same public release line. That creates a new wheel candidate and document selection: the
exact `compatible_wheel` and every document's `implementation_version` move with the
new wheel, while an editorial `documentation.version` may continue independently on the
same line. A PEP 440 `post` revision is reserved for packaging or metadata correction of
an existing version.

The current tuple stores a logical external documentation `manifest_ref`, its
manifest digest, and the snapshot digest/byte count. The rendered snapshot and
its nested manifest are validated only when
`validate_release_alignment.py --artifact-root <root>` is given; the Git tree
does not retain a generated per-version documentation directory.

When an editorial documentation revision is introduced, its external manifest and
current tuple must expose both the exact `compatible_wheel` and a distinct
`documentation.version` identity. The latter stays on the same release line and
does not replace `project_version`/`implementation_version`; those fields continue to
bind every document to the installed implementation. The validator must reject a
revision whose release line differs from the compatible wheel or whose closure/counts
exceed the wheel binding.

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
