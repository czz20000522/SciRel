---
name: scirel-acceptance
description: Run SciRel's local checks. Use before committing or pushing any change to this repository, after merging a candidate, and before saying a change is done. Maintainer skill; not delivered to users.
---

# Check a SciRel change

A change is done only when the checks here pass. Run them yourself; do not assume a hook ran them, and do not report a check you did not run.

## When to run what

| Moment | Command | What it covers | Time |
| --- | --- | --- | --- |
| While working | `python3 scripts/dev_container.py shell`, then run `python -B scripts/test_scope.py --changed <path>` and the command it prints | The affected tests | Seconds to minutes |
| Before asking for review | `python3 scripts/dev_container.py check` on the host-native container architecture | Full local acceptance and merge evidence, fastest on Apple Silicon arm64 | About 5 minutes on native CPU |
| Optional cross-device spot check | Manually dispatch the `Cross-device check` workflow | Same full acceptance on Linux/amd64 | About 5-15 minutes |
| Before each commit | `python3 scripts/dev_container.py precommit` | Lint and format on staged Python, no private paths or secrets in staged text | Seconds |
| Before each push, and before saying a change is done | `python3 scripts/dev_container.py check` | Everything listed below | About 5 minutes |

`check_all.py` prints `ALL GREEN` when everything passes. Any other ending means the tree is not green.

It prints the time of each step and takes about five minutes. Much longer means the machine is busy: look for other runs before suspecting the code. Only one run per checkout is allowed. Run it in the foreground, so that you see the result.

The pre-push fast path reuses a successful check only for the exact `HEAD` tree and current host
architecture. Receipts live in shared Git metadata keyed by that pair: different trees use different
entries, while linked worktrees at the same tree and architecture share one entry. The cache keeps at
most 16 receipts for 30 days and writes each receipt atomically. Under one cross-worktree lock, it
prunes expired, schema-mismatched, malformed and excess entries when they are safe to read and
remove. Missing or non-matching requested receipts are cache misses and run the complete check.
Unsafe cache directories and unreadable or malformed current receipts are also misses; malformed
unrelated entries are pruned when possible or skipped without hiding a readable current receipt.

It runs the full test suite, the review registry gate, contract signatures and examples, the docstring and contract sync check, the scan for new hazard patterns, the documentation build, the report validator on every solved example, the lockfile check, and a wheel build with its exposure check.

## Docstring and contract: one source of truth

For each operator, the code signature and its numpydoc docstring are the source of truth for parameter names, order, defaults, units, return entries, raised exceptions and the example. The JSON contract keeps what is only for agents (model, scope, applicability, failure semantics, evidence, limitations), and its fields that overlap the docstring are derived from it. When you change one, change the other in the same commit.

`skills/development/scirel-acceptance/scripts/check_contract_sync.py` enforces this for the assets listed in `skills/development/scirel-acceptance/scripts/contract_sync_scope.json`: signature and input names, required flags and defaults; Parameters, Returns, Raises, See Also and Examples sections; every contract unit written as `[unit]` in the matching docstring entry; every exception in `failure_semantics` listed under Raises; Examples that run as doctests and are the same code as `example.code`; the Chinese reader record bound to the current contract; and phrases listed as stale for the asset. Add an asset to the scope list once its docstring passes; the goal is the whole catalog.

## Set up once per clone

```sh
python3 scripts/dev_container.py prepare
git config core.hooksPath .githooks
```

The hooks call the same container entry point: the staged-file check on `git commit` and the full check on
`git push`. They are a safety net, not a replacement for running the checks yourself. Do not bypass them with
`--no-verify`. If a hook is wrong, fix the hook.

## Ratchets

Two lists only tighten.

- `skills/development/scirel-acceptance/scripts/contract_sync_scope.json` lists the assets whose docstring and contract are checked for agreement. Add to it; do not remove from it.
- `skills/development/scirel-acceptance/hazard_baseline.json` lists accepted hits of the hazard scan. A new hit fails the check. Read it with the `api-design-method` skill's checklist. Fix it, or if it is intended, regenerate the baseline with `scan_hazards.py src/scirel --write-baseline <file>` and say why in the commit message.

## When a check fails

1. Find the cause before changing anything.
2. Fix the code when the code is wrong. Fix the check, and say why in the commit message, when the check is wrong.
3. Never widen a tolerance or delete an assertion only to pass. Physics changes need the maintainer's decision; see `AGENTS.md`.
4. Rerun. Only the latest run counts.

## After changing a delivered skill or the wheel

Also confirm the package builds from a clean commit:

```sh
python3 scripts/dev_container.py shell
uv build --wheel --out-dir <tmp>
uv run --frozen python -B scripts/build_pure_delivery.py --wheel <tmp>/scirel-*.whl --output <new-dir>
```

Skills under `skills/development/usage/` are what users' agents receive. `scirel-outbound-evaluation` covers testing them.

## What these checks do not establish

They confirm structure, regressions and bindings. They do not establish that the physics is right. Scientific review is recorded in `catalog/review/`, and status changes need a human decision.
