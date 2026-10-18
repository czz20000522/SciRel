---
name: scirel-review-preparation
description: Prepare a stable D2 scientific development increment for final human review and release preparation, reusing exact evidence and exposing unresolved decisions.
---

# SciReL final review preparation

Use the shared operating contract already loaded for this task mode. If it is
not loaded, read [the shared operating contract](../../references/scirel-development-core.md)
once before proceeding; do not reload it for each routed sub-skill.
Use after D2 has integrated retained changes and relevant D3 evidence exists. Humans decide endorsement and
publication; this skill prepares a truthful review surface and cannot approve, grant rights or publish.

## Route and freeze

- Missing exact documents: [relation page contract](../scientific-asset-normalization/references/relation-page-contract.md).
- Scientific finding or correction: [asset correctness](../scientific-asset-correctness/SKILL.md); source-only gap goes to D1.
- Application interpretation/repeatability: [project implementation](../../usage/scientific-project-implementation/SKILL.md).
- Upload/decision mechanics: [human review handoff](../scientific-asset-normalization/references/human-review-handoff.md).

1. Bind the stable candidate, dependency/runtime identities, retained denominator, D2 checks and relevant D3
   application receipts. Reuse attributable evidence; do not repeat valid D1 work or require one full pipeline per
   operator.
2. Separate unfinished Agent work, scientific failures, missing independent evidence, rights/licence constraints,
   human decisions and release checks. `pending_human` must not hide a repairable defect or missing oracle.
3. For a confirmed source defect, require D2 successor correction and validation before asking an expert to judge it.
   Use [correction disclosure](references/scientific-correction.md#required-disclosure-at-the-current-stage)
   with original observation, independent basis, exact change, before/after result and remaining limits.
4. Build the human reading surface from exact contracts and evidence: scope/assumptions/gaps, capability/port map,
   actual checks and claim ceiling. Keep raw logs and internal paths as linked drill-down, not duplicated prose.
5. Return review packet, exact hashes, rights questions, unresolved decisions, next owner and reopen conditions.
   `no_changes` creates neither approval nor release. Only an authorized successful publication creates a release.
