---
name: scirel-review-preparation
description: Prepare a stable scientific development increment for final scientific review and release preparation, reusing evidence and omitting duplicate inputs from the review queue.
---

# Scientific Final Review Preparation

Use after D2 integrated and tested retained changes and relevant D3 evidence is available.
Humans make final approval decisions; routine development does not wait for them.
Follow the receiving project's review/publication policy and portable [stage boundaries](../../extraction/scientific-computation-asset-extraction/references/stage_boundary_contract.md).
Project-level D1 delivery and later D2/D3 work may have different owners and be weeks apart. Review the stable
retained increment and relevant application evidence; do not require each source operator/graph to travel through
its own complete pipeline. Project intake grouping does not turn human decisions into a project-wide lock.

## Route remaining work

- Missing exact documents: [canonical preparation](../scientific-asset-normalization/references/relation-page-contract.md).
- Scientific finding: [scientific-asset-correctness](../scientific-asset-correctness/SKILL.md); source-only gaps go to D1.
- Application interpretation or repeatability: [scientific-project-implementation](../../usage/scientific-project-implementation/SKILL.md).
- Upload/decision mechanics: [review handoff](../scientific-asset-normalization/references/human-review-handoff.md).

Separate unfinished Agent work from final human decisions before freezing this handoff. A generic pending-human
label must not hide unresolved failure triage, feasible correction or missing independent evidence. For rights
questions, first inspect attributable license terms against the exact shipped code/data/dependencies and intended
use; provide an evidence-backed recommendation, unmet conditions and the precise decision or permission still
needed. Agent analysis cannot create a rights-holder grant. Refer scope-specific blockers to the integration owner;
do not convert a publication restriction into a blanket stop on otherwise authorized technical work.

Do not repeat valid stage work just to make this handoff look independent.
For a confirmed source defect, first require the D2 correction and applicable validation to be complete;
a defect list is not the normal final-review deliverable. Use the existing
[correction disclosure](../../extraction/scientific-relation-implementation/references/scientific-correction.md#required-disclosure-at-the-current-stage)
to expose original observed behavior, independent error basis, exact implemented change, corrected results and
remaining limits in the bound human review page. Ask the expert to judge the supplied correction, not implement it.
An exceptional unrepairable/undetermined item remains separate with attempted investigation and a precise
missing decision; do not label repairable work as such merely because human review follows.

## Allocate review attention

Use [evidence-based review attention](../../extraction/scientific-operator-review/references/evidence_based_review_attention.md)
when preparing multiple AI review rounds and a large human queue. Separate supported package eligibility from
consequence/uncertainty-based attention. Resolve author self-check and independent challenge findings through
evidence, with targeted successor review where needed; neither repeated agreement nor high model confidence
closes a material contradiction. Apply the caller's requirement for a final decision on every retained candidate;
explicit batch confirmation can reduce reading effort without silently approving unreviewed items.
An operator/graph review page highlights scientific decisions and residual uncertainty. The usage manual
reorganizes the same canonical facts for tasks and APIs, retaining limits without copying review mechanics.

## Freeze the increment

Compare against the previous trusted version, or explicitly state none exists.
Include cumulative science and affected dependencies, not every development commit.
Bind actual code, tests, canonical documents and evidence to Git; bind any wheel/catalog actually built.
Register the frozen reviewable version through the receiving project's actual candidate mechanism when supplied;
a candidate entry does not imply approval. Keep successors linked without rewriting reviewed entries.
Completed review projections already carry candidate code and test evidence. Before release, verify each
approved revision against the solidified code, actual test results and distribution. Check the actual finalizer's
capabilities instead of assuming it performs that full binding.
Record Agent reviewer identity/version and findings separately from human approval.
Review prose explains the delta and references the canonical document.
Make that document the normal human reading surface. Provide a compact cumulative change summary only as needed;
code, tests and detailed evidence remain optional drill-down. Agent owners check their consistency before submission
and resolve ordinary intermediate choices. Do not create a second dossier or require humans to audit every raw log.

Keep reviewable retained units separate from dispositions for every input, using the receiving project's protocol.
Reuse/exact_duplicate/covered_by needs target version and scientific evidence, not a new review item
when no retained public contract changes. Partial overlap is not coverage.
A pure no-change batch ends as no_changes; it creates neither approval nor release.
A reused pending target stays pending.

Use the receiving project's submission mechanism after semantic work. Its structural check is not scientific proof.
Inspect its actual pending-review or no-change result and bind the real producing integration identity.
Submission scripts, API field names and schema namespaces belong to that implementation, not this method.
Before registering a pending candidate that embeds the selected canonical document, apply the process's UTF-8
document-binding check to the actual workflow output, including Unicode metadata. A clean console display or
structural pass is insufficient. A serialization/decoding mismatch needs a preserved predecessor and metadata
successor, not repeated scientific execution or another full review.

## Final decision

Uploaded versions stay fixed. Explicit successors preserve predecessors; no silent queued/approved mutation.
Agent review supports internal development, not human endorsement. Human approval covers only its exact
increment and dependency closure. Material changes need a new reviewed successor.
Publication still requires authority, license, dependency and release checks in the receiving project's process.
Only an authorized successful publication creates a released entry. Use the receiving project's version policy;
approval of a subset does not automatically establish a complete dependency-closed release.
