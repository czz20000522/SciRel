# SciReL standalone decomposition operating contract

This contract belongs only to the D0-D3 decomposition bundle. It is shipped
with that bundle and deliberately contains no link to the separate development
package. A downstream developer receives its exact packets as inputs and may
maintain a duplicated contract for its own package.

This is the shared contract for every formal SciReL skill. Read it after the entrypoint and before loading a
specialist reference. Load only the one reference named by the current trigger; references are progressive
disclosure, not a second prompt to preload.

## Invocation and routing

Every invocation must bind, or explicitly mark unavailable:

- **task**: the requested scientific action and the smallest affected capability set;
- **stage**: `D0`, `D1`, `D2`, `D3`, or `read_only_diagnosis`;
- **target**: exact source/candidate/package and content/dependency digests (never `latest`);
- **scope**: retained capabilities, full denominator, exclusions and applicability reasons;
- **owner**: the stage owner, writable derived output and next owner;
- **runtime**: profile, platform, command and dependency consumer; and
- **evidence**: available receipts, oracle/reference identity, prior failures and rights/licence basis.

If a required binding is absent, stop the affected claim as `blocked` or `NOT_RUN` and state the exact reopen
condition. Do not invent a default, probe an unbound source, or turn a short report into missing evidence.

Use the entrypoint's trigger table to choose one route. A route may call another skill only for that skill's
named responsibility. Do not load all related skills, all references, or all project history “for context”.
Reuse an attributable receipt when target, inputs, runtime and claim are unchanged; rerun only changed behavior and
its affected reverse dependencies.

## Stage and claim boundaries

| Stage | Owns | Does not prove |
| --- | --- | --- |
| `D0` | read-only upstream intake, source preparation, lineage, scope delta and frozen source delivery | extraction fidelity, scientific correctness, approval or release |
| `D1` | complete frozen-D0 denominator, source-shaped/source-free implementation, source behavior comparison, composition and fidelity review | independent physical/numerical correctness, normalization, human endorsement or release |
| `D2` | scientific correctness, independent comparison, correction, deduplication, normalization and integrated development delivery | D0/D1 source coverage, human endorsement, publication or release |
| `D3` | exact installed package on its supported platform, useful application case, repeatability and application evidence | source fidelity, library-wide correctness, human endorsement or release |
| `read_only_diagnosis` | inspect one exact snapshot and report state/evidence | any write or stage transition |

Human approval, redistribution rights and release acceptance are separate states. Agent output cannot grant rights,
approval or publication. A successful technical run advances only its named claim.

## Evidence planes and result states

Keep these planes separate in every receipt and handoff:

1. **source** — what the bound source/D0 actually did, including failures and NaNs;
2. **runtime** — environment, dependency, process and packaging observations;
3. **scientific** — independently stated relation, oracle, numerical/composition checks and correction basis;
4. **human** — expert interpretation, endorsement and unresolved decisions; and
5. **release** — licence/rights, packaging, publication and distribution acceptance.

Use explicit states: `passed`, `failed`, `blocked`, `NOT_RUN`, `inapplicable`, `pending_human`, and `no_changes`.
`blocked` means a required fact or owner action is missing; `NOT_RUN` means the check was not executed. Neither is
pass. Preserve the first failure, exact error/exit status, target identity, inputs and attempted command. A repaired
checker or binding gets a successor receipt; never overwrite or relabel the original observation.

## Denominators and gates

Carry the complete declared capability/case/branch denominator into every derived matrix. Keep original grids,
tolerances, thresholds, boundary and failure cases. A digest binds bytes, not truth; a manifest binds membership,
not scientific validity. Never shrink scope, remove a failing row, downgrade a tolerance, or replace a missing oracle
with a compact report. Mark an excluded item with its reason and reopening condition.

## Minimal output contract

Return one compact, machine-readable or tabular handoff with:

- exact target/dependency/runtime identities and stage;
- scope and denominator (`covered`, `passed`, `failed`, `blocked`, `NOT_RUN`, `inapplicable`);
- checks actually executed, observed values and criteria;
- evidence-plane references and hashes (source/runtime/scientific/human/release);
- claim ceiling and limitations; and
- next owner, action and reopen condition.

Do not claim stage completion, approval, rights or release unless the receiving owner has its own evidence and
transition rule. A process count, test count, worker activity, clean diff or generated document is not completion.

## Shared language and diagnosis

Use the project's development-process and owning requirement terminology for
stages, assets, relations, handoffs and claims. When a term is ambiguous, record
the competing meanings and resolve the smallest decision that changes scope or
acceptance; do not create a second glossary inside a skill. Prefer the existing
specialist route for diagnosis: source-fidelity comparison for D0/D1, scientific
validation for D2, runtime dataset construction for D3, and operator review for
independent or human-bound decisions. A generic bug fix, a compact report, or a
worker transcript cannot replace the route's evidence plane.

For repeated work, measure context loaded, specialist calls, retries, rework,
and handoff size against the same denominator and claim ceiling. Promote a
change only when it preserves scientific and ownership boundaries at lower or
better-bounded total cost; otherwise keep the observation as a scoped next
trigger rather than adding a case-specific rule.

## Evolution loop

A skill evolves only when a repeated error path is observed. Record the smallest counterexample with its trigger,
wrong route, missing binding, wasted work and outcome. Then update exactly one of: trigger/exclusion, route table,
output field, validator, or reference. Add one regression test or fixture that would have caught that path; preserve
existing gates. Measure before/after context lines, tool calls, retries, and claim quality on representative tasks.
Retire a rule when its trigger is redundant or its evidence shows no value. Do not append case stories to the skill
body: promote the invariant and keep examples in a reference or test.
