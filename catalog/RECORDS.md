# Record locations, lifetime and cleanup

This policy covers product assets, tools, records, working contexts, running
resources and deliveries. Location follows authority and lifetime. Age can
trigger review; it is never sufficient evidence for deletion. A long-lived asset
can retire when its supported purpose or obligation ends.

## Ownership and retirement

| asset | owner / continuing purpose | end condition and required readback |
| --- | --- | --- |
| implementation, contract, direct test, formal docs or skill | maintainer of the supported capability or method | reviewed removal or replacement of the promise; migrate live consumers and references together, preserve necessary evidence, verify the remaining interface and tests |
| formal script / validator / builder | maintainer of its active entrypoints and consumers | supported workflow replaced or retired; check callers, tests, docs and scheduled users before removal; a script is not disposable merely because an Agent wrote it |
| one-off probe / task note / handoff | creating task until its result is accepted or transferred | preserve the minimal conclusion/failure identity/regression in the existing canonical record; recipient takes over or problem closes, then remove the obsolete active copy |
| branch / worktree | active task owner | task accepted, cancelled or transferred and every uncommitted/unmerged result has an explicit destination; inspect owner, status, refs and merge state before retirement; use the managing tool for managed worktrees |
| session | responsible task owner | result, blockers, evidence and next action transferred to the canonical task and recipient; stop pending work before archiving, subject to the user's archive authorization |
| temporary service / process | starting task and active users | no continuing consumer or scheduled work; stop the exact owned process, verify its exit and endpoint closure; do not kill by age or broad process name |
| environment / container / cache / scratch | task or workflow that uses it | command/task complete and no active owner, shared use or unique untransferred result; remove only the owned resource and read back its absence; retain the canonical development environment while it is used |
| final delivery / snapshot and minimal receipt | delivering task plus current recipients | no live recipient, test, acceptance or decision still needs it, and its replacement or retirement is verified; an immutable in-use delivery remains unchanged even when the source advances |

Use the existing task, Git refs, caller search and runtime state to decide; do not
create a hand-maintained registry of every repository asset. A reference may be
stale, so check its owner and purpose as well as its existence. Lack of evidence
to retire an asset means keep it and record the specific unresolved use.

Before deletion, list exact paths/resources and inspect references, active owners
and uncommitted/unmerged work. Transfer necessary results first, remove only the
reviewed set, then read back filesystem/Git/process state. Record the actual
outcome in the existing task; a policy edit alone is not completed cleanup.

## Durable, Git-tracked process records

| location | contents | lifetime | cleanup / change |
| --- | --- | --- | --- |
| `catalog/examples/` | public contracts, derived from `src/` implementations | project lifetime | change it in the same commit as the code it records |
| `catalog/AUDIT.md` | audit and promotion policy | project lifetime | controlled doc change |

These are process records. The implementation is the truth: the contract is its
derived record, and the documentation derives from the contract.

## Separate process records from results

Process records describe a reusable method or obligation and stay in their
canonical tracked location. Results describe one exact source/runtime/command
observation and must carry its scope, status, and claim ceiling. Temporary
runtime products are disposable after their useful finding is condensed into
the existing task or review record. Frozen deliveries and
truth fixtures remain byte-exact while a named consumer, test, acceptance, or
decision still uses them. A historical result may be retained as evidence but
must never be presented as the current baseline.

Every named checkpoint that creates generated output closes with an exact
disposition receipt: path, owner, consumer, `RETAIN`/`RETIRE`/`HOLD`, reason,
end condition, and readback. Do not create a second artifact registry; use the
existing task and handoff records. If ownership or continuing use is unclear,
keep the path and record `UNKNOWN` or `HOLD` rather than deleting it.

## Transient work products

| location | contents | lifetime | cleanup |
| --- | --- | --- | --- |
| task-owned ignored run directory under `dist/` | raw audit reports, probes, smoke/acceptance runs and worker scratch | until findings and minimal evidence are transferred to the existing task/review record | delete the reviewed scratch set when its purpose ends; preserve failing evidence needed for recovery |
| system temporary directory | unavoidable short-lived tool scratch | one command | clean the owned paths; do not make private temporary paths a tracked evidence dependency |
| `build/`, `*.egg-info/`, `__pycache__/` | build/cache | one command | delete after build/test; never commit |

Before retiring a failed attempt, record its minimal candidate identity, failure
cause and regression result in the existing task/evidence record. A rejected
package with no continuing use is then removed immediately; retaining a whole
wheel/docs/partial tree is not failure evidence. Builders stage outputs and roll
back owned partial outputs on failure without touching pre-existing targets.
Keep only genuinely needed human-review evidence in the existing review record.

Task handoffs end when the recipient has taken over; problem notes end when the
problem is resolved. Transfer necessary conclusions into the existing canonical
truth/task record, then remove the obsolete note from the active tree. Keep one
current handoff entry; use Git for history rather than parallel handoff copies.
After a successful task, remove its scratch, duplicate environments and caches.

## Generated product artifacts

| location | contents | lifetime | cleanup |
| --- | --- | --- | --- |
| `dist/docs-*`, `dist/scirel-docs-*.tar.gz`, consumer bundles / transport archives | rendered documentation and immutable delivery snapshots | while actively used or required for verification | rebuild to a new target at a named commit; retire old outputs only after verifying replacement and ending their continuing use |
| `dist/reference-truth/` | external oracle artifacts used by tests/reports | while referenced by a test, acceptance record or decision | keep the `TRUTH.json` provenance and generator script; delete only after the reference is retired and the test is updated |
| `tests/fixtures/<domain>/` | reviewed, tracked domain fixtures used directly by tests | while the supported test and its evidence remain active | preserve byte identity and provenance; retire only with the consumer, contract evidence and generator/decision update |
| `dist/acceptance/` | acceptance verdicts | project lifetime or release cycle | archive with the release; never silently replace |

Generated artifacts are gitignored. They are reproducible products, not source
truth; a test may use a reviewed tracked fixture when its provenance and
candidate-generation path are documented. Candidate outputs must remain
separate from the formal fixture and must not overwrite it by default.

## Skills

`skills/` is part of the published tree. Do not put run outputs or truth artifacts
inside a skill directory.

## Review candidates

Candidate code and contracts that are not admitted belong in the review tree
(`catalog/review/candidates/`, `catalog/review/examples/`, or an external review
tree), never in `src/scirel/` or `catalog/examples/`. The review tree may be
Git-tracked as review evidence; it is never installed or exposed. After merge, the staged copy is removed
only after the merged closure is green; the verdict record remains.

## Closing checklist

1. `git status --porcelain` is clean.
2. No tracked file cites `/tmp`, a private path or a hidden oracle.
3. The final deliverable is bound to its clean source and exact content. Remove
   superseded snapshots and rejected packages with no continuing reference/use;
   a superseded label alone is not retirement. Keep genuinely referenced final
   deliveries for their actual scope.
4. Every derived artifact has provenance and a reproducible generator.
5. A contract whose implementation has not landed lives in
   `catalog/review/examples/` and is promoted together with that code.
6. Review-stage code and contracts are never installed or exposed.
