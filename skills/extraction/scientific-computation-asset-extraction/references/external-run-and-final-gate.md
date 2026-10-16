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
- Before resuming, inspect saved deliveries across all stages and receive the
  latest applicable frozen payload, including its package, contracts and
  necessary evidence. An older control file or an incomplete local copy must
  not send a project with valid D2/D3 results back through D0/D1.
- For an interactive terminal, verify that the follow-up appears as a new
  worker input and produces an attributable response or action. A successful
  terminal scripting command, visible window or live process alone does not
  establish that the worker received or began the task.
- Close `decomposition/FINAL` against the caller's declared decomposition scope
  and the evidence actually delivered. A hash match alone does not establish
  that scope. Record scientific limitations and unresolved source rights without
  inventing approval. SciRel reception, integration, human endorsement and
  publication are downstream decisions; their absence does not block an
  otherwise complete external result. Do not place their flags in FINAL.
- During an active retry, distinguish the pre-request failure from the later
  attempt. At closeout, retain only evidence needed to interpret the final
  result; transient runner status, prompts and duplicated attempt records do
  not become permanent assets merely because they once existed.
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

## Completed project cleanup

Keep source and one current FINAL outside the development repository. Replace
FINAL only after validating its bundle; do not accumulate a new backup per run.
FINAL must contain the implementation/package, contracts, necessary scientific
evidence and licence files it declares. Resolve and verify those files before
handoff: a manifest that only points into WORK, INBOX or a disposable directory
is not a durable final payload. The upstream source remains in the separate
source root.
Project descriptors and directory indexes contain identity and paths only.
WORK and INBOX are resumable workspaces, not a second permanent status system.
After required implementation, contracts, scientific evidence and licenses have
been retained in FINAL, delete obsolete progress and redundant staging copies.

For an already integrated project, consult the development owner's actual
integration history and successor acceptance records before scheduling any
work. A status flag in a predecessor receipt applies only to that predecessor.
Check the maintained implementation and actual wheel payload as well: a later
integration can port the accepted content without making the original candidate
commit an ancestor. Distinguish a finished external scientific delivery from
missing integrated documentation, package data or notices; those omissions need
integration repair, not another decomposition run. A FINAL directory containing
only an early-stage delivery cannot establish whole-project completion or erase
later valid deliveries elsewhere.
Preserve genuinely required frozen evidence byte-for-byte; delete unneeded
status copies instead of adding another status overlay. Missing material in a
temporary staging copy does not reopen completed scientific work.

## Worker completion and coordinator cleanup

An external worker's terminal state is separate from the scientific delivery
state. The coordinator closes a completed run in this order:

1. verify the authoritative FINAL scope, manifest and payload on the receiving
   external project root;
2. record the reception identity and any remaining claim limits;
3. stop the worker and verify that its process and helper wrapper have exited;
4. remove the disposable Mac staging copy after the received payload is
   readable and hash-verified.

If FINAL is absent or its payload is not received, keep WORK and the worker
available for continuation. If FINAL is verified but an old terminal or side
session still appears active, treat that as stale control state; do not resume
scientific work merely because the session remains visible. A new authorized
phase receives a new run identity from the latest FINAL. Keep the one external
FINAL and the necessary source root; do not create a second archive to preserve
the closed worker.
