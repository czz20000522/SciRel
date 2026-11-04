# Evidence and Runtime Resource Lifecycle

Use this reference whenever extraction creates probes, source workcopies, captured arrays,
validation output, build products, Docker containers, or temporary volumes. Cleanup is part of
extraction correctness: the formal deliverable is the source-free asset bundle; external evidence
and runtime resources are bounded working state, not a second permanent product tree.

Do not delete evidence that is still needed for replay, an independent extraction check, a paused handoff, or an
unresolved claim. Do not retain it indefinitely after those consumers have finished. The lifecycle
is `create -> use -> condense -> verify -> retire`, with every exception explicit.

## Establish one run ownership envelope

Before creating the first external file or container, choose one stable `run_id` for the extraction
or milestone and record an external run-resource manifest containing:

- the immutable source identity and exact formal bundle root;
- one evidence root and one or more disposable scratch/build roots;
- every created path, container ID/name, temporary volume, and background process owned by the run;
- current state (`active`, `paused`, `evidence_pending`, `frozen`, `failed`, or `abandoned`);
- retention reason and expiry/reopen condition for anything that must survive a pause; and
- a disk budget, current free-space check, and low-space stop threshold.

Use one stable run directory. Within it, allocate a distinct attempt write root when an execution may overlap,
runs in the background, or is retried before the previous writer's termination and evidence disposition are
proved. Reuse an existing attempt root only after those checks. Do not keep a new timestamp tree for every
serial retry when the previous attempt has no independent audit value: condense or discard it, then reuse or
replace it deliberately. Cleanup may act only on exact resources in this manifest after resolving and checking
their identities. Never use a broad glob, workspace root, user profile, drive root, `docker system prune`,
`docker container prune`, or a cross-project evidence parent as a cleanup target.

Use this minimum manifest shape; additional fields are allowed, but none of these ownership fields
may be omitted:

```json
{
  "schema_version": "1.0",
  "run_id": "<stable-run-id>",
  "state": "active",
  "source_identity": "<immutable-source-digest-or-ref>",
  "formal_bundle_root": "<exact-path>",
  "evidence_root": "<exact-path>",
  "scratch_roots": ["<exact-path>"],
  "owned_paths": ["<exact-path>"],
  "containers": [
    {
      "id": "<docker-id>",
      "name": "<deterministic-name>",
      "required_for_resume": false
    }
  ],
  "temporary_volumes": [],
  "disk_budget_bytes": 0,
  "low_space_stop_bytes": 0,
  "retention_exceptions": []
}
```

The manifest is mutable run control, so it stays outside the formal bundle and is deleted with the
run tree after its cleanup result has been condensed into the formal report/ledger.

## Evidence classes

### Formal retained result

Keep the canonical bundle: callable packages, runtime-required data, package tests, framework map,
extraction report, ledger, and allowed runtime metadata. Before retiring external evidence, copy
only its durable conclusions into these formal contracts: source/equation anchor, case identity,
claim ceiling, branch and boundary coverage, tolerances, aggregate error metrics, failure/reopen
condition, bundle digest, and the exact validation result. Never copy captured arrays, source
outputs, raw logs, probes, build trees, or host-specific paths into the bundle.

### Temporary gate evidence

Keep the smallest replayable source oracle, sealed holdout, manifest, and anomaly receipt only while
an extraction gate or explicitly requested independent extraction check still depends on it. Once the same
bundle digest has passed those gates and the durable conclusions have been written into the formal package,
report, and ledger, retire the raw attachment. An explicit legal, regulatory, or user-requested archive is the
only normal exception; record its owner,
scope, size, location, and retention end condition.

### Disposable diagnostics and scratch

Compiler objects, generated executables, failed build trees, duplicate logs, transient parsers,
temporary converted tables, caches, repeated captures, and intermediate arrays are run-owned
scratch. Delete them after the current failure or milestone has been reduced to the minimal
diagnostic record needed to reproduce or reopen it. A raw dump is not more authoritative merely
because it is large.

Named probe output, launch logs, receipts, and evidence indexes belong under the run-owned scratch or evidence
roots, not a host-global temporary directory. A tool-required host temporary file is acceptable only while its
exact consumer is active; move needed content into the run or remove the file after that consumer finishes.

