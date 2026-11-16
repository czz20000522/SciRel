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
steps 10/10 passed; tests collected 3021, selected 3021, deselected 0, passed 3019, failed 0, error 0, skipped 2, xfailed 0, xpassed 0 (skip reasons: Windows root component traversal (1); got empty parameter set for (report) (1))
SKIP  Windows root component traversal  (1): tests/delivery/test_solving_skill.py::test_windows_skill_root_cannot_have_a_redirected_ancestor
SKIP  got empty parameter set for (report)  (1): tests/tooling/test_solved_examples.py::test_example_reports_pass_the_validator[NOTSET]
ALL GREEN
```

`ALL GREEN` is the last line when everything passes. Any other ending means the tree is not green. The step count alone is not evidence: it says that ten steps exited zero, not what the tests did. A large skip would otherwise hide behind a passing exit code, so each skip reason gets its own `SKIP` line with its count and the first few test IDs.

The test counts come from pytest itself. `skills/development/scirel-acceptance/scripts/scirel_pytest_counts.py` (relative to the repository root) observes the run and changes no outcome; `check_all.py` loads it with `-p scirel_pytest_counts` and has it write JSON into the run's temporary directory. The standard result retains this record under `tests` before that directory is removed. Nothing is read from the human-readable summary. If that report is missing, unreadable, or its numbers disagree — every selected test must reach exactly one outcome, and `selected` must equal `passed + failed + error + skipped + xfailed + xpassed` — the `tests` step is red: a count nobody can check cannot support a green.

The counts record uses schema `2`. It preserves the complete ordered `selected_nodeids` and
one entry per selection in `results`, with its `nodeid`, final `outcome` and observed `phases`.
Each phase records `when` (`setup`, `call`, `teardown`), pytest's raw `outcome`, `wasxfail`
when present, and the existing skip reason for skipped phases. The reader checks identities,
uniqueness, phase order/completeness, phase-derived final outcomes, every total and skip reason,
and the pytest exit status against the subprocess result. Missing fields and old count schemas
are rejected; a separate collect-only run cannot supply missing identities for this run.

The result file carries schema `scirel.acceptance.v2` and records what produced it: the
`sha256` of the exclusive credential token (never the token, which retires before the lock
is released), one `log_sha256` per retained step log, the digests of `check_all.py` and
`scirel_pytest_counts.py`, and a `<report>.sha256` sidecar holding the digest of the result
file itself; the run prints `RESULT SHA256 <hex>`. A reader refuses a v2 result whose
credential digest, log digest, script digest or sidecar is missing or disagrees.

What that buys, stated exactly: v2 binds the result file to the run that wrote it. Every
step log has a recorded digest and the sidecar covers the result bytes, so editing the
result — or one log — is visible without redoing the run. **The credential digest binds too,
but only when the verifier holds the live token:** `validate_provenance(..., token=…)`
requires `sha256(token)` to equal the recorded `exclusive.token_sha256`, and
`run_full_check()` passes the credential it already re-verified, so a result produced under
another run — or by someone who never held the lock — is refused with *recorded credential
digest does not match this run's live token*. Called without a token, the function can only
check the shape: **format validation is not binding.**

**This is still not a signature.** Anyone who can rewrite the result, every log and the
sidecar together can build a self-consistent bundle; what they cannot do is make the
recorded digest equal the live token held by the verifier. Removing that last gap needs
verification moved outside the clone, which is a separate decision and not part of this
protocol.

Three review consequences follow from that boundary:

1. **An edited script invalidates its receipts.** Any change to `check_all.py` or
   `scirel_pytest_counts.py` makes every earlier v2 receipt fail with
   `check_all_sha256 disagrees`; the answer is a new run, never a repaired receipt.
2. **`validate_provenance` does not compare step count or names.** Binding steps to a plan
   is the caller's duty; `validate_extraction_package.py` does it against the candidate plan.
3. **The measured matrix keeps its ACCEPTED cells, and they are not the same cell.** Re-seal
   the sidecar after changing a field → `ACCEPTED` **only when no live token is supplied**;
   the same forgery against the token of the run being verified → `REFUSED`. That is the
   whole difference between shape validation and binding.

A `scirel.acceptance.v1` receipt predates all of this. It is **refused by default**: a fresh
forgery and a genuine historical receipt are indistinguishable, and there is only one legal
shape for delivered evidence. `--allow-legacy-receipts` reads one for archaeology only and
prints `legacy receipt accepted for archaeology only, not as evidence`.

A setup or teardown failure gives the item final outcome `error`; otherwise a call failure
gives `failed`, followed in priority by `xfailed`, `skipped`, `xpassed`, `passed`. A strict XPASS
remains pytest's call failure. Each selected item counts once, so a passed/failed call followed
by a teardown error counts as one `error`; both phase observations remain available. Setup
skips and `xfail(run=False)` have no call phase and do not prove test-body execution. Even a
call phase alone does not establish that a test body completed successfully.

`collection_finished` and non-passing `collection_reports` retain collection state separately
from selected-test outcomes. Incomplete items have final outcome `null` and keep the phases
already observed. Collection failure, interruption, duplicate identities or phases, missing
results and inconsistent records fail the step. Readable rejected records remain under `tests`
for diagnosis, with the result marked invalid; they are never used to print a trusted summary.

Full acceptance also requires `deselected 0`. `dev.py` clears the host's `PYTEST_ADDOPTS` so a
personal test filter cannot reduce the suite. Pass filters explicitly to `dev.py pytest` for local work.

The complete check explicitly selects `tests/`, rather than accepting a different `testpaths`
from a candidate. It always retains each step's complete output and a `scirel.acceptance.v1`
JSON result under `.runtime/logs/`; `RESULT` prints its location. The extraction validator passes
`--report <path>` to preserve those records after deleting its temporary candidate tree. A green
exit without a complete result, or with zero executed tests, cannot support package admission.

The current `scirel.acceptance.v1` result also binds the following fields; older results lacking
them are rejected, not upgraded or reused:

- `run_id` identifies this invocation. The extraction validator supplies a fresh ID and a new
  result filename for each run, and checks both. `--report` refuses an existing file, so a
  failed or interrupted run cannot inherit a previous green result.
- `candidate.before` and `candidate.after` contain the actual `commit`, HEAD `tree`, `dirty`
  flag and `worktree_sha256`. The last field hashes Git status, staged and working changes,
  and untracked file contents; those names and contents are not copied into the result.
  A change to any identity field fails the run, including a different commit with the same
  tree or a content change while the worktree stays dirty.
- `environment.before` and `environment.after` contain only Python implementation/version,
  platform, architecture, `uv_lock_sha256` and `python_version_sha256`. These SHA-256 digests
  identify the exact bytes of `uv.lock` and `.python-version`. Missing identity or unreadable
  dependency inputs fail the binding; changed environment inputs also fail the run. The
  result does not collect environment variables, hostnames, email addresses or credentials.
- Each step retains its `argv` and `started` flag alongside its status, exit code and full
  output log. `argv` is the argument list passed to the subprocess, or the planned list when
  it could not start. Missing uv or a failed spawn means `started: false`, `NOT_RUN` and a
  null return code. A started, interrupted step fails; later steps are `NOT_RUN`.
- `evidence` is `clean_candidate`, `development` or `invalid`, and `binding_errors` retains
  identification failures. Stable dirty runs can exit zero as development feedback, ending
  with `DEVELOPMENT PASS (dirty candidate)` rather than `ALL GREEN`; they cannot support
  package admission. A failed step or binding failure sets `exit_code: 1` and `invalid`.

The extraction validator observes the real candidate before and after its run, **after
`git am`**, and compares both observations with the fresh result. The frozen base commit is
not the candidate identity. It also checks the actual candidate's step plan and argument lists,
started flags, retained logs and unchanged environment. Missing fields, stale IDs, mismatched
commits, dirty candidates and identity drift are rejected. Counts still retain every outcome
and skip reason: at least one `passed`, `failed` or `xpassed` outcome is required to demonstrate
execution. All-skipped, all-error or solely `xfailed` results cannot establish it; pytest can
record `xfailed` without calling a test body (`xfail(run=False)`).

The result bindings alone do not establish clone-wide exclusivity. `dev.py check` and the
explicit `dev.py run --exclusive <command>` entry acquire the existing clone-wide EX lock
and print `EXCLUSIVE`. Ordinary `run`, `prepare` and `pytest` keep their shared lock.
For complete extraction-package validation, run from the clone containing the frozen commit:

```sh
python3 scripts/dev.py run --exclusive python -B scripts/validate_extraction_package.py <package> --repo .
```

The outer entry holds the lock across patch application, the candidate's direct `check_all.py`
call and mutation. The validator verifies the candidate's actual Git common directory, a fresh
credential under the existing `.runtime/locks/`, and the live kernel lock before and after both
checks, retaining the same credential throughout. On POSIX an independent shared-lock probe
must be blocked; a shared holder cannot satisfy it. Windows probes the existing serialized
byte lock. Bare environment values, retired credentials, free/shared locks and a different
clone are rejected. Ordinary commands clear inherited exclusive markers and stale records;
credentials are retired under the original lock after the command group has exited, including
on interruption. This is verification of the outer lock, not permission to reacquire or bypass
it. Do not nest `dev.py check` inside `dev.py run`; the locks conflict. A direct `check_all.py`
invocation alone is still not evidence of exclusivity. `--fast` skips admission and exits 2
for an otherwise valid package.

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

`skills/development/scirel-acceptance/scripts/check_contract_sync.py` enforces this for every public asset derived directly from `catalog/examples/`: signature and input names, required flags and defaults; Parameters, Returns, Raises, See Also and Examples sections; every contract unit written as `[unit]` in the matching docstring entry; every exception in `failure_semantics` listed under Raises; Examples that run as doctests and are the same code as `example.code`; the Chinese reader record bound to the current contract; translated clause counts and unknown keys; and phrases listed as stale for the asset. Optional positional asset IDs select local checks; unknown IDs, an empty selection and a missing or empty catalog fail. `--rules` selects `skills/development/scirel-acceptance/scripts/contract_sync_rules.json` by default. It holds only asset-specific stale-phrase options, never a checked-asset list; unknown or duplicate rule IDs fail.

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

Checks only tighten.

- Contract synchronization covers the entire public catalog automatically. Do not exclude an asset or weaken any existing field check to pass. The asset-specific stale-phrase rules in `skills/development/scirel-acceptance/scripts/contract_sync_rules.json` remain enforced independently of coverage; removing an option-free row cannot remove an asset from checking.
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
