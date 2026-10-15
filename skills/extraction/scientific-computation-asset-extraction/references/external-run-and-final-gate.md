# External worker runs and FINAL gates

Use this reference when a decomposition worker runs outside the SciRel checkout
and its output will later be received by the owning project.

## Evidence from the 2026-10-15 Pleiades/fluidBW runs

- Validate the runner's model selector before dispatch. A configured display
  name may be exposed through a local alias; an unknown selector is a
  `blocked_before_first_request` event, not a decomposition failure and not a
  reason to silently fall back to another model.
- Give the worker a local staging root and an explicit mapping to the
  authoritative project. The worker must be forbidden from touching the
  SciRel checkout and must keep source, evidence, outputs and lessons under
  the staging root.
- Verify the staged copy against the authoritative closed-set manifest before
  interpreting any result. Record matched, mismatched and absent members with
  byte totals. Absence from a partial staging copy is a transfer fact; it is
  not evidence that the authoritative project lacks the member.
- A frozen D2 candidate, a successful technical validation, or a complete
  staging hash does not close `decomposition/FINAL`. Root reception, scientific
  and release approval, redistribution rights, and any separately authorized
  D3 contract remain independent gates. When one is false, emit a resumable
  handoff and leave `FINAL/FINAL.json` and its bundle untouched.
- Keep the original blocked-run record and the later verification record. A
  retry that uses a valid local alias is a new attempt; it must not erase the
  pre-request failure or change the requested-model history.
- Enumerate operator and TaskGraph coverage from released record bytes and
  declared graph contracts. Thin legacy wrappers that delegate to the same
  entrypoint are duplicate views, not additional TaskGraphs; preserve the
  mapping in the handoff instead of inflating the denominator.
- Use `git bundle verify` and an explicit commit lookup for cross-stage
  bindings. A valid bundle can still omit the exact commit named by a later
  D3 predecessor receipt; record that negative result and keep the D2-to-D3
  binding gap open.
- A manifest/hash check proves byte integrity of a D3 output archive, not that
  its scientific jobs were re-executed in the current staging run. Keep
  output verification and scientific execution as separate evidence states.

These rules apply to external worker staging and reception. They do not require
every worker to copy every large binary before it can inspect a project; they
require the worker to label the copy's scope and to refuse an authoritative
completeness claim until the manifest-bound bytes are present and verified.
