---
name: scirel-acceptance
description: Run SciRel's local checks. Use before committing or pushing any change to this repository, after merging a candidate, and before saying a change is done. Maintainer skill; not delivered to users.
---

# Check a SciRel change

A change is done only when the checks here pass. Run them yourself; do not assume a hook ran them, and do not report a check you did not run.

## When to run what

The levels differ in what they prove, not in how strictly they check. Only the last two are
evidence, and they come from one step table filtered by `--stage`.

| Level | Who runs it | Command | Covers | Typical time |
| --- | --- | --- | --- | --- |
| Domain loop | the implementer, constantly | `python3 scripts/dev.py run python -B scripts/test_scope.py --changed <path>`, then the command it prints through `python3 scripts/dev.py pytest ...` | Only the tests of the domain being changed | Seconds |
| Development stage | whoever reviews a PR, before merging it | `python3 scripts/dev.py check --stage dev` | Every non-release test, contract schema and runtime signatures, contract sync, hazard scan, lint, format, lockfile | About 4 minutes (measured: 246 s) |
| Release stage, the default | whoever merges into `main`, and every outward delivery claim | `python3 scripts/dev.py check` | The development stage plus example execution, the documentation build, the wheel build and wheel exposure, and every release-only test | About 8-9 minutes (measured: 512.6 s before the split) |
| Before each commit | `git commit`; the hook runs `precommit_check.py` with the host `python3` | Private paths and secrets in staged text | Under a second |
| Optional cross-device spot check | Manually dispatch the `Cross-device check` workflow | The release stage on Linux/amd64 | About 5-15 minutes |

**The domain loop is not evidence.** A targeted `pytest` run proves only what its author chose to
run, so it never appears in a receipt and never stands in for either stage. Parallel or filtered
runs stay development feedback.

Measured on 2026-11-16 on the tree that shipped this split: the development stage takes 246 s
(241.4 s of it the `tests` step) with 8210 tests selected and 154 deselected, and ends `ALL
GREEN` on a clean commit. The release stage still costs the 512.6 s it cost before the split,
because none of its steps changed: the split added a faster path, it did not shorten the slow one.
Keeping `tests/tooling/test_validate_extraction_package.py` in the development stage costs about
33 s of that, which is the price of running the guard for this split in the stage it guards.

The development stage was also measured while `python3 scripts/dev.py pytest tests/kinetic -q`
ran concurrently in the same worktree. Both finished green — 2172 passed in the other run, 7/7
steps and the same selection here — so the shared level does not block a developer's run and did
not turn a failure into a pass. One measured overlap is not a proof for every pair of
runs, which is why the release stage keeps the exclusive lock.

The two stages take different lock levels of the same clone-wide lock. The release stage takes the
exclusive lock and prints `EXCLUSIVE`; the development stage takes the shared lock an ordinary
`pytest` run takes, so a developer's test run neither blocks it nor is blocked by it. A shared
holder still blocks an exclusive one, so stop a development run before starting a release one. The
development stage prints no `EXCLUSIVE` line, and that is one more reason its receipt cannot pass
for release evidence.

## What each stage proves

- **Development stage (`--stage dev`)** proves that this change holds at the unit,
  contract-consistency and static-check level, and that it did not break the parts of the suite it
  never touched. It does **not** prove that the package installs, that the documentation site
  builds, or that the documented examples run.
- **Release stage (default)** is the evidence that can be delivered: the whole suite, the executed
  examples, the built and inspected wheel, and the built documentation. Every batch merged into
  `main`, and every outward delivery claim, needs a release-stage receipt.
- **A development-stage receipt is not release evidence and must never be cited as one.** The
  receipt records its `stage`, so this is checkable rather than a promise:
  `scripts/validate_extraction_package.py` refuses a `stage: "dev"` result and tells the caller to
  rerun the release stage on the same candidate.

The development stage is faster because it proves less, not because the checks are looser: the steps
it keeps are the same checks with the same failure criteria, and the release stage is still exactly
the gate this repository already had.

### Which tests may be skipped, and why the list is a document

`release_only_tests.txt` next to this file lists the tests the development stage deselects, one
`<path or nodeid> | <reason>` line each. The rule for the list: a test belongs there when a failure
means the packaged or published product is wrong, and **not** when it means this change is wrong.
Anything unclear stays in the development stage. An entry also needs its reason written down: if you
cannot say why its failure does not mean "this change is wrong", it does not belong on the list.

Prefer a nodeid to a file in that list: a file entry takes every test in the file out of the
development stage, including a correctness test added later, and nothing fails when that happens.
The stale-entry check covers renamed and deleted tests, not added ones, so narrowing an entry is
the only safe way to add a correctness test to a file the list already names. A file that holds a
guard for this split itself — like `tests/tooling/test_validate_extraction_package.py`, which
holds the test that refuses a development-stage receipt — stays out of the list entirely.

