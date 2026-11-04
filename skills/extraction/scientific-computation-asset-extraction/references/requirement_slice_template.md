# Requirement-Driven Extraction Slice

Use one copy for each high-value demand, branch, or framework edge. Keep it
project-agnostic; put project paths and numeric results in the project ledger.

## Demand

- demand:
- source/document anchors:
- expected scientific output or state transition:
- configurable inputs, axes, units, and branch selectors:

## Producer → consumer contract

- producer asset/state:
- consumer asset/graph:
- explicit port mapping (`from.output -> to.input`):
- edge closure state (`emitted_asset` / `controlled_glue` /
  `explicit_contract` / `configuration_or_schema_need` /
  `validation_oracle_gap` / `extraction_gap` / `terminal_non_emitted`):
- state/config ownership (producer / consumer / caller / observer-only):
- branch selector and default behavior when the optional port is absent:
- normalization/order/sign/unit/boundary rules:
- index scope contract (inner mesh/physics axes versus outer case/species/surface selectors; never reuse one index namespace implicitly):
- hidden state required by composition:
- runtime/probe preconditions (mode guards, initialization gates, safe abort):
- orthogonal gate matrix (recompute/refresh versus pulse/actuator enablement;
  include a recompute-allowed but actuator-off case):
- observer-only downstream graph (optional):
- observer state binding (`producer.output -> observer.input`):
- feedback mode (`static_precomputed` / `sequential_state_feedback`):
- feedback projection contract (step-0 state -> step-1 producer input):
- feedback prohibition/default-path behavior:

## Extraction decision

- emitted operator/task graph:
- controlled glue included:
- omitted or downgraded behavior:
- canonical gap (`extraction_gap` / `configuration_or_schema_need` /
  `ai_completable_glue` / `validation_oracle_gap` / `cannot_complete`):
- reason and evidence boundary:
- terminal-gap audit (if not emitted):
  - missing source fields and first producer:
  - observable output or workcopy capture:
  - existing emitted transform audit:
  - independent oracle required:
  - exact reopen condition:
  - global ghost/band/solver contract (if applicable):
    - ghost slots and source surfaces:
    - band-column/shift placement:
    - active-row, reflection/combine, RHS padding, tolerance:
    - caller-owned values still required:

## Verification

- package tests:
- composition probe:
- evidence-only probe/attachment (must remain outside formal assets):
- numerical oracle and provenance:
- `max_abs` / `max_rel` / aggregate norm:
- source-free check (source files, cache dirs, network policy):
- failure-boundary check (zero-state, nonterminal, crash/abort, and captured
  precondition evidence):
- semantic-termination check (process exit status versus source/branch completion
  marker; early-stop or `STOP` is not scientific completion):
- hidden-state branch reachability (expected branch, initialization guard,
  semantic terminal, build/link status, per-branch trace counts; distinguish an
  untriggered branch from a failed capture):
- sequential-feedback check (step-0 perturbation changes step-1 producer input;
  producer runs after state update; static precomputed paths are not called
  feedback):
- gate-boundary check (producer snapshot retained, consumer event skipped with
  explicit reason, and default behavior tested when the gate is absent):
- custom-assembly check:

## Closeout

- formal package paths:
- sidecar/evidence attachment paths:
- persistence timing: capability/contract/oracle immediately; counts/matrix/digest/report roll-up deferred:
- remaining risk:
- next slice or terminal decision:
