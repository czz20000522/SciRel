---
name: Agent task
about: A bounded piece of work for an agent or contributor, with its method and acceptance
labels: agent-task
---

<!-- One or two sentences: what is wrong or missing, and who is affected. -->

## Method

<!-- How to do it, including how to decide between options. Name the standard to follow. -->

## Scope

<!-- A checklist of concrete items: module, function or contract, and what to do with each. -->

- [ ] 

## Done when

<!-- Something a reviewer can check without trusting the author: a command and its result, or a test that fails before and passes after. -->

## Read first

- `AGENTS.md`, for the repository rules.
- `skills/development/scirel-acceptance/SKILL.md`, for the checks.
- `skills/development/scirel-code-style/SKILL.md`, for the standard.
- `skills/development/scirel-code-style/references/review-checklist.md`, which is how the PR will be judged.
<!-- Add what this task needs, such as `skills/development/api-design-method/SKILL.md` or `catalog/README.md`. -->

## Rules for every PR

- Set up with `uv sync --locked --group test` and `git config core.hooksPath .githooks`.
- Run `.venv/bin/python -B skills/development/scirel-acceptance/scripts/check_all.py` in the foreground and paste its final lines in the PR. It must end with `ALL GREEN`. There is no CI, so this is the evidence.
- Interface and style work must not change results. If you find a result you think is wrong, stop and comment here.
- Physics changes need a reference and the maintainer's decision. Never widen a tolerance to pass.
- Put the explanation in the commit message. Do not add change-log files.
- Link this issue from the PR with `Closes #N`, or `Part of #N` when items remain.
