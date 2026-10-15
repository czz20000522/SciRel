---
name: scientific-computation-asset-extraction
description: Prepare a versioned source project in D0 and coordinate complete, source-faithful D1 extraction into source-free operators and TaskGraphs; diagnose existing extraction read-only.
---

# Scientific computation asset extraction

Read [the shared operating contract](references/scirel-skill-core.md) first. This entrypoint is the D0/D1
coordinator; it owns project scope, denominator, worker integration and the immutable handoff. It does not own
D2 scientific correctness, D3 application acceptance, human approval, rights or release.

## Trigger and route

| Request | Load one reference / route |
| --- | --- |
| inspect progress or an existing handoff | [progress diagnosis](references/progress_diagnosis.md), read-only |
| prepare or freeze source | [material access and preprocessing](references/material_access_and_preprocessing.md#d0-source-preparation) |
| decide operator/TaskGraph/support/disposition | [asset projection decision](references/asset_projection_decision_manual.md) |
| map source framework or physics | [source framework method](references/source_framework_production_manual.md); physics manual only if needed |
| implement one source-backed relation | [relation implementation](../scientific-relation-implementation/SKILL.md), `source_fidelity` |
| compare source and candidate | [computation validation](../scientific-computation-validation/SKILL.md), `source_fidelity` |
| recover hidden state or missing observations | [source-free playbook](references/source_free_extraction_playbook.md), then runtime dataset construction |
| review fidelity/completeness | [operator review](../scientific-operator-review/SKILL.md), `source_fidelity` |
| package/load a bundle | [intake directory contract](references/intake_directory_contract.md) |
| run an external worker or close FINAL | [external run and FINAL gates](references/external-run-and-final-gate.md) |
| repeated work or evidence invalidation | [workflow optimization](references/workflow_optimization.md) |

Do not preload the references in the table. A specialist returns a bounded candidate or evidence; the coordinator
owns integration and never self-approves independent review.

## D0 then D1

1. Keep official upstream read-only. In an owned workcopy, build or reuse the source index, record upstream
   delta and retained entrypoints, and freeze a digest-bound D0. D0 preparation is not scientific qualification.
2. Bind D1 to that exact D0. Map the complete frozen-D0 capability denominator, material branches, state/order,
   terminal outputs and source failures. A partial pilot must declare its narrower denominator and cannot be called
   project completion.
3. Partition by scientific relation and target path, not file count. Workers use private writes and scoped material;
   one integrator assembles the candidate. Verify actual runner/model/material access before dispatch and preserve
   prompt, session, stdout/stderr and resumable output. A process or compact report is not a FINAL artifact.
4. Implement or wrap source behavior with the smallest interface/dependency change. Use `source_fidelity`: the
   frozen D0 is the oracle, including reproducible defects. Record source issues for D2; repair only introduced
   extraction/interface defects here.
5. Close the full denominator with attributable package, source-free, source-comparison and composition evidence,
   including material branch/state/failure cases. Preserve uncovered scope and `NOT_RUN`; never shrink cases,
   loosen tolerances or overwrite frozen evidence.
6. Save a durable handoff containing exact bundle/dependency/runtime identities, source mapping, evidence hashes,
   claim ceiling, limitations, next D2 owner and reopen condition. Formal asset documents belong after D2 stability.

## Failure and output

Classify each issue as source behavior, extraction defect, runtime/dependency, evidence gap or owner decision.
Keep the original error and exit status; a checker repair creates a successor receipt and reruns only affected
comparisons. Return the shared contract's compact handoff with `covered/failed/blocked/NOT_RUN/inapplicable` counts.
D1 completion means source fidelity/completeness only; it is not correctness, endorsement or release.
