# Normalization output contract

Produce an integrated development candidate and one disposition per input, without conferring approval.

## Input accounting

Record reuse, duplicate/covered target, retained change, conflict or unresolved relation with scientific evidence,
exact compared versions and source lineage. Partial overlap is not equivalence; names, hashes and samples alone
cannot justify absorption.

The optional input_dispositions in scirel.standardization-submission.dev carries reuse/exact_duplicate/covered_by,
source_asset_ids, target_asset_id, target_ref, target_digest and evidence. Target bindings identify the actual
comparison. review_units plus input_dispositions cover each input exactly once. Pending targets remain pending;
do not hide uncertainty as a no-change decision.

## Retained changes

Implement/test in the owned development branch; public imports and internal development wheels are allowed.
Stable retained changes receive one [canonical document](relation-page-contract.md).
Review prose explains the delta. Final review units bind document, code/patch or genuine no-code rationale,
tests, dependencies and evidence. Pure duplicates generate neither review units nor new formal documents.

## Completion

Freeze exact versions, dispositions, tests, limits and actual wheel/catalog. Inherited evidence keeps its original
conditions; changed behavior receives affected validation. A no-change batch completes without review/release.
Unresolved branches stay explicit while independent work proceeds. Use [review handoff](human-review-handoff.md)
for final approval preparation.
