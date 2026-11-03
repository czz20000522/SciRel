# Evidence-based admission and review attention

Use when a receiving workflow must select scientifically supported capabilities for an internal distribution
and prepare a large retained increment for human review. The receiving project supplies admission and approval
policy. Reviewers return evidence and recommendations; the integration owner applies policy. These methods do
not turn source-fidelity work into a correctness review or authorize deployment, human approval or publication.

## Separate the decisions

Assess the exact implementation, public claim, applicability and dependency versions. Keep three dimensions
distinct: source fidelity, scientific/numerical support for the retained claim, and coverage/completeness.
Reproducing a source error may establish fidelity; matching examples alone does not establish correctness.
An unimplemented capability, untested extension, demonstrated error and environment failure require different
next actions. Preserve that distinction instead of reporting all of them as “needs human review.”

First determine whether evidence supports the retained claim. Then allocate human attention using consequence,
evidence independence and gaps, numerical sensitivity, assumption uncertainty, change magnitude and dependency
reach. Complexity and model confidence may prompt investigation but are not calibrated error probabilities.
A simple relation with a counterexample is not low risk; a complex well-supported relation can be admissible
while still requiring substantial human attention because of its consequences. Never average a material
correctness conflict away with passing tests, a score, or a majority of reviewers.

When the project permits supported but not yet human-approved internal packages:

- Supported claims without material unresolved conflict may enter under a pending-review identity.
- A supported restricted contract may enter with explicit coverage limits. State the limits in its canonical
  contract, review presentation and runtime docstrings; enforce reliably checkable preconditions at the API.
- A demonstrated or evidenced suspected defect, unresolved correctness disagreement, or missing basis for the
  retained claim stays outside the accepted package until resolved. A warning or expected-failure test does not
  make inaccurate behavior admissible. Preserve the candidate and reproducer for investigation.

Isolation is an admission safeguard, not completion of an authorized correctness/repair task. The D2 owner
must route a confirmed in-scope defect through the existing
[scientific-correction workflow](../../scientific-relation-implementation/references/scientific-correction.md):
establish the scientific basis, implement the repair, independently validate the corrected and affected domains,
and obtain read-only review. Apply admission and attention decisions to the resulting supported revision.
Do not substitute narrower claims or escalation for a feasible repair. Only a concrete unresolved behavior or
remedy after necessary investigation justifies scientific deferral; temporary tooling failure leaves work pending.
Final human review normally receives the corrected implementation with original behavior, error basis, changes
and verified final results. It does not outsource implementation to the reviewer.

A restricted contract needs a meaningful independent basis, not a list of passing fixtures selected after a
failure. A narrower model can be useful without claiming a broader model's physics. Confirm its implementation,
exports and dependencies isolate the unsupported behavior, and that installed code matches the restriction.
If the faulty path cannot be reliably separated, hold the affected asset. Do not hide it as a private helper or
retain it transitively through an otherwise supported graph. Unrelated supported scopes may still proceed.

TaskGraphs inherit restrictions on the dependency scopes they actually use and need evidence for composition:
units, coordinate conventions, ordering, shared state, feedback and failure propagation. A set of supported
nodes alone does not qualify their composition. Prioritize a shared uncertainty at its dependency root, then
identify the affected consumers rather than opening identical investigations for every descendant.

## Make AI rounds add evidence

Use author self-check, independent challenge, and targeted correction/review as distinct contributions when
multiple rounds are requested. The independent reviewer inspects exact contract, implementation and evidence
with its own counterexample hypotheses before reconciling the author's conclusion. A different model is not
automatically independent; reviewers can share the same bad oracle or assumption.

Record actual reviewer/author identity, reviewed version and scope, evidence considered, findings and unresolved
disagreements in existing development records. Distinguish proposed tests from executed observations. Route
executable validation to its authorized owner; this read-only review skill does not execute experiments.

Reconcile disagreements through a discriminating example, independent derivation or relevant reference, not
voting. Preserve the original counterexample and tolerances. A correction creates a successor with affected
regressions and dependency review; a documentation-only repair can reuse still-attributable numerical results.
Stop when the retained claim has a supported stable decision and material findings are resolved, or when a
specific missing resource/domain decision makes further automated work unproductive. Escalate that precise
question with the alternatives and consequences; do not loop for consensus or demand equal rounds for every
asset. Owner/dependency/contract changes invalidate only conclusions whose premises changed.

## Spend human attention where it changes the decision

The normal review entry is the operator/graph scientific document or its bound human projection. Put the
supported claim, applicability, significant delta, strongest evidence, residual uncertainty and precise decision
first. Keep raw logs, code, test details and source history available as optional drill-down. Prioritization and
round history are development annotations bound to that exact document/version, not competing scientific truth
or fields forced into a public scientific schema.

Where all retained candidates require final human decisions, low attention means concise review or explicit
batch confirmation of listed exact items, not implicit approval or sampling away unreviewed items. High-attention
items highlight the unresolved scientific choice. Shared assumptions may be reviewed together while preserving
item/dependency bindings. Existing unaffected approvals may be reused only under the receiving version policy.
Human judgment cannot manufacture absent evidence or erase a counterexample; a revised claim needs appropriate
validation and a new bound decision. Publication authority remains separate.

A usage manual serves a different reader: organize scientific facts by user task and API, preserve actionable
limits and failure behavior, and omit internal review mechanics. Derive it from the same canonical scientific
contract rather than copying the review page verbatim or maintaining another full scientific definition.

## Transfer a successful closed loop without overstating it

A scoped end-to-end success demonstrates that the method and its handoffs work under observed conditions. It
does not certify all source capabilities, all future projects, maintained-mainline membership or release readiness.
Transfer the decisions: fixed read-only stage inputs and editable successors; source-fidelity versus correctness;
claim-bound independent evidence; exact installed distribution in a source-independent useful application;
bad-input and recovery checks; and a compact durable handoff usable without the prior owner's session.

Reuse attributable numerical evidence across handoff, packaging and metadata repairs. Preserve failed records
and add a traceable correction; rerun affected verification when scientific inputs, implementation, relevant
environment or evidence correspondence changed. A hash/manifest pass binds bytes; stage content acceptance and
human decisions still need their own evidence. Keep project names, fixture values, device paths, service limits
and runtime choices in the task/environment record, not in this portable method.
