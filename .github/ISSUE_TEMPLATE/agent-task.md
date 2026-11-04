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

## Write scope

<!-- Exact repository paths this task may change. Anything outside this list needs a separate task. -->

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

- Use one issue, one temporary branch and one worktree per agent; do not share a mutable worktree.
- Set up with `python3 scripts/dev_container.py prepare` (Windows: `py -3`) and `git config core.hooksPath .githooks`.
- Run `python3 scripts/dev_container.py check` in the foreground and paste the final lines in the PR. It must end with `ALL GREEN`. GitHub Actions reruns the same container check.
- Write only inside the issue's declared repository paths. Do not change the user home, sibling projects, global Git/Docker configuration or another worktree.
- Interface and style work must not change results. If you find a result you think is wrong, stop and comment here.
- Physics changes need a reference and the maintainer's decision. Never widen a tolerance to pass.
- Put the explanation in the commit message. Do not add change-log files.
- Link this issue from the PR with `Closes #N`, or `Part of #N` when items remain.
