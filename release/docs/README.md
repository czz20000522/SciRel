# SciRel documentation version line

Documentation is generated from the same Git commit as the candidate wheel. The current checkout and its exact documents are the source of truth; Git history, tags, and short release notes carry prior wording and API history. The canonical current binding is [`../CURRENT.json`](../CURRENT.json). Do not copy a complete documentation tree or add a per-version documentation record just to record a candidate.


Documentation evidence is maintained separately from wheel evidence so wording,
examples, and navigation can evolve without rebuilding runtime bytes. The
current documentation pointer must still bind one exact wheel version and its
complete document closure: the selected records, handbook asset IDs, and
operator/task-graph counts must equal the wheel record. A documentation change
that adds a capability requires a new wheel-bound selection in the same release
workflow; it must not silently make the documentation line broader than the
installed wheel. Git history records revisions instead of keeping duplicate
copies of the same document set.