The development stage deselects exactly that list, and the counts prove it rather than assert it:
the counts record carries `deselected_nodeids` (schema `3`), every deselected nodeid must belong to
an entry, and every entry must have deselected something — so a renamed or deleted test cannot leave
a stale exclusion behind. The release stage passes no `--deselect` at all and still requires
`deselected 0`.

`check_all.py` prints one line with both counts before its verdict, for example:

```text
steps 10/10 passed; tests collected 3021, selected 3021, deselected 0, passed 3019, failed 0, error 0, skipped 2, xfailed 0, xpassed 0 (skip reasons: Windows root component traversal (1); got empty parameter set for (report) (1))
SKIP  Windows root component traversal  (1): tests/delivery/test_solving_skill.py::test_windows_skill_root_cannot_have_a_redirected_ancestor
SKIP  got empty parameter set for (report)  (1): tests/tooling/test_solved_examples.py::test_example_reports_pass_the_validator[NOTSET]
ALL GREEN
```

`ALL GREEN` is the last line when everything passes. Any other ending means the tree is not green. The step count alone is not evidence: it says that ten steps exited zero, not what the tests did. A large skip would otherwise hide behind a passing exit code, so each skip reason gets its own `SKIP` line with its count and the first few test IDs.

The test counts come from pytest itself. `skills/development/scirel-acceptance/scripts/scirel_pytest_counts.py` (relative to the repository root) observes the run and changes no outcome; `check_all.py` loads it with `-p scirel_pytest_counts` and has it write JSON into the run's temporary directory. The standard result retains this record under `tests` before that directory is removed. Nothing is read from the human-readable summary. If that report is missing, unreadable, or its numbers disagree — every selected test must reach exactly one outcome, and `selected` must equal `passed + failed + error + skipped + xfailed + xpassed` — the `tests` step is red: a count nobody can check cannot support a green.

The counts record uses schema `3`. It preserves the complete ordered `selected_nodeids` and the
ordered `deselected_nodeids` of a run that deselected anything, and
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

The release stage also requires `deselected 0`; the development stage instead requires the
deselections to be exactly `release_only_tests.txt`. `dev.py` clears the host's `PYTEST_ADDOPTS` so a
personal test filter cannot reduce either stage. Pass filters explicitly to `dev.py pytest` for local
work, where they are development feedback and not evidence.

The complete check explicitly selects `tests/`, rather than accepting a different `testpaths`
from a candidate. It always retains each step's complete output and a `scirel.acceptance.v2`
JSON result under `.runtime/logs/`; `RESULT` prints its location. That result records its `stage`,
which is what lets a reader tell a development-stage receipt from a release-stage one. The extraction validator passes
`--report <path>` to preserve those records after deleting its temporary candidate tree. A green
exit without a complete result, or with zero executed tests, cannot support package admission.

The current `scirel.acceptance.v2` result also binds the following fields; older results lacking
them are rejected, not upgraded or reused:

- `stage` is `release` or `dev`. Admission requires `release`, and a result that carries no
  stage at all is refused as unusable rather than read as either. The field joined an existing
  `scirel.acceptance.v2` result without a version bump — the only reader refuses a v2 result
  without it, so an older v2 receipt fails loudly instead of being misread.
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

It prints the time of each step. The release stage takes about 8-9 minutes and the development
stage about 4; much longer means the machine is busy: look for other runs before suspecting the code. Only one run per checkout is allowed. Run it in the foreground, so that you see the result.

A push runs nothing: there is no `pre-push` hook, so pushing is cheap and proves nothing. The
complete check runs when you run it, on the commit you intend to merge. No result is reused: a tree is
green only for the commit that was checked.

The release stage runs the full test suite, contract signatures and examples, the docstring and
contract sync check, the scan for new hazard patterns, the documentation build, the report validator
on every solved example, the lockfile check, and a wheel build with its exposure check. The
development stage runs the same checks minus example execution and minus the three artifact steps
(`documentation build`, `wheel build`, `wheel exposure`), with the release-only tests deselected.

## 让检查结果能被复核

要当证据的那次检查，执行命令里不许接管道。写成 `python3 scripts/dev.py check > .runtime/check.log 2>&1; echo EXIT=$?`，先拿到真实退出码，再看日志里的细节。`a | b` 的退出码是 `b` 的，而 `tail`、`grep`、`tee` 正常结束一律返回 0，检查失败会被读成成功——#117 的批跑里就有人写成 `check 2>&1 | tail -20`，一次真实的失败报出了 0。管道留给事后读已经落盘的日志用（`tail -20 .runtime/check.log`），不要出现在执行检查的那一条命令里。

