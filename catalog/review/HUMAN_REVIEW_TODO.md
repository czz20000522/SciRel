# Human-review decisions pending

Status: one pending decision. Pending assets are not exposed while listed.
Resolved decisions remain in `VERDICTS.json`, their cited evidence and Git history.

| item | asset(s) | question | owner | decision | evidence required |
| --- | --- | --- | --- | --- | --- |
| Direct inversion release | `scirel.inference.direct-anisotropic-inversion` | restore/bind exact admitted direct-inversion graph artifact, then rerun composition + physical-closure | inference owner | pending | exact graph artifact id/hash + re-audited composition |
When a decision is made: update `HOLD.json`/`VERDICTS.json`, add the evidence,
run `scripts/review_gate.py --check`, rebuild docs, and only then expose.
