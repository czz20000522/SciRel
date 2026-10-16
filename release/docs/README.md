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