退出码非 0 时，把完整输出留下来再报，不要只贴尾部。`tail` 挑出来的那几行往往正好丢掉"哪一步失败、为什么失败"，评审拿到一段像成功的尾巴，比没有日志更难判。要看重点，也是在完整输出之外另附摘要，不能拿摘要替换输出。

这两条是同一个病根：为了看得方便，把判断依据裁掉了。而判断依据一裁掉就没有第二份能还原——这次运行同时会覆盖上一次的判定依据，重建的虚拟环境、wheel 和文档输出都已经是这一次的状态，事后只剩这一个退出码和这一份完整日志。收窄成几十行，等于把"这一次过没过"和"上一次是什么结论"一起丢掉；等到有人回头核对，既补不出当时的输出，也复现不出当时的结论。放行用的那次完整检查还必须独占本仓库的测试，见 `AGENTS.md` 的「环境和验收」段，这里不重复。

证据里要同时写两个计数：`steps N/M passed` 的步骤数，和 pytest 的测试计数（collected、selected、passed、failed、skipped，跳过写原因与条数）。只写步骤数就是"缺分母的成功"——三千条测试里跳过了多少、为什么跳过，读者看不到；而 pytest 只要退出码是 0，这一步同样算过。照 `check_all.py` 最后那几行原样贴（汇总行加 `SKIP` 行再加强末行），不要只摘一句 `ALL GREEN`。

## 变异验证：先说清"走没走到"，再说"红不红"

变异验证用来回答"这条证据测试是否承重"。它有一个前提，不写清楚就会得出反向结论：**被改的那一行在这次测试里到底执行了没有**。同一个"变异存活"有三种完全不同的解释，修法也相反：

- `covered` — 已证明执行、测试仍全绿。结论是"测试未约束该行为"，修法是**加强断言**（例如断言单调性、双值比较、量级关系）。
- `not-exercised` — 现有测试未覆盖该分支。结论是"这里没有测试"，修法是**补覆盖**（构造能把该分支逼出来的输入）。
- `equivalent` — 改动**语义等价**，任何测试都不可能杀死它。判定义务是**用代码阅读证明两处路径等价**（例如同一条件、同一消息的守卫在两条路径上各有一份，前置早退使活跃输入必然走到第二处），并在结论里指出重复守卫可以删除。**这类存活不是测试缺口，也不是"测试未约束该行为"**——把它归进 `covered` 会导出一条无法执行的待办（"加强断言"，而行为没变）。
- `UNKNOWN` — 插桩失败、副本崩溃、标记文件不可读。不作任何结论。

`equivalent` 与 `not-exercised` 的区别要写清楚：前者是"测试再强也杀不死"，后者是"测试还没走到"；两者都不能写成"不可达"。

判定这两件事本身都要能被验证：变异副本先用 `print(scirel.__file__)` 确认命中的是副本（只设 `PYTHONPATH` 会被 `pyproject.toml` 的 `pythonpath` 覆盖，得到假绿）；插桩要打**阳性对照**——同一副本里对一个必然执行的行也打标记并断言它出现，标记写文件而不是 stderr（pytest 会捕获并丢弃 stderr）。没有阳性对照，"标记为空"永远有两种解释。

**`not-exercised` 不得升级为"该分支不可达"。** 连续参数空间上的不可达性无法用采样证明，换一个人的输入就能推翻；本仓库因此误判过一次，差点按"死代码"删掉一段正确的可去奇点极限实现（把 `x` 附近的面板宽度降到 1e-9，那段分支命中 84 次）。要主张删除，必须给出**穷尽性论证**（例如该参数只能取有限集合），而不是"我这几组输入没走到"。

报告固定两栏：`mutants killed / total`，以及**每个存活变异**的覆盖判定。

## 单文件多记录的合并：逐条并集

`tools/docs/zh/*.json` 一个文件里有几十条资产记录，代码与合同的并行改动都落在同一个文件上，冲突几乎必然发生。解决这类冲突**不许整份取一侧**（`git checkout --theirs <file>`）：那样会把对方在这批里新增的记录整段退回旧文本，而且差异不会出现在任何代码里——只有 `check_contract_sync.py` 的"条款条数不符"能看出来。本仓库已因此静默退回两次（一次 45 条 reader 记录，一次 3 条）。

正确做法是**逐资产取并集**：按 `asset_id` 合并两侧记录，只让本批真正改过的资产采用本侧版本，其余保留对方的。合并后必须跑 `check_contract_sync.py`（它比对每条记录的条款条数），并用脚本逐条比对与 `origin/main` 的差异，确认"差异集合"恰好是本批改过的那些资产。

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
