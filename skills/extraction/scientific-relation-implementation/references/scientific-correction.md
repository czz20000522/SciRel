# Critical source review and scientific correction

Use this protocol when source inspection, runtime observations, validation, or read-only review exposes a
possible source error and the caller authorizes correctness repair. Source is evidence of behavior,
not scientific authority. Preserve the original snapshot for evidence; do not preserve a known wrong
relation as the default usable asset.

## Skill group and handoffs

The group has four core responsibilities plus conditional source observation. It is not a requirement
to run five agents or load every skill for every operator.

| Skill | Responsibility | Handoff |
| --- | --- | --- |
| `scientific-computation-asset-extraction` | Identify complete scientific mappings, graph boundaries, source scope and delivered contracts | Concrete relation/defect, affected nodes and ports |
| `scientific-relation-implementation` | Derive and implement the justified correction | Changed relation, code, assumptions and impact |
| `scientific-computation-validation` | Independent oracle, meaningful tests, numerical and terminal-state verification | Actual metrics and separately bounded claims |
| `scientific-operator-review` | Read-only challenge of the submitted revision and sufficiency of evidence | Advisory findings for the exact scope; never stage completion or approval |
| `scientific-runtime-dataset-construction` | When needed, recover missing source state and record genuine before/after observations | Immutable observations, failure case and held-out inputs; never truth by itself |

Cycle through the relevant owners until the known defect is repaired and validated, or a specific
unresolved scientific decision is established. Implementation must not self-approve; review cannot edit
its target in place. These are role boundaries, not automatic permission to spawn agents.

## Establish whether it is an error

Compare implementation with the governing relation and declared convention: units/scaling, signs,
coordinates/axes, normalization, conservation/limits, boundary rules, discrete convergence and state
lifecycle. Derive a counterexample or independent expected property. Different conventions or models
are not defects unless they contradict the declared mapping. A paper may also contain a typo or an
inconsistent reduction: explain the derivation, not merely “the paper says so.”

Distinguish an observed source defect, an introduced extraction defect, an unverified historical claim,
and an unresolved model choice. Attribute “source error” only to an implementation actually inspected
or observed. A missing source file must not be used to invent its contents or a failing source run.

When the error and correction are clear, fix the candidate under the authorized correctness/repair scope.
Do not defer demonstrable dimensional, sign, index, false-convergence, or invalid-value handling defects to
an unspecified later decision. When the expected physics cannot be determined, state the missing choice;
do not hide it with a clamp, zero fill, guessed closure or narrower undocumented domain.

## Implement and verify

1. Preserve the original observation, input and revision when available; record a reproducible failure
   or a derivation that exposes the defect. Keep development diagnostics distinct from held-out evidence.
2. State the corrected relation and expected difference before evaluating the acceptance case. Change
   the smallest coherent implementation, contract and dependent graphs. Do not edit the source baseline
   or overwrite a previously frozen candidate.
3. Route shape/interface restoration through the existing controlled-repair protocol; label it
   `source_repaired` unless independent science supports a stronger claim. Equation, physical boundary,
   normalization or model corrections require independent evidence and a `scientifically_corrected` claim.
4. Validate the unaffected domain against source where available. In the corrected domain, record the
   intentional source divergence and judge against independent equations, analytic cases, invariants,
   convergence or a justified external reference. Do not force a repaired answer back to known wrong output.
5. Exercise affected graph inputs, state updates, stopping/failure behavior and complete terminal fields.
   Use a separate case not used to choose the fix or tolerances where the acceptance claim requires it.
6. Submit the exact corrected revision to read-only review. A diagnosis or edited formula alone is not
   validation; passing source parity cannot overrule an independently demonstrated scientific error.

The original defective behavior is retained as evidence, not as an extra callable by default. Only an
explicit compatibility requirement justifies a separately labelled, isolated legacy path; it cannot be
presented as the corrected relation or inherit its validation.

## Required disclosure in the affected scientific page

Describe the **科学修正说明** in the inherited scientific contract, normally under `实现对应`,
`行为与边界`, and `验证与溯源`. Do not create an expert-review section merely because a confirmed
defect was repaired:

- What the inspected implementation did and precisely why it is wrong under the stated assumptions.
- The independent basis or counterexample, with honest attribution and no unverifiable citation.
- The before/after relation or behavior, what was modified, and why the correction follows.
- The affected input domain, output differences, compatibility and dependent TaskGraph impact.
- What validation actually supports the correction and what remains unproved or for expert decision.

This disclosure is mandatory even when the repair is fully explained in a separate report. Keep command
logs, content hashes and changing pass counts in bound evidence, not the scientific narrative. The heading
placement does not excuse leaving an objectively repairable defect in the implementation. The calling
correctness owner must judge the correction against the contract, validation evidence, and read-only findings.
If a scientific choice remains unresolved, report the exact missing decision and claim impact; this protocol
does not route or approve it.
