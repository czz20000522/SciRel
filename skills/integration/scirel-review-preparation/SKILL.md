---
name: scirel-review-preparation
description: Prepare a stable SciRel development increment for final scientific review and release preparation, reusing evidence and omitting duplicate inputs from the review queue.
---

# SciRel Final Review Preparation

Use after D2 integrated and tested retained changes and relevant D3 evidence is available.
Humans make final approval decisions; routine development does not wait for them.
Follow the [workflow requirement](../../../docs/requirements/scirel-workflow.md).

## Route remaining work

- Missing exact documents: [canonical preparation](../scientific-asset-normalization/references/relation-page-contract.md).
- Scientific finding: [scientific-asset-correctness](../scientific-asset-correctness/SKILL.md); source-only gaps go to D1.
- Application interpretation or repeatability: [scientific-project-implementation](../../usage/scientific-project-implementation/SKILL.md).
- Upload/decision mechanics: [review handoff](../scientific-asset-normalization/references/human-review-handoff.md).

Do not repeat valid stage work just to make this handoff look independent.

## Freeze the increment

Compare against the previous trusted version, or explicitly state none exists.
Include cumulative science and affected dependencies, not every development commit.
Bind actual code, tests, canonical documents and evidence to Git; bind any wheel/catalog actually built.
Register the frozen reviewable version through SciRel's release index when that development path exists;
the candidate entry does not imply approval. Keep successors linked without rewriting reviewed entries.
Completed review projections already carry candidate code and test evidence. Before release, verify each
approved revision against the solidified code, actual test results and wheel; the current single-draft
finalizer does not perform that full binding.
Record Agent reviewer identity/version and findings separately from human approval.
Review prose explains the delta and references the canonical document.
Make that document the normal human reading surface. Provide a compact cumulative change summary only as needed;
code, tests and detailed evidence remain optional drill-down. Agent owners check their consistency before submission
and resolve ordinary intermediate choices. Do not create a second dossier or require humans to audit every raw log.

Use review_units plus input_dispositions in the [submission contract](../../../contracts/standardization-submission-dev.schema.json).
Reuse/exact_duplicate/covered_by needs target version and scientific evidence, not a new review item
when no retained public contract changes. Partial overlap is not coverage.
A pure no-change batch ends as no_changes; it creates neither approval nor release.
A reused pending target stays pending.

Use scripts/submit_standardization.py after semantic work. Its structural check is not scientific proof.
Inspect the actual review_pending or no_changes result. The current API binds the D2 scirel-integration producer
identity; do not substitute this router's digest for it.
Before registering a pending candidate that embeds the selected canonical document, apply the process's UTF-8
document-binding check to the actual workflow output, including Unicode metadata. A clean console display or
structural pass is insufficient. A serialization/decoding mismatch needs a preserved predecessor and metadata
successor, not repeated scientific execution or another full review.

## Final decision

Uploaded versions stay fixed. Explicit successors preserve predecessors; no silent queued/approved mutation.
Agent review supports internal development, not human endorsement. Human approval covers only its exact
increment and dependency closure. Material changes need a new reviewed successor.
Publication still requires authority, license, dependency and release checks in the [process](../../../docs/development-process.md).
Only a successful release creates a released index entry; converge related development versions and contracts
to v1 before the first formal release.
Current single-draft fixtures do not automatically promote arbitrary approved item subsets to a complete release.
