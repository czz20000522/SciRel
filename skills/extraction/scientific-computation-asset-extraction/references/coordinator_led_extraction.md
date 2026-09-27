# Coordinator-Led Single-Project Extraction

Read this reference when one source project exposes multiple independent scientific work items or when the
runtime may provide delegated workers. The coordinator derives work from the project's scientific dependency
graph. The caller supplies an objective and scope ceiling, not worker assignments.

## Authority and invariant method

The coordinator owns the frozen source/evidence universe, living project map, dependency queue, live bundle,
shared sidecars, integration, and all completion claims. Workers own only the private staging paths or read-only
questions named in their work packets.

Worker capacity is a runtime observation, not a workflow parameter. When capacity is available, dispatch as many
independent ready items as can be owned safely. When no delegated capacity is available, the coordinator runs the
same queue serially. Do not prescribe a worker count, role count, or concurrency target. More workers never relax
dependencies, write ownership, evidence independence, or extraction exit criteria.

Use only a delegation surface provided by the runtime or explicitly approved for the run. Generic shell access is
not itself delegated capacity: do not synthesize unmanaged child CLI processes or let workers recursively create
workers. When the run supports external CLI workers, its launcher must admit capacity atomically, confine each
worker's writes to the packet lane, keep shared integration coordinator-only, and leave a durable exit/handoff
receipt. If those controls are absent or reject the launch, return the packet to the same queue and use the serial
fallback.

The coordinator continuously performs these actions:

1. update the project discovery map from accepted evidence;
2. derive ready, waiting, and integration work from scientific identities and explicit port dependencies;
3. select the highest-value ready frontier rather than the largest file or package batch;
4. assign an item to one owner or claim it locally;
5. review and integrate a handoff against the current dependency revisions;
6. freeze each complete candidate into project staging; and
7. declare extraction complete only after the declared project scope reaches `full_freeze`.

## Pipeline queue

Useful work-item kinds include:

- read-only relation/source/state discovery for a named scientific region or target path;
- hidden-state or runtime-observation recovery;
- operator contract and source-free implementation;
- source-fidelity and relation-sensitive extraction checks;
- TaskGraph composition after exact dependencies are ready;
- contract or root-document drafting from already confirmed scientific facts; and
- integration or repair of a named candidate/edge.

An item moves through the states appropriate to its kind:

```text
discovered -> boundary_draft -> ready -> active -> integration_review
           -> candidate_integrated -> candidate_staged
```

Use `waiting_dependency`, `blocked_external`, `needs_replan`, or `failed` only with a named reason and reopen
condition. A TaskGraph remains `waiting_dependency` until the exact node and nested-graph versions it binds are
ready. An unrelated operator may pass through the line while that graph waits.

## Work packet

Every delegated or locally claimed item has one durable packet:

```text
work_item_id and kind
scientific question and expected extraction artifact or evidence result
target relation, capability, path, edge, or candidate identities
frozen source/evidence and current candidate/dependency digests
provisional inputs/outputs, units, axes, lifecycle, and dependency revision
complete owned read-only allowlist, candidate-read decision, owned write paths, and prohibited shared paths
claim ceiling, explicit non-goals, and downstream consumer
targeted validation and required handoff fields
```

Do not assign broad ownership such as "all operators" when a scientific relation or source/state question can be
named. Discovery workers are normally read-only. Candidate workers write private staging paths. Only the
coordinator changes the live bundle, project map, ledger, aggregate progress, current digests, or lifecycle signal.
For parallel regions, name the target outputs, source anchors, dependencies, and expected handoff separately so
overlapping physics is reconciled once by the coordinator. A document worker may prepare a private draft from a
confirmed contract or validated snapshot; it may not infer missing physics or edit the shared root report.

Shared reads are part of the ownership contract. Allowlist the frozen source and only the exact frozen references
needed by the item; exclude coordinator state, unrelated lanes, and aggregate evidence. Candidate workers may
read a frozen candidate version when the packet says so. When the claim requires an output-blind or otherwise
independent context, the packet must prohibit candidate reads. Enforce this allowlist in the launcher/runtime
when that capability exists and review the observed read policy before accepting the claim. If it cannot be
enforced, keep the independence claim unproved or return the item to coordinator-local serial execution; do not
infer isolation from lane-only writes.

Two items may execute concurrently only when their writes do not overlap and they either have no dependency or
consume a frozen upstream contract. A downstream worker may draft against a frozen interface, but composition
cannot close until the coordinator verifies the actual upstream output and digest.

