# Public capability gap intake

Use this reference after discovery finds no directly applicable public contract.
The gap report is an observable outbound result; it is not a blanket `HOLD` and
it does not decide scientific acceptance.

## Gap card

Record one card per missing relation or incompatible contract:

```yaml
run_mode: internal | external
request_id: <task or benchmark id>
case_id: <optional case id>
requested_relation: <scientific relation or operation>
public_search:
  contracts: [<asset ids or "none">]
  near_matches: [<asset id: incompatibility>]
observed_boundary: <what the public API can and cannot provide>
fallback_class: public_capability | task_glue | contract_clarification | runtime
action: merge_intake | self_complete | ask_user | stop_for_input | retry_runtime
tests: [<normal/lower/upper and applicable adversarial cases>]
disclosure: <what remains outside SciRel and how it was checked>
reopen: <specific evidence or decision that changes the action>
```

`public_capability` means a reusable scientific relation or composition with
stable ports, units, shapes, applicability and failure behavior. `task_glue`
means orchestration, data preparation, ordinary numerical code, format
conversion or presentation that belongs to this user task. `contract_clarification`
means the request is missing a convention that changes its scientific meaning.
`runtime` means the capability is known but the selected environment did not
run. Do not use a runtime failure as evidence that a capability is absent.

## Route by mode

| Mode | First action | Allowed continuation |
| --- | --- | --- |
| `internal` | Write the card and route `public_capability` to merge/intake; keep the affected claim separate from unrelated work. | Continue with explicit glue only for non-scientific orchestration. Reopen after a candidate packet or contract decision. |
| `external` | Disclose the public gap in the user result. If choosing glue versus a SciRel addition changes scope, ask the user; otherwise continue with explicit ordinary code and public dependencies. | Keep the replacement tested and visible as task glue. Never claim that glue promoted the missing relation into SciRel. |

For an external task, a missing SciRel capability is not itself a user-facing
blocker: the programming language and ordinary dependencies remain available.
Ask only when the choice affects the requested deliverable, budget, privacy,
or scientific convention. If the user has asked for a SciRel-only result, use
`stop_for_input` and state the exact missing relation.

## Promotion decision

Send a gap to D2 intake when the same relation appears in independent tasks or
has a stable scientific contract. Keep it as glue when it is task-specific
control, conversion, formatting, or a one-off composition. A successful glue
run is evidence for that task only. Before promotion, require normal,
lower-bound and upper-bound tests, plus applicable degenerate, branch, failure
and composition cases. Preserve source or benchmark observations separately;
they are not hidden inputs to an external user run.

## Closure

Close the card with one of `merged_public_capability`, `tested_task_glue`,
`clarification_requested`, `runtime_repaired`, or `still_open`. Include the
actual output or typed failure, generated tests, and the next owner. Do not
replace a concrete gap with a generic `NOT_RUN` or a success label.
