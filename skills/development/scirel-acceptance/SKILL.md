---
name: scirel-acceptance
description: Run SciRel's local checks. Use before committing or pushing any change to this repository, after merging a candidate, and before saying a change is done. Maintainer skill; not delivered to users.
---

# Check a SciRel change

A change is done only when the checks here pass. Run them yourself; do not assume a hook ran them, and do not report a check you did not run.

## When to run what

| Moment | Command | What it covers | Time |
| --- | --- | --- | --- |
| While working | `.venv/bin/python -B scripts/test_scope.py --changed <path>`, then run the command it prints | The affected tests | Seconds to minutes |
| Before each commit | `.venv/bin/python -B skills/development/scirel-acceptance/scripts/precommit_check.py` | Lint and format on staged Python, no private paths or secrets in staged text | Seconds |
| Before each push, and before saying a change is done | `.venv/bin/python -B skills/development/scirel-acceptance/scripts/check_all.py` | Everything listed below | About 5 minutes |

`check_all.py` prints `ALL GREEN` when everything passes. Any other ending means the tree is not green.

It runs lint and format, the full test suite, the review registry gate, contract signatures and examples, the documentation build, the report validator on every solved example, the lockfile check, and a wheel build with its exposure check.

## Set up once per clone

```sh
uv sync --locked --group test
git config core.hooksPath .githooks
```

The hooks then run the pre-commit check on `git commit` and the full check on `git push`. They are a safety net, not a replacement for running the checks yourself. Do not bypass them with `--no-verify`. If a hook is wrong, fix the hook.

## When a check fails

1. Find the cause before changing anything.
2. Fix the code when the code is wrong. Fix the check, and say why in the commit message, when the check is wrong.
3. Never widen a tolerance or delete an assertion only to pass. Physics changes need the maintainer's decision; see `AGENTS.md`.
4. Rerun. Only the latest run counts.

## After changing a delivered skill or the wheel

Also confirm the package builds from a clean commit:

```sh
uv build --wheel --out-dir <tmp>
.venv/bin/python -B scripts/build_pure_delivery.py --wheel <tmp>/scirel-*.whl --output <new-dir>
```

Skills under `skills/development/usage/` are what users' agents receive. `scirel-outbound-evaluation` covers testing them.

## What these checks do not establish

They confirm structure, regressions and bindings. They do not establish that the physics is right. Scientific review is recorded in `catalog/review/`, and status changes need a human decision.
