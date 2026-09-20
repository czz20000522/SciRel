# Human review handoff

Read the [SciRel workflow requirement](../../../../docs/requirements/scirel-workflow.md). The expert reviews one
scientific proposal through three linked materials:

- the candidate document, which explains the relation, differences, API, provenance, evidence, limits, and requested
  decision;
- the candidate code or an explicit no-code rationale for reuse/duplicate dispositions; and
- the candidate tests and actual results supporting the proposal.

The document is the primary surface. It must let the expert understand the proposal before opening implementation or
machine records. Missing science remains a visible question; it is not filled from names, similarity, or model output.

## Queue and observation boundary

`review_pending` means only that an item is discoverable in the review queue. Until an expert opens the full trio,
the model may merge, replace, or withdraw it to reduce duplicate review work. The queue may show a minimal index, but
that index is not scientific review.

On first open, the host sends `start_review` to SciRel before displaying detail. SciRel returns one
`review_in_progress` snapshot containing the exact document/code/test view. From then on, do not change that view in
place. New evidence or code becomes a linked rework or replacement candidate.

The host owns identity, authorization, artifact storage, CAS/current-pointer updates, and UI delivery. SciRel owns
the meanings of draft, gap, review action, approval, and release. Host run success is not scientific approval.

## Expert actions

The review surface supports four outcomes:

- `approved`: the observed proposal may enter a separate baseline-integration run;
- `needs_evidence`: the scientific proposal is plausible but its claim needs named evidence;
- `rework_requested`: the document, code, tests, or proposed disposition must change; or
- `rejected`: the proposal must not be integrated in its observed form.

An approval does not edit the SciRel baseline. The later integration run compares the approved proposal's base with
current SciRel, applies it only when the approved meaning is preserved, and runs affected tests. A scientific identity,
contract, dependency, TaskGraph, or patch conflict produces a linked new candidate; it is never resolved by
last-write-wins or by carrying the old approval forward.

Only successfully integrated and released assets enter the catalog and runtime.
