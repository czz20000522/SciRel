# Human review handoff

Read the [SciRel workflow requirement](../../../../docs/requirements/scirel-workflow.md). The expert reviews one
scientific proposal through three linked materials:

- the candidate document, which explains the relation, differences, API, provenance, evidence, limits, and requested
  decision;
- the candidate code or an explicit no-code rationale for reuse/duplicate dispositions; and
- the candidate tests and actual results supporting the proposal.

The document is the primary surface. It must let the expert understand the proposal before opening implementation or
machine records. Missing science remains a visible question; it is not filled from names, similarity, or model output.

## Upload and review boundary

Before upload, the external agent may merge, replace, or withdraw drafts to reduce duplicate review work. Upload
records the exact initial document/code/test version for each `review_pending` item and ends that agent run. The
workbench has no background model that changes queued content, whether or not an expert has opened the item.

Opening full detail is read-only and records the exact version shown. Claiming an item is a separate action: the host
grants an exclusive write lease and binds the current version as the reset point. Human edits create linked content
versions; returning the item saves the current version and releases the lease without completing review. Only an
explicit submit action binds the final version and review decision.

If AI rework is needed, the uploader starts a separate external-agent task and explicitly uploads or links its result.
It never silently replaces an existing queued version.

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
