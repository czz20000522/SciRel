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

Build a snapshot from an exact source ref with
`scripts/build_scirel_docs_from_ref.py`. It archives the ref, invokes the
archived `scripts/scirel_docs.py` with the explicit source revision, and writes
the snapshot plus `build-manifest.json` outside the checkout. A dirty checkout
or a snapshot built from the current directory without an explicit ref is not a
candidate document artifact. For a release candidate, pass the
project-relative selected-document-set manifest as well; the helper verifies
each record digest and materializes the exact set only in its temporary build
directory:

```sh
python scripts/build_scirel_docs_from_ref.py \
  --ref "$ref" \
  --selection provenance/selections/scientific-core-documents-20261017-dev9.json \
  --output-dir "$tmp_docs"
```