### Shared runtime resources

Pinned images, shared compiler/dependency caches, and platform runtimes are not run-owned by
default. Reuse them and do not remove them automatically. Remove an image, shared cache, named
volume, or another task's container only with separate explicit authorization.

## Bound evidence growth at creation time

- Prefer shapes, selectors, units, hashes, min/max/sum/norms, worst-error indices, and bounded
  samples over full production arrays. Capture a full field only when elementwise replay is
  necessary and no smaller deterministic representation can prove the contract.
- Keep one current compact result per case/branch and one final canonical-plus-holdout set. Replace
  failed or superseded attempts after their useful diagnostic delta is recorded.
- Stream or aggregate large traces instead of materializing them. Put build output and test caches
  in the declared scratch root, never in the formal bundle.
- Check available space before a source build or capture whose upper bound could cross the run
  budget. Stop before exhausting the drive and classify the run as resource-limited; do not create
  partial multi-gigabyte evidence and hope to clean it later.

## Docker lifecycle

Short jobs use `docker run --rm`. Every extraction container also carries labels equivalent to
`codefusion.workflow=scientific-extraction`, `codefusion.run_id=<run_id>`, and a project or source
identity. A resumable or long-running container may omit `--rm` only when it has a deterministic
name, the same labels, persisted logs/status, and an entry in the run-resource manifest.

At each milestone and terminal state:

1. list containers matching the exact workflow and `run_id` labels;
2. compare their IDs and names with the run-resource manifest;
3. distinguish a live owned computation from an exited or orphaned container;
4. preserve a live process only when the run is still `active` or an explicit paused checkpoint
   says it is required for resume; and
5. stop/remove only the verified owned containers, then verify that none remain.

Do not infer ownership from a name prefix alone. Do not stop a still-running source computation
because its output has been quiet, and do not restart another task's container. Run-owned anonymous
volumes may be removed after their contents are either condensed or declared disposable; shared or
named volumes are retained unless separately authorized.

## Lifecycle checkpoints

### Active milestone

After each staged slice, condense its evidence into one current report, delete superseded attempts
and disposable scratch, and reclaim exited owned containers. Keep only the inputs and observations
needed by the next named frontier or pending replay.

### Pause or handoff

Write a restart checkpoint containing the frontier, exact retained files, resource IDs, and reopen
command. Remove everything else owned by the run. A paused task with unexplained evidence or an
unlabelled container is not a valid handoff.

### Failure or abandonment

Retain one bounded diagnostic record with the failing input identity, command/runtime identity,
semantic status, minimal output excerpt or metrics, and reopen condition. Delete duplicate logs,
partial builds, captures that cannot support a claim, and all verified orphaned containers. If no
reopen work remains, retire the entire external run tree after recording the bounded gap in the
formal ledger.

### Extraction freeze

After all evidence-consuming gates have passed against the frozen bundle digest:

1. confirm that no captured value or evidence path is an active runtime input;
2. write final validation metrics, claim ceiling, digest, retained exception, and cleanup result to
   `extraction_report.md` and `extraction_ledger.md` using logical evidence identities rather than
   host-specific paths;
3. remove the run-owned evidence and scratch roots, verified containers, and run-owned temporary
   volumes;
4. recheck the formal bundle, container inventory, and free space; and
5. record counts/bytes removed and any approved retention exception.

`full_freeze` is not complete while cleanup is silently pending. If a required replay or reproduction still
requires external evidence, use `evidence_pending` (or another honest nonterminal status) and state
the exact retention reason. Project-specific instructions may prohibit deleting a particular cache
or checkpoint; they override the generic cleanup action and must appear as a retention exception,
not be ignored.

## Minimum cleanup receipt

The final ledger/report entry records:

- `run_id` and frozen bundle digest;
- evidence consumers completed;
- paths retired as logical run-relative roots and total files/bytes removed;
- container/volume counts removed and count remaining for that `run_id`;
- retained exceptions with owner and end condition; and
- free space after cleanup plus confirmation that unrelated resources were not touched.

The receipt is compact formal provenance. It is not a reason to keep the raw evidence tree that it
proves was retired.