## Attempt write ownership

A lane identifies the scientific work item; an attempt identifies one execution writer. Give a background,
delegated, or retried execution distinct run-owned `scratch` and `evidence` roots whenever the prior writer's
termination has not been proved. A path has at most one live writer. Before launch, record the attempt identity
and exact writable paths and prove that no active process or container owns them. After launch, verify the actual
mounts and singleton writer rather than relying only on the requested command.

After an attempt emits a receipt or evidence that must remain auditable, freeze that attempt's writable roots.
A rerun after changing the harness, input, image, command, or expected observation always gets a new attempt,
even when the earlier writer terminated cleanly. Reuse is limited to a terminated attempt whose contents were
explicitly discarded because no receipt or evidence needs retention; never mix or overwrite two observations in
one attempt.

If concurrent writers touch one attempt, stop the exact writers after preserving bounded logs, mark the whole
attempt `superseded_contaminated_concurrent_write`, and reject its scientific conclusions. Do not select an
apparently clean file from a contaminated attempt. Rebuild the probe or worker inputs from immutable source and
frozen dependencies in a fresh attempt. Read-only source and candidate mounts may be shared; writable scratch,
evidence, output, and receipt paths may not.

Keep named probe output, launcher logs, receipts, and singleton/mount proof under the owning run or attempt.
Host-global temporary storage is not a durable handoff path. If a tool necessarily creates an ephemeral host
temporary file, track it and either move its needed content into the run or remove it after the last consumer.
Do not copy a run-owned script to host-global temporary storage merely to execute it; execute the owned copy
directly so the command, content digest, and cleanup boundary stay attributable to the lane.

## Handoff and integration

A handoff contains the exact changed paths, baseline/result digests, dependency revision, scientific finding,
tests actually run, remaining gaps, and proposed queue transition. It excludes hidden reasoning, credentials,
unbounded logs, and self-declared platform decisions.

When a launcher validates a structured handoff, `required_handoff_fields` contains literal JSON property names
only. Put nested content requirements and explanatory phrases in the packet's validation expectations, not in a
decorated field name that a machine would interpret literally.

Before integration, verify that source, candidate, and dependency digests still match the packet. Revalidate an
unrelated overlap; rebase or rerun when the owned candidate or a consumed contract changed. Workers run targeted
candidate and direct-dependent tests. The coordinator reruns the affected integration slice after accepting the
handoff. Bundle-wide gates run at a declared bounded-delivery or project-freeze boundary, not after every packet.
Reuse unchanged, digest-bound source probes, frozen candidate evidence, and prior test receipts only when their
inputs, runtime conditions, claim, and consumer still match. A source, contract, dependency, or implementation
change invalidates its affected slice and downstream consumers, not every unrelated region. Reuse never turns a
canonical case into an independently sealed holdout or bypasses a required final whole-bundle gate.

An accepted implementation handoff is not automatically a staged candidate. Freeze a candidate only after its scientific
contract, source-free callable, dependency closure, provenance, targeted evidence, and claim ceiling agree in one
digest-bound version. After freeze, retain it unchanged in project staging and continue the project queue. When
the complete declared project scope reaches `full_freeze`, close one project bundle without merging candidate
digests, dependencies, tests, or findings into one ambiguous claim.

## Delegation failure and independence

Distinguish three runtime conditions without changing the scientific method:

- No usable delegated capacity: record coordinator-only execution once and continue the same packets serially.
- Transient provider/network failure: use bounded recovery, return the packet to the queue, and let another owner
  or the coordinator claim it; do not convert transport failure into a scientific block.
- Capacity currently occupied: retain the dependency state and claim another ready item locally or dispatch it
  when capacity becomes available.

When independent validation requires a fresh output-blind context, queue it for a genuinely independent context.
If that context is unavailable, keep the affected correctness claim unproved; do not simulate independence inside
the implementation context. Reading coordinator state, an unauthorized lane, aggregate evidence, or candidate
data prohibited by the packet invalidates the affected independent claim even when no shared path was modified.
Reject that attempt's conclusion rather than repairing it in place. This limits the claim, not unrelated
extraction work.

Record process telemetry only to improve flow: state-transition time, queue wait, scientific delta, targeted-test
duration/result, rework cause, dependency wait, and runtime/provider failure. Useful throughput is frozen
candidates and closed critical frontiers, not worker utilization, package count, test count, or log volume.
