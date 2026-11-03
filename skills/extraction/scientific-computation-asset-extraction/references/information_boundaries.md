# Information boundaries

The decomposition line is a general methodology. It must not depend on the receiver's
catalog, roadmap, repository, storage layout or acceptance decisions. Keep knowledge
compartmentalized so that each worker needs only its own job context.

## Roles

- **Decomposition agent / team**: knows the source project (or the provided source slice),
  this methodology, the scientific capability definitions and the required delivery format.
  It may use source probes and source-specific evidence. It must not know the receiver's
  capability catalog, roadmap, acceptance decisions, other projects' candidates, or the
  receiver's internal project structure.
- **Receiver / integration agent**: knows the delivered, self-contained capability package,
  its contracts/tests, neutral capability-level replay evidence and the receiver's local acceptance/reception rules. It must
  not need to know which source project produced the package, its history or its runtime.
  It evaluates whether the capability is needed, overlapping or acceptable.
- **Human owner**: the only role that holds the full chain: project selection, source,
  candidates, delivery, acceptance and integration context. The human decides scope and
  global priorities.
- **Optional global coordinator agent**: may know the cross-project chain only to assist the
  human. It must not leak the receiver's catalog/roadmap to decomposition workers, nor leak
  source identity/provenance to receiver workers. It is an assistant, not a second owner.

## Allowed / forbidden

| Role | Allowed | Forbidden |
| --- | --- | --- |
| Decomposition | read provided source, run probes, write its own package/evidence, use this method and runtime-provided public admission tools | read receiver repo/catalog/roadmap/private implementation, infer receiver needs, contact receiver workers, inspect other projects' private work |
| Receiver | read delivered package, run its tests, map to local capabilities, decide acceptance | inspect source project or decomposition history, require source checkout, use provenance as a substitute for package evidence |
| Human | hold global mapping, set priorities, decide acceptance | — |
| Global coordinator | assist human with global state | propagate global context to workers; embed receiver/source identity in packages |

## Delivery boundary

The delivery must be self-contained and reviewable without the source project:

- capability inventory and selected candidate(s);
- implementation and direct tests;
- contracts/ports/units/axes/state/failure semantics;
- correctness evidence with enough detail to rerun or verify;
- license/attribution and explicit limitations/claim ceiling.

The receiver does not need the source project's identity or the decomposition agent's
runtime. Source-specific probes may remain as internal evidence, but they must not become
a required runtime dependency or an implicit input channel.

Neutral transfer preserves the capability oracle: complete frozen inputs and expected
observations, exact encodings and special-token decoding, axes/units/real-complex conventions,
NaN/Inf and comparison rules, actual diagnostics and the relevant first-failure/repair chain.
Keep the minimum data sufficient for the receiver's replay outside the callable bundle.
Remove source-checkout dependencies, private project mappings and process context; do not
replace the oracle with a PASS summary. Preserve legally required licence/attribution bytes
unchanged even when they identify an origin; this grants no access to private source work.

A capability-level oracle supplied for D1/D2 replay is not a future question's hidden answer.
Keep new question text, hidden application answers and acceptance oracles out of unrelated
workers' context, while delivering the scientific evidence required by the actual receiving
consumer. Retire that evidence only after its downstream replay/review consumers have ended,
as specified by the [evidence lifecycle](evidence_persistence_boundary.md).

## No leakage by construction

- Decomposition packages must not encode receiver-specific paths, catalog IDs or expected
  acceptance.
- Receiver-side evaluation must not depend on knowing the source project; if it does, the
  package is not self-contained.
- The human/global coordinator may translate context between sides, but workers receive
  only the slice needed for their task.
