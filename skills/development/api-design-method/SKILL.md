---
name: api-design-method
description: Review and improve the public API and code style of any Python library, from inventory to verified change. Use when asked to refactor an API, unify style, find interface hazards, or keep documentation and code in agreement. Works for any library; takes no project knowledge beyond what its code and documents say.
---

# Improve a library's API

An API is a promise to people who will not read the code. The most expensive defect is not an ugly name; it is a call that looks right, runs, and returns a wrong answer. So work in this order: first make wrong use fail loudly, then make facts agree, then make things consistent. Stop when the remaining changes cost more than they save.

Work through the stages in order. Each one produces something the next one needs.

| Stage | Output | Details |
| --- | --- | --- |
| 1. Inventory | The list of public names, signatures and docstring coverage | below |
| 2. Find hazards | Findings, each with a concrete way to get a wrong result | [hazard checklist](references/hazard-checklist.md) |
| 3. Decide the conventions | One written standard, taken from a mature library | [conventions](references/conventions.md) |
| 4. Assign one truth to each fact | Which place owns each fact, and what enforces the rest | [single source of truth](references/single-source-of-truth.md) |
| 5. Plan the changes | A ranked list in small batches | [planning](references/planning.md) |
| 6. Change and verify | Commits, each with its own evidence | [verification](references/verification.md) |
| 7. Stop | What you left undone and why | [when to stop](references/planning.md#when-to-stop) |

## 1. Inventory

Do not rely on memory or on the documentation's list. Ask the code:

```sh
python <this skill>/scripts/api_inventory.py <package> --src <source dir>
```

It lists each public name, with its kind, signature, docstring sections and any interface flags. It also reports names defined twice, names outside the naming pattern you give it, and modules that never declare `__all__`. Read the output before forming an opinion. A library's real surface is often not what its authors believe it is.

Find out who calls the API too: tests, examples, documents and downstream users. Each one tells you what a change will break.

## 2. Find hazards

Read the [hazard checklist](references/hazard-checklist.md), then scan:

```sh
python <this skill>/scripts/scan_hazards.py <source dir>
```

The scan reports patterns worth a look, not verdicts. Read each hit in context and decide. A clamp may be a documented physical limit or a hidden error. For each real finding write down the input that produces the wrong result. Run it if you can. A hazard you cannot demonstrate ranks below one you can.

The scan cannot find the most damaging class of hazard: a parameter whose meaning is unclear, or a unit the documentation does not state. Only reading finds those. The best way to find them is to watch someone else use the library; see [blind trials](references/verification.md#blind-trials).

## 3. Decide the conventions

Adopt the conventions of a mature library in the same field instead of inventing your own, and write down where you differ and why. See [conventions](references/conventions.md). The standard belongs in one document that the project's contributors already read.

## 4. Assign one truth to each fact

A fact stated in two places will eventually be wrong in one of them. For every fact your project records twice, choose the owner, then generate the other copy or check it automatically. Then add the check to the project's normal checks, so that disagreement fails the build:

```sh
python <this skill>/scripts/check_docs_sync.py <package> --src <source dir> --sections Parameters Returns Raises "See Also" Examples
```

See [single source of truth](references/single-source-of-truth.md).

## 5. Plan the changes

Rank by harm, then by reach, then by cost. Work in batches small enough to review. Do not mix a behaviour change with formatting or renaming. See [planning](references/planning.md).

If there is more mechanical work than you should do yourself, demonstrate the method on a few representative functions, then hand the rest over as written tasks with a method, a scope and a check that shows when each is done.

## 6. Change and verify

Each change needs evidence that would have failed before it: a test showing the old call now fails loudly, or a check that now covers the fact. Then ask whether a stranger can use the result. See [verification](references/verification.md).

Rules for every commit:

- Say what changed, why, what callers must do, and what was checked. See [commit messages](references/verification.md#commit-messages).
- Keep the explanation in the commit message. Do not add a change-log or summary file for one refactor.
- Never change a scientific or business result as a side effect of an interface change. If an interface change reveals a wrong result, stop and raise it as its own decision.
- When a check fails, find out why. Fix the code if the code is wrong and fix the check if the check is wrong, then rerun. Do not keep a failure you understand, and do not relax a check just to pass.

## 7. Stop

Say what you left undone. A short, honest list of remaining hazards is worth more than a large diff. See [when to stop](references/planning.md#when-to-stop).

## Scripts

All use only the standard library, take the target as arguments, and know nothing about any particular project. Each exits non-zero when it finds something to act on.

| Script | Purpose |
| --- | --- |
| `scripts/api_inventory.py` | List the public surface and its flags; compare it with a list of documented names |
| `scripts/scan_hazards.py` | Find code patterns that often hide silent behaviour, with a baseline so that only new hits fail |
| `scripts/check_docs_sync.py` | Check docstrings against signatures, required sections, unit notation, and runnable examples |
