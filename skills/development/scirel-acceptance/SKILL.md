---
name: scirel-acceptance
description: Run SciRel's local checks. Use before committing or pushing any change to this repository, after merging a candidate, and before saying a change is done. Maintainer skill; not delivered to users.
---

# Check a SciRel change

A change is done only when the checks here pass. Run them yourself; do not assume a hook ran them, and do not report a check you did not run.

## When to run what

| Moment | Command | What it covers | Time |
| --- | --- | --- | --- |
| While working | `python3 scripts/dev.py run python -B scripts/test_scope.py --changed <path>`, then run the command it prints through `python3 scripts/dev.py pytest ...` | The affected tests | Seconds to minutes |
| Before each commit | `git commit`; the hook runs `precommit_check.py` with the host `python3` | Private paths and secrets in staged text | Under a second |
| Before asking for review, and before saying a change is done | `python3 scripts/dev.py check` | Full local acceptance and merge evidence | About 5 minutes |
| Optional cross-device spot check | Manually dispatch the `Cross-device check` workflow | Same full acceptance on Linux/amd64 | About 5-15 minutes |

`check_all.py` prints one line with both counts before its verdict, for example:

```text
steps 10/10 passed; tests collected 3021, selected 3021, deselected 0, passed 3019, failed 0, error 0, skipped 2, xfailed 0, xpassed 0 (skip reasons: engine is not running (2))
SKIP  engine is not running  (2): tests/docs/test_build.py::test_live_build, tests/docs/test_build.py::test_live_links
ALL GREEN
```

`ALL GREEN` is the last line when everything passes. Any other ending means the tree is not green. The step count alone is not evidence: it says that ten steps exited zero, not what the tests did. A large skip would otherwise hide behind a passing exit code, so each skip reason gets its own `SKIP` line with its count and the first few test IDs.

The test counts come from pytest itself. `scripts/scirel_pytest_counts.py` observes the run and changes no outcome; `check_all.py` loads it with `-p scirel_pytest_counts` and has it write JSON into the run's temporary directory, which is removed with the run. Nothing is read from the human-readable summary. If that report is missing, unreadable, or its numbers disagree — every selected test must reach exactly one outcome, and `selected` must equal `passed + failed + error + skipped + xfailed + xpassed` — the `tests` step is red: a count nobody can check cannot support a green.

Full acceptance also requires `deselected 0`. `dev.py` clears the host's `PYTEST_ADDOPTS` so a
personal test filter cannot reduce the suite. Pass filters explicitly to `dev.py pytest` for local work.

It prints the time of each step and takes about five minutes. Much longer means the machine is busy: look for other runs before suspecting the code. Only one run per checkout is allowed. Run it in the foreground, so that you see the result.

A push runs nothing: there is no `pre-push` hook, so pushing is cheap and proves nothing. The
complete check runs when you run it, on the commit you intend to merge. No result is reused: a tree is
green only for the commit that was checked.

It runs the full test suite, contract signatures and examples, the docstring and contract sync check, the scan for new hazard patterns, the documentation build, the report validator on every solved example, the lockfile check, and a wheel build with its exposure check.

## 让检查结果能被复核

要当证据的那次检查，执行命令里不许接管道。写成 `python3 scripts/dev.py check > .runtime/check.log 2>&1; echo EXIT=$?`，先拿到真实退出码，再看日志里的细节。`a | b` 的退出码是 `b` 的，而 `tail`、`grep`、`tee` 正常结束一律返回 0，检查失败会被读成成功——#117 的批跑里就有人写成 `check 2>&1 | tail -20`，一次真实的失败报出了 0。管道留给事后读已经落盘的日志用（`tail -20 .runtime/check.log`），不要出现在执行检查的那一条命令里。

退出码非 0 时，把完整输出留下来再报，不要只贴尾部。`tail` 挑出来的那几行往往正好丢掉"哪一步失败、为什么失败"，评审拿到一段像成功的尾巴，比没有日志更难判。要看重点，也是在完整输出之外另附摘要，不能拿摘要替换输出。

这两条是同一个病根：为了看得方便，把判断依据裁掉了。而判断依据一裁掉就没有第二份能还原——这次运行同时会覆盖上一次的判定依据，重建的虚拟环境、wheel 和文档输出都已经是这一次的状态，事后只剩这一个退出码和这一份完整日志。收窄成几十行，等于把"这一次过没过"和"上一次是什么结论"一起丢掉；等到有人回头核对，既补不出当时的输出，也复现不出当时的结论。放行用的那次完整检查还必须独占本仓库的测试，见 `AGENTS.md` 的「环境和验收」段，这里不重复。

证据里要同时写两个计数：`steps N/M passed` 的步骤数，和 pytest 的测试计数（collected、selected、passed、failed、skipped，跳过写原因与条数）。只写步骤数就是"缺分母的成功"——三千条测试里跳过了多少、为什么跳过，读者看不到；而 pytest 只要退出码是 0，这一步同样算过。照 `check_all.py` 最后那几行原样贴（汇总行加 `SKIP` 行再加强末行），不要只摘一句 `ALL GREEN`。

## Docstring and contract: one source of truth

For each operator, the code signature and its numpydoc docstring are the source of truth for parameter names, order, defaults, units, return entries, raised exceptions and the example. The JSON contract keeps what is only for agents (model, scope, applicability, failure semantics, evidence, limitations), and its fields that overlap the docstring are derived from it. When you change one, change the other in the same commit.

`skills/development/scirel-acceptance/scripts/check_contract_sync.py` enforces this for the assets listed in `skills/development/scirel-acceptance/scripts/contract_sync_scope.json`: signature and input names, required flags and defaults; Parameters, Returns, Raises, See Also and Examples sections; every contract unit written as `[unit]` in the matching docstring entry; every exception in `failure_semantics` listed under Raises; Examples that run as doctests and are the same code as `example.code`; the Chinese reader record bound to the current contract; and phrases listed as stale for the asset. Add an asset to the scope list once its docstring passes; the goal is the whole catalog.

## Set up once per clone

```sh
python3 scripts/dev.py prepare
git config core.hooksPath .githooks
```

The host needs Git, a Python 3 launcher and uv. `prepare` installs the interpreter pinned in
`.python-version` into the project, then syncs the locked environment. Every run artifact stays inside the
project, under the ignored `.runtime/`: the main checkout's holds the managed Python, uv cache and the
clone-wide check lock that all worktrees share, and each worktree's own holds its virtual environment,
bytecode, ruff cache and temporary directory. `dev.py` sets those locations, so run commands through it
(`run`, `pytest`, `check`) rather than the host's `python` or a bare `uv run`. `doctor` lists every location.

The `pre-commit` hook scans staged text on the host, with the host `python3 -I`, the standard library and
`git` only; it needs no project environment, so a documentation commit works before `prepare`. It does
not run lint or format: those belong to the complete check, where they gate what is merged rather than what
is saved. Hooks are a safety net, not a replacement for running the checks yourself. Do not bypass them with
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
python3 scripts/dev.py run uv build --wheel --out-dir .runtime/tmp/wheel
python3 scripts/dev.py run python -B scripts/build_pure_delivery.py --wheel .runtime/tmp/wheel/scirel-*.whl --output <new-dir>
```

Skills under `skills/development/usage/` are what users' agents receive. `scirel-outbound-evaluation` covers testing them.

## What these checks do not establish

They confirm structure, regressions and bindings. They do not establish that the physics is right. Scientific review is recorded in `catalog/review/`, and status changes need a human decision.
