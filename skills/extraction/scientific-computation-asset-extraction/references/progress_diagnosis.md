# Extraction Progress Diagnosis

Use this mode for one evidence-bound status assessment of an existing project extraction. It is read-only and does
not continue extraction, repair records, restage candidates, rerun source capture, approve science, or publish a
bundle. Repeated monitoring requires an explicit request and a bounded interval or milestone.

## Required scope

Resolve the exact source-project scope and the current extraction snapshot before judging progress:

- source identity and declared scope manifest;
- progress record and its `closure_signal` when present;
- capability evidence matrix and extraction ledger;
- exact bundle root and staged candidate identities;
- validator version or repository revision used for the assessment; and
- prior snapshot only when its project scope and identity are comparable.

Missing inputs do not become empty coverage or zero progress. Continue with the available evidence and mark the
affected conclusion `inconclusive`.

## Diagnose

1. **Bind the snapshot.** Record the exact paths or artifact refs, repository revision, bundle digest when one exists,
   and whether any inspected tree is dirty. A dirty tree is an observation, not a completion state.
2. **Establish the contract.** Read only the applicable sections of
   [capability closure and progress](scientific_capability_closure_and_progress.md) and
   [the stage boundary contract](stage_boundary_contract.md). Keep project discovery, candidate staging, scientific
   review, and publication as separate owners.
3. **Use deterministic evidence.** When all required inputs are available, run the maintained validator without
   editing them:

   ```text
   python scripts/validate_capability_progress.py <progress.json> \
     --scope-manifest <scope.json> \
     --capability-evidence-matrix <matrix.json> \
     --ledger <ledger.json> \
     --bundle-root <bundle-dir> \
     --require-closure-signal
   ```

   Record the real exit state and JSON result. A validator failure is evidence about the supplied snapshot; it does
   not authorize an automatic rewrite.
4. **Separate counts from readiness.** Report discovered, inventoried, staged, blocked, and closed capabilities only
   when the current records support those categories. Candidate count, test count, or a clean build does not prove
   project closure.
5. **Locate the frontier.** Identify the smallest current boundary preventing the next valid state: undiscovered
   scope, missing scientific contract, unresolved dependency, missing source observation, failed evidence gate,
   candidate not staged, or external resource unavailable. Name its owner and the evidence needed to close it.
6. **Compare history carefully.** Claim improvement, stall, or regression only from comparable snapshots. Distinguish
   no new evidence from actual failed work, and distinguish `blocked_external` from incomplete work that remains
   locally actionable.
7. **Name the next stage point, not a guessed date.** State the exact gate whose satisfaction advances the project.
   Estimate time only when comparable throughput and remaining-scope evidence exist; otherwise report the remaining
   gates instead of inventing a schedule.

## Output contract

Return a compact assessment:

```text
Scope
  Project:          <identity and exact snapshot>
  Evidence status: <complete|partial|inconclusive>

Observed progress
  Closure signal:  <recorded value or absent>
  Coverage:        <evidence-supported counts or unknown>
  Candidates:      <staged/blocked/ready facts>

Diagnosis
  Assessment:      <consistent|at-risk|inconclusive>
  Evidence:        <validator result and decisive records>
  Blockers:        <frontier, owner, and missing evidence>

Next stage point
  Gate:            <next mechanically or scientifically meaningful condition>
  Ready work:      <independent work that can proceed now>
  Time basis:      <supported estimate or insufficient evidence>

Limits
  <unread, unexecuted, or non-comparable boundaries>
```

The assessment labels are advisory summaries, not workflow states. Preserve the recorded `closure_signal` verbatim
and never translate `consistent` into approval, `full_freeze`, integration, or release.
