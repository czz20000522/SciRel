# Human-review exposure hold

`HOLD.json` is the reversible exposure gate between candidate capability and
public capability list. Held contracts remain in `catalog/review/examples/` and
their candidate code in `catalog/review/candidates/`; their review evidence and
direct tests are retained. They are excluded from:

- generated documentation and readers,
- the capability index / query service,
- the capability matrix,
- catalog release exposure.

An asset leaves this hold only after a human owner records the decision and the
evidence required by `catalog/AUDIT.md`. The hold is a review state, not a
second scientific truth: the contract remains the single truth for the
implementation while review is pending.

## Merge layers

1. `auto-merge`: the agent verdict is `pass` or `pass-with-limits`, no agent
   disagreement remains, and the evidence closure is reproducible. The asset
   may enter the exposed catalog.
2. `human-review`: the agent cannot decide correctness/exposure, agents disagree,
   or the model/source attribution needs an owner decision. The asset is listed
   in `HOLD.json` and is not exposed.
3. `rejected`: the asset fails a required check and is not exposed; keep the
   failure record, do not silently delete the evidence.

No `auto-merge` is allowed for a tier-A asset with only self-consistency
evidence. No held asset may be cited as available in user-facing docs.

## Review record fields

`status`, `reason`, `required_decision`; optionally `owner`, `decision`,
`decided_at`, `evidence`. `HOLD.json` has no schema version suffix.
