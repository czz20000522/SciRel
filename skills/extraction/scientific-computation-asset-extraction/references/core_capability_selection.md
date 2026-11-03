# Candidate capability inventory and receiver-side selection

Extraction and selection are different jobs. The decomposition agent must not guess
what the receiver needs before the receiver has seen the candidates.

## Two roles

1. **Decomposition agent: maximize recall of defined capabilities.** Read the frozen
   source, enumerate every distinct scientific/numerical mapping and executable
   framework slice that satisfies the `scientific_operator` / `scientific_task_graph`
   definitions in `shared_asset_contract.md`. Do not filter by a guessed receiver value,
   a 10–20% target or a capability matrix you do not own.
2. **Receiver: select and merge.** The receiver owns the catalog/capability matrix, overlap
   review and the decision about which candidates add leverage. The expected 10–20%
   carried-forward share belongs to this receiver-side decision.

## Practical candidate test

These are form tests, not value tests. If the answer is "yes", keep the capability as
a candidate even when its receiver value is unknown.

- Can you name one scientific/numerical mapping (operator/function) or one executable
  framework slice (task graph/composition) with a clear purpose?
- Does it have explicit inputs, outputs, units/axes/state, and deterministic or
  explicitly declared numerical behavior?
- Is the behavior source-specific scientific/mathematical content, rather than only
  configuration, parsing, logging, plotting, orchestration glue or a vendor copy?
- Can it be independently tested, or can a source/trace/oracle be inspected to test it?
- After deduplicating generated variants, is it a distinct semantic capability?

If the evidence is insufficient, mark it **uncertain candidate**, not "not needed".
Only exclude cases that fail the form test: non-scientific glue, vendor code, generated
duplicates, or a capability with no identifiable behavior.

## Inventory record

For every candidate, record:

- capability id, one-line scientific purpose and source anchor;
- type: operator/function or task_graph/composition;
- ports, units/axes, state/order and failure behavior known so far;
- evidence available (source probe, test, oracle) and duplicate family;
- extraction effort/risk and an execution priority (centrality/reuse/testability);
- uncertainty notes.

Priority is an ordering for implementation, **not** a filter. A low-priority candidate
stays in the inventory and backlog.

## What 10–20% means

10–20% is a receiver-side estimate of how many candidates may add enough leverage to be
carried into the receiver. It is not a line-count target and not an extraction quota.

- Early in the receiver, when the catalog is sparse, the carried fraction can be higher.
- As the catalog becomes richer, fewer source capabilities add new leverage.
- A large candidate inventory is a successful extraction, not a failure of precision.
- Do not drop a genuine capability merely because it might be outside an estimated
  core set. Do not extract only glue because it is numerous.

## Reporting

Report candidate counts by type, duplicates removed, excluded form failures, uncertain
candidates and uncovered source areas. Optionally report a proposed execution order.
Do not report "we selected 10–20%" unless the receiver's catalog/overlap review has
actually happened.

## Relation to the receiver naming

The methodology uses `scientific_operator` and `scientific_task_graph`; the delivered
the receiver library calls the same shapes plain **functions** and **compositions**. The
definitions, not the labels, are the boundary.

## Proactive supply, not demand-driven extraction

the receiver targets broad coverage of controlled fusion work. The decomposition line must
not wait for a capability-demand map, a capability matrix or a "we need this now"
signal before starting. It is a proactive supply line: identify valuable scientific
capabilities in mature source projects before the receiver needs them.

"Valuable" here means source-side scientific/numerical value, reuse leverage and
testability — not a guess about the receiver's current roadmap. The decomposition agent may
rank candidates for execution, but must not reject a genuine capability because it
cannot see a current demand.

## Handoff boundary

- The decomposition line owns: source understanding/translation, independent rewrite,
  direct tests, source/oracle evidence, asset contracts, candidate inventory and a
  submission that satisfies the receiver's defined reception/admission interface.
- The receiver owns: acceptance, overlap/reception decisions, capability-matrix placement,
  catalog integration and the final decision about what enters the library.
- Once the candidate inventory and admission-shaped submission are delivered with
  correctness evidence, the decomposition line's responsibility ends. It must not
  wait for acceptance or perform reception/merge decisions.

## Correctness is the product

A decomposed asset that is not demonstrably correct has no value: users could use the
mature source project instead. Every delivered candidate must carry the strongest
available evidence — source parity, independent oracle, analytic invariant, boundary
probe, or an explicit NOT_RUN with the missing evidence named. Do not trade correctness
for coverage; do not submit untested guesses as assets.
