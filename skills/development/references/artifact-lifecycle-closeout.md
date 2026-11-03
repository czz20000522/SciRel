# Artifact lifecycle closeout

Use this reference when a task creates, receives, hands off, archives, or
cleans generated files, runtime resources, test evidence, or delivery
packages. Ordinary source work that creates no named artifact can skip it.
This is an execution method; the repository retention rules in
[`catalog/RECORDS.md`](../../../catalog/RECORDS.md) remain authoritative.

## Classify before touching files

Give the task one stable `task_key` and record the owner, lifecycle mode,
source revision, worktree state, runtime/dependency identity, run or receipt
identity, owned roots, non-goals, and the condition that ends retention. Every
path must belong to exactly one class:

| class | meaning | default treatment |
| --- | --- | --- |
| process | method, contract, validator, skill, or durable policy | keep in its canonical source; change only with the owning rule and consumers |
| result | current test, audit, acceptance, or decision evidence | bind to the exact source/runtime/command/scope; transfer the conclusion to the canonical task or review record |
| temporary | cache, scratch, failed attempt, build tree, duplicate log, or probe | remove after its useful finding is condensed and read back |
| frozen delivery | immutable package, truth fixture, acceptance verdict, or receipt still serving a consumer | retain byte-exactly until the named consumer, test, acceptance, or decision ends |

A result is not a process record. A historical result is not the current
baseline. A digest proves bytes and a manifest proves membership; neither one
proves scientific correctness or human acceptance.

## Closeout sequence

1. **Classify and bind.** For each result or delivery, record its exact path,
   owner, consumer, source revision, dirty state, runtime, command, target
   scope, status, and failure or claim ceiling. Use only
   `PASS`, `FAIL`, `NOT_RUN`, `BLOCKED`, `HOLD`, and `UNKNOWN` as applicable;
   never upgrade a missing receipt from file existence.
2. **Condense.** Move the minimum conclusion, failure identity, reopen
   condition, and next owner into the task, review record, or Notion record.
   Do not add a handoff log to the published repository, do not create a second
   registry, and do not copy a full output tree into a skill or tracked source
   directory.
3. **Plan exact dispositions.** For every owned path choose `RETAIN`,
   `RETIRE`, or `HOLD`, with the consumer, reason, and end condition. A
   superseded name, age, size, or glob is not a deletion reason. Missing
   ownership, an unresolved consumer, a live process, or an untransferred
   failure stops that path as `UNKNOWN` or `HOLD`.
4. **Apply only the reviewed set.** Remove exact temporary paths after their
   findings are condensed. Never delete by broad workspace root, recursive
   pattern, age, or filename prefix. Never mutate a frozen delivery in place;
   make a new bound target when replacement is authorized.
5. **Read back.** Verify removed paths are absent, retained paths still match
   their manifest or digest, the Git tree contains only intended tracked
   changes, and no active consumer or process was touched. Record files/bytes
   removed and every retention exception.
6. **Close the handoff.** Update the current handoff and existing work record
   with the final source revision, clean/dirty state, checks, dispositions,
   unresolved states, and the first authorized next action. Leave release,
   platform, rights, and human-scientific claims `NOT_RUN` when they were not
   executed.

## Minimum closeout record

```text
task_key / owner / mode
source_revision / source_dirty / runtime_identity / run_or_receipt_id
owned_paths: exact paths
dispositions: path -> RETAIN | RETIRE | HOLD + consumer/reason/end condition
checks: command + scope + exit/status
removed: files and bytes
retained_exceptions / unresolved states / reopen condition
next_owner / next authorized action
```

The cleanup route may stop with a partial receipt. It must say which paths are
still `HOLD` or `UNKNOWN`; it must not hide them by deleting the evidence or
calling the whole task complete.
