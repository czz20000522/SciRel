# SciRel current handoff

The durable architecture boundary for source behavior graphs, public
compositions, user-owned task graphs and scale-aware static retrieval is
[`ARCHITECTURE.md`](ARCHITECTURE.md). Read it with `RULES.md` before changing
the contract, consumer query surface or decomposition handoff.

## 2026-10-29 ten-case demonstration capability closure

The ten demonstration problem contracts were clarified before the final clean
run. q02 now states the signed-frequency convention, q04 treats the supplied
response tables as complete inputs, q05 states its finite topology scope, q06
states the fixed atomic-only slab configuration, q07 states that its outputs
are determined by the finite geometry/mask, q10 states the fixed finite-grid
and bounded-nonconvergence protocol; q03 no longer carries an unrelated
polarization requirement, and q09 has the standard problem/output/acceptance
projection files.

Three reusable public compositions were merged for the formerly mismatched
cases:

- `scirel.kinetic.simulate_sat123` for the ten SAT1/SAT2/SAT3 scenarios,
  shear shift, geometry projection, signed spectra and interval integration;
- `scirel.kinetic.solve_atomic_slab_transport` for the fixed finite velocity
  mesh, boundary normalization, ionization/CX/recombination rates, repeated
  generation propagation and moment reduction;
- `scirel.equilibrium.solve_finite_frc_feedback` for the fixed finite-grid FRC
  Green/coil composition and explicit bounded feedback diagnostics.

The clean outbound run `clean-agent-run-20261029-v2` used only the revised
cases and a current public-package snapshot. It did not read reference
answers, hidden oracle, historical glue, receiver roadmap or source archives.
All ten cases completed with observable per-case traces; q04, q06 and q10 now
resolve through the public APIs. q06 retains `max_generations` when the fixed
input does not satisfy the truncation threshold, and q10 retains
`converged=false/maxiter_reached`; neither state is rewritten as scientific
acceptance. The v2 audit and intake are in the external challenge artifact
directory. Current domain tests passed after the additions (1360 passed, 3
skipped, 2 warnings); the four direct new/changed tests also pass.

This closes the engineering/outbound capability gap for the ten contracts. It
does not approve scientific validity, physical applicability, source rights or
release. The remaining user-owned presentation code is glue and stays outside
SciReL core.

## 2026-10-27 Windows tooling failure closure

Implementation commit `0bee05b3` closes all 46 previously recorded
delivery/tooling failures. The affected architecture/docs/delivery/tooling run
was **721 passed, two unchanged optional MCP SDK transport checks not run**.
After fast-forwarding the reviewed bytes into the canonical Windows checkout,
43 focused checks passed there, including current contract examples and the
CLI/MCP path boundary. These scopes overlap and are not additive.

Skill capture now uses anchored native Windows handles and rejects reparse
points before reading; the POSIX descriptor path remains intact. Five bounded
POSIX loader probes passed. Consumer CLI output is explicitly UTF-8, preserving
its byte budget, and CLI/MCP retain lexical roots for the common validator.
Archive checks inspect original ZIP names before normalization. Windows tests
use actual file reparse points and directory junctions without changing host
privileges; POSIX retains real symlinks. No old failure became a skip.

Two current mapping-interface source digests were stale after the existing
`576ee4c9` validation guards. Their registry entries now match the unchanged
implementation; all 14 records and 70 module bindings were checked. This batch
changes no scientific implementation, public scientific port, numerical
assertion/tolerance or frozen evidence, and adds no dependency. Scientific,
rights, publication and release acceptance remain separate.

The older docs setup and generic tooling failures recorded below describe the
receiver's earlier revision and are superseded by this engineering repair;
their historical receipts remain unchanged. The independent outbound attempt
retains its own earlier source identity rather than claiming this revision ran.

## 2026-10-27 bounded empirical stopping increment

Added one independent leaf in the existing collisions domain:
`scirel.collisions.fast-ion-stopping-increment`, exported as
`evaluate_fast_ion_stopping_increment`. The public catalog now has 250 assets;
the existing single human-review hold remains separate and unchanged.

This is evaluation of a specified empirical expression with fixed y=0.6, not
total stopping, attenuation, deposition, geometry or time evolution. The power
port is explicitly local volumetric deposition density in W/m^3: a supplied
total-W metadata label was corrected without changing formula, constants or
fixture numbers. The caller supplies magnetic-axis birth-pitch cosine and
slowing time. Toroidal/full-local-field pitch equivalence, calibration range,
fit error, arbitrary species validity and application effects are unestablished.
Human scientific acceptance remains pending; development expression admission
does not close those limits.

Windows Python 3.14.7 / NumPy 2.5.4 is now available in the canonical local
`.venv`. The original neutral packet's seven tests passed; its complete frozen
56-case/37-row source-behavior comparison passed, retaining the original
5e-12/1e-300 criteria and all exceptional cases. The normalized library has 70
passing direct tests, including those 56 fixtures, the original seven behavioral
assertions and independent high-precision expression/scaling checks. The
affected collisions plus known neutral-transport cross-domain scope was 507
passed and one xfailed. All 250 contracts and mechanical review bindings passed.
Those scopes bind different packet/product identities and must not be merged
into a physical-qualification count.

Both reader languages, handbook topics and authored tutorial sections are
synchronized. The actual scalar example is (1,1), float64,
1.9645775636530587e-18 m^2. Two Windows renderer keys now use POSIX paths in
both language pipelines, fixing generated HTML routes. Documentation tests are
92 passed and one setup failure: Windows WinError 1314 prevents creation of the
symlink needed by that remaining boundary test. Its failure was preserved.
The initial broader generic run also retains failures in unchanged pure-consumer
and skill-export tooling, plus the previously recorded multi-coil complex-mapping
binding check. No unrelated export, source evidence or tolerance was repaired.

The main coordinator owns concurrent admission validator/producer/exporter,
contract and related test changes; this batch does not stage them. Source
identity and global dirty state must be read live. Public source query, runtime
signature and the new example were executed successfully. No scientific
approval, source-application parity, wheel, publication or release was performed.
The next owner is the main coordinator for independent review of this source
batch before a separate outbound session uses public capabilities only.

## 2026-10-26 skill lifecycle and residue cleanup

The development package now has one executable artifact closeout reference at
`skills/development/references/artifact-lifecycle-closeout.md`. The cleanup
route uses it together with `catalog/RECORDS.md`, separates process records,
current results, temporary runtime products and frozen deliveries, and
requires exact disposition plus filesystem/Git/consumer readback. Stale skill
links were rebound to the current contracts and record policy; SciRel's
development route no longer asks for AOCI maintenance. The tracked policy
change is `fe87dddf` (`DOC: close artifact lifecycle and cleanup loop`).

The cleanup pass retired 42 exact targets: the stale 247-asset `.runtime`
documentation snapshot, superseded 2026-10-22 documentation/review snapshots,
synthetic query-maintenance output, package metadata scratch, an empty
maintenance directory, repository `.DS_Store` files and project
`__pycache__` directories. The safe-delete plan covered 4,788 files and
143,241,495 logical bytes; its apply receipt is outside the repository. The
canonical development `.venv` was retained. The remaining `dist` roots are
intentional: `acceptance/` (project acceptance), `reference-truth/` (external
oracle used by acceptance evidence), `famou-pure-20261022-20afa0cc/` (private
immutable integration delivery), and `contract-semantic-audit-20261023/`
(open remediation evidence). These retained roots are historical or frozen,
not the current source baseline.

The affected architecture/docs/tooling run recreated 21 source-package cache
directories; a second exact safe-delete pass removed 136 files and 1,180,676
logical bytes. The final readback has no project `__pycache__` directories.

The current source identity is always the live output of `git rev-parse HEAD`
and `git status --porcelain`; the preceding closeout commit was
`d370651bc087862a5aba19db8bf5b0d1940ab896`, and this handoff refresh
supersedes it as the clean baseline.
The public catalog is 249 assets, with one human-review hold
`scirel.inference.direct-anisotropic-inversion`. Docs tests and asset schema
validation passed; the affected architecture/docs/tooling scope was 361
passed with one pre-existing failure in the multi-coil-vacuum-field complex
mapping binding check. Full suite, wheel, platform, release, rights and
human-scientific acceptance remain `NOT_RUN` unless a future task explicitly
opens those gates.

## 2026-10-25 modal numerics integration batch

Integrated the admitted reference-cell orthonormal modal basis and modal
projection capabilities under `scirel.numerics`. The public catalog is now 249
assets (the existing human-review hold remains separate); contracts, direct
tests, bilingual API reader records, handbook navigation, package exports,
license notice and mechanical verdict bindings are synchronized. The bounded
checks passed: 122 direct numerical tests, 210 architecture tests, 33 core docs
tests, 13 English-site tests and 168 delivery tests (2 skipped); the standalone
documentation snapshot build and asset validation also passed. No wheel,
`dist/`, frozen case or deployment artifact was changed. The tooling suite has
one pre-existing unrelated failure in the multi-coil-vacuum-field complex
mapping binding check; it is retained as `NOT_RUN` for this batch's scope.

Read `AGENTS.md`, `RULES.md`, `catalog/README.md`, and
`tools/docs/manual/README.md` before changing this checkout. The unique checkout
is `/Users/tomczz/Projects/SciReL`; use `git rev-parse HEAD` and `git status` for
current identity. Historical checkpoints and resolved work remain in Git.

## Current baseline and next outbound entry

This batch started from a clean `d9ca1001`; the 2026-10-26 baseline recheck was
`b49ab1ac3bfb4710349f490af1009485543a17cc` with a clean worktree. Read the
current identity live with `git rev-parse HEAD` and `git status` before acting.
The bounded maintenance gate is canonical in
[`RULES.md` section 12](RULES.md#12-baseline-and-outbound-batch-gate), and the
outbound worker entry is `skills/development/usage/scirel-solving/SKILL.md`.
This batch records the gate only; it does not rebuild a wheel, alter a frozen
case/package, or start a new scientific run.

The first candidate workflow for the next authorized user task is **axisymmetric
vacuum coil-field evaluation**: discover public field/geometry contracts, select
the complete contract, state any grid aggregation as explicit glue, execute in a
task-owned environment, read back field/profile artifacts, then independently
check symmetry/limit/shape constraints. Its status is `source-backed development
execution COMPLETE` here; `wheel-Famou acceptance NOT_RUN`. The completed task
used 84 already-expanded circular-filament inputs; the rectangular
`coils-to-filament` requirement is `NOT_READY` for this input. Scientific
correctness, rights, and human acceptance remain separate from structural
admission.

## Current public boundary

- Public capabilities: **249**; current contracts are `catalog/examples/`.
- Human-review hold: **1**, `scirel.inference.direct-anisotropic-inversion`.
  Its implementation and contract remain in the review tree and are excluded
  from the installed package, discovery index, API pages and runnable tutorials.
  Restore/bind the exact admitted direct graph artifact and rerun direct
  composition/physical closure before reconsidering the hold.
- The diagnostics/inference authored chapter references that unavailable API.
  Both language sites therefore show an explicit subset placeholder for this
  chapter. Do not count it as delivered runnable tutorial coverage.
- Source-based acceptance and scientific evidence remain in the existing
  catalog review records; do not infer scientific approval from test counts.

## Private consumer delivery

The formal consumer protocol and maintenance sequence are
`tools/docs/PURE_CONSUMPTION.md`. One standard-library query/Consumer core serves
four read-only tools (`describe`, `browse`, `search`, `get`) through the official MCP SDK over stdio and
Streamable HTTP. Computation stays in user Python with the installed wheel.
SDK dependencies are separately locked; scientific dependencies remain NumPy,
SciPy and mpmath on Python `>=3.14,<3.15`.

At an explicitly authorized integration checkpoint,
`scripts/build_pure_delivery.py --wheel PATH --output NEW_ROOT` exports one Agent
runtime from a clean source revision and exact wheel. It derives the lightweight
index directly from public contracts and bound Chinese sidecars, checks the
public set and source/wheel bytes, and binds the actual runtime inputs and
internal skill reference closure. It does not need a documentation snapshot,
Sphinx or HTML generation. Human API/tutorial/site generation remains the
independent `scripts/scirel_docs.py build` pipeline, with its documentation
bindings, examples, links and resources. Never overwrite an existing immutable
bundle.

The only outbound skill is the ignored local
`skills/development/usage/scirel-solving/SKILL.md`. The internal entry reads its
method notes as needed; the exporter copies the reachable internal references
and helpers unchanged under `skills/scirel-solving/`. Cross-skill references are
rejected. All used bytes are bound because Git SHA alone does not cover ignored
local skills. The exported `tools/query.py` is the real standard-library CLI;
MCP is optional and uses the same dispatch. `runtime.json` contains only generated
runtime identity, pins and member integrity. `get` returns one complete original
JSON contract with its byte digest and path; it has no language selector or
embedded Markdown, and the browse/search card budget does not truncate it.
The runtime contains no API/tutorial Markdown, tutorial index or human site
assets. Human reading is optional and uses only separately supplied actual
site/version/path bindings; no URL or “latest” wheel match is inferred.
Build checks remain internal; no
delivery receipts or separate protocol/quickstart are required at runtime.
Daily source discovery uses `scripts/scirel_docs.py query --source-root .`; it
needs no wheel or pure build, shares the delivery query core and binds current
public inputs rather than inventing an installed-wheel receipt.
The current structured-runtime batch record holds scope, candidate, verification
and cleanup:
https://app.notion.com/p/4011c0206a8781aeb2ccf15955414772

MCP retrieval does not establish physical applicability or composition. Keep
snapshot/wheel pins and continuation identity. Unknown ports/units/relations
remain unknown. Do not call a held implementation as glue. Disclose and verify
any scientific glue using only public inputs.

## Verification and recovery

Select tests with `scripts/test_scope.py --changed PATH...`, then run local and
affected domains/layers. No default wheel/release/full-suite work outside an
explicit checkpoint. Exact-wheel inspection is
`scripts/check_wheel_exposure.py --wheel PATH --source-root src`; it is static
and does not replace installed import/call verification.

Private technical integration is not public release, legal acceptance or
Famou/Linux validation. Keep `NOT_RUN`/`NOT_DEPLOYED` for unexecuted targets.
Authored tutorial dependency hashes are traceability; natural-language science
review is not inferred from generation. Existing execution-bound standalone
chapters and other hand-authored RST have distinct evidence scopes.

Record locations, retirement and actual task cleanup follow the single policy
`catalog/RECORDS.md`. Keep this entry current; history remains in Git and Notion.

## 2026-10-28 SciRel public runner / settlement continuation

接替旧 runtime-engineering 会话后，当前 SciRel-only outbound runtime 交接已收口到以下事实：

- 独立边界仍为 `D:/software/JetBrains/python_workspace/SciRel-runtime`、WSL `/srv/scirel/.runtime`、containerd namespace `scirel`、BuildKit builder `scirel-buildkit`。CodeFusion runtime、locks、cache、output 与 `codefusion*` namespace 禁止读取、挂载、检查、清理或复用。
- 外部准备包 `E:/SciRel-lab/_shared/outbound/portfolio-20261027/results/unified-sciRel-runtime-p0-20261028/` 新增 `scirel_runtime_runner.py`、`22_SCIREL_PUBLIC_RUNNER_CONTRACT.md`、`23_SCIREL_PUBLIC_RUNNER_CHECK.json`、`24_SCIREL_PUBLIC_RUNNER_CLOSURE.json`。runner 是标准库实现：在 CID 创建前校验 SciRel roots、manifest/资源限制、request/manifest hash、fresh census <=300 s、immutable image digest、exact wheel hash 和一次性授权；运行只接受单请求/单结果；settlement 先写 pre-cleanup receipt，再只处理精确 CID 并读回 CID 缺失。
- 既有 `16_SCIREL_RUNTIME_PREPARATION_CLOSURE.json` 的 stale manifest bytes/hash 已修复；`16`、`17-21_TEN_TASK_RUNTIME.sha256`、`21_TEN_TASK_RUNTIME_CLOSURE.json` 与 `24` 已逐成员读回一致。
- 当前证据：runner/manifest/settlement static design `PASS`；immutable image `UNBOUND`、exact wheel `UNBOUND`、fresh census `NOT_RUN`、Linux cgroup/network/CID execution `NOT_RUN`、cleanup settlement `DESIGNED_NOT_RUN`、scientific acceptance `NOT_ASSESSED`。

下一步：由独立 Linux/amd64 owner 提供本地 immutable image digest、exact wheel binding 和 fresh census，生成一次性 exact authorization；完成 bounded preflight/cgroup/network/CID readback 后，才可启动单个真实任务。未满足前置条件时保持 BLOCKED/NOT_RUN，不运行科学，不改写历史 receipt。

## 2026-10-29 P0 outbound successor sealed preparation

The current outbound successor re-read the public SciReL surface and sealed a new ten-case request from the neutral scaffold. The final source binding, public input digest and contract count are retained in the sealed evidence below; the old 250-asset scaffold identity is stale and was not reused.

Capability discovery for all ten neutral cases, including candidate-003 masked toroidal volume, candidate-005 relativistic co-drift spectrum, candidate-006 A03/A05/A06, and the now-public candidate-004 discrete feedback primitive, is retained at `E:/SciRel-lab/_shared/operations/demo-targeted-extraction/coordinator/p0-demo-20261028/outbound-sealed-20261029/capability-discovery-20261029.json`. Each case records reusable public assets, explicit glue, and uncovered relations; glue is not counted as SciReL capability and science acceptance remains pending human review.

The current sealed request and manifest are `sealed-request.json` (SHA-256 `72252768ae37f80841762e966d99cb34f15b06ac4c1d9360a01ee5a4a361c439`) and `current-manifest.json` (SHA-256 `6bfc5cd6905e5b251c4c80469a3522df4955a199fb50e3b843a53adaf456abd9`). The fresh census is `fresh-census-20261029.json`; its decision is `BLOCKED_NO_EXECUTION`: the SciRel-only WSL runtime root and required containerd/BuildKit sockets were not observable, Docker daemon/buildx were unavailable, and immutable image, exact wheel, and one-use grant were unbound. No case started, no public API was called, and no scientific result or acceptance claim was made. The next action is an independent current image digest, exact wheel hash, fresh <=300 s census, then a new exact single-use grant before reviewing `benchmark-magnetic-001` for execution.


## 2026-10-29 SciRel endpoint repair diagnostic

A bounded host/provider read-only diagnostic was completed for the SciRel runtime boundary. The Windows Docker Desktop `desktop-linux` context was unreachable; `docker version` could not connect and `docker buildx ls` reported both builders as error. WSL remained running.

The allowed `/srv/scirel/.runtime` root existed, but the expected containerd and BuildKit sockets were absent. Five containerd processes shared the same SciRel root/state; two duplicate owners exposed `/tmp/scirel-p0.sock`, and the current SciRel log reported waiting for BoltDB open. The only alternate containerd/BuildKit listeners were under `/tmp/scirel-p0-runtime`, outside the allowed root, and were explicitly classified as non-reusable. No CodeFusion runtime was read.

Static repair only: added `D:/software/JetBrains/python_workspace/SciRel-runtime/endpoint-guard-v004.sh` and wired `start-new-boundary.sh` through pre-start/post-start fail-closed checks. Bash syntax checks passed; current pre-start correctly fails with `containerd_duplicate_processes`. No process was killed, no WSL restart occurred, and no daemon/container/scientific task was started.

Fresh diagnostic evidence is `E:/SciRel-lab/_shared/operations/demo-targeted-extraction/coordinator/p0-demo-20261028/outbound-sealed-20261029/fresh-census-20261029-endpoint-repair-r3.json` (SHA-256 `e4965547c0833a8600e8bcd2ae790e17b97ae8c77c82282b21174ce91fb940a8`), with summary `endpoint-repair-20261029-r3.json` (SHA-256 `d84ae34360d9534b59657845ba2dff040dd56108c8be33ec93aac6f2c6672a73`). Decision remains `BLOCKED_NO_EXECUTION`; immutable image, exact wheel, fresh grant and exact request are unbound/not generated. The next owner must perform an explicitly authorized SciRel-only runtime reset, restore the expected sockets, then capture a new <=300-second census before issuing a single-use grant.

## 2026-10-29 Docker provider boundary rebind

Docker Desktop context `desktop-linux` is now available as a Linux/amd64 Engine; Docker Buildx node `desktop-linux` is running with BuildKit v0.34.0. The physical BuildKit namespace is Docker-owned `moby`; the logical SciRel boundary remains labels `scirel` and `scirel-buildkit`. The provider adapter no longer requires the missing legacy `/srv/scirel` sockets.

A non-scientific bounded preflight used local image digest `sha256:82c07562f5217250593cea9c86938cc741dfa89b61dca98753cc7ef056c62e19` with `--pull=never`. It created one labeled CID, mounted only the preflight script read-only and one owned results directory, used network none, 2 CPUs, 4 GiB memory, 4 GiB memory-swap, pids 128 and read-only rootfs, then exited 0. In-container readback passed `cpu.max=200000 100000`, `memory.max=4294967296`, `memory.swap.max=0`, `pids.max=128`, interfaces `lo`; exact CID removal and absence readback passed. No scientific API or case ran, and no existing running service was interrupted.

Evidence:

- `E:/SciRel-lab/_shared/operations/demo-targeted-extraction/coordinator/p0-demo-20261028/outbound-sealed-20261029/provider-fresh-census-20261029-r2.json` SHA-256 `48d08b79d4d920dd1325d4fbeac79eee68dd86aeefc51455e4c0e83ce2db8695`
- `provider-boundary-20261029-r2.json` SHA-256 `13095f24f7e63201b27f192bea83918eadeee5e2d79aca90d81958c1eefd7ada`
- `provider-readiness-20261029-r2.json` SHA-256 `040bbee1d2f0d22b16462caba652d6d2806996dd645f30c466bb7d0c9ae37efc`
- `provider-exact-request-preparation-20261029-r2.json` SHA-256 `62a409811c19388c48230329d385973bd8b4ab823b50a13f5e3fce9f99d96e59`
- `docker-provider-adapter-contract-20261029.md` SHA-256 `e39088e886e9bcc05dcdbf47de1de7ecac628ffc429b9a6f0793c6b45e3e69ae`

Provider readiness is `PASS_FOR_BOUNDED_PREFLIGHT`; outbound exact request remains `BLOCKED_NOT_GENERATED` until a current outbound image digest, exact wheel hash and fresh single-use grant are bound. The minimum outbound entry is `provider-exact-request-preparation-20261029-r2.json`. CodeFusion paths/namespaces remain forbidden; no old grant was reused.

## 2026-10-29 Unified ten-case demo smoke

The Docker provider was available for the P0 demo closure. A single common image `scirel/p0-demo-unified:20261029` (`sha256:e2fd749b01d6b0ec8123e5db863467828f0f5c49ce257a5189d6c9e890fa5466`) ran the external q01-q10 glue serially with 2 CPUs, 4 GiB memory, pids 128, network none and `--rm` cleanup.

Nine cases produced parseable outputs and q10 produced a parseable bounded nonconvergence (`converged=false`, `maxiter_reached`); there were no timeouts, nonzero exits or hard blocks. Results are indexed at `E:/SciRel-lab/_shared/outbound/portfolio-20261027/results/p0-demo-runtime-20261029/demo-results-index.json`, with the complete run summary in `unified-smoke-summary.json` and per-case artifacts under `unified-smoke/q01` through `unified-smoke/q10`.

q07 remains an observed `SOURCE_DIFF` in the volume reference and is an AI-retryable focused follow-up. q10's nonconvergence is retained as an observable failure path. Scientific acceptance remains a separate expert decision; neither case blocks the runtime/demo closure. Demo-specific glue remains outside SciRel core.

## 2026-10-29 编程题式通用性测试原则

SciRel 后续能力提取、合并和出库统一采用编程题式测试。每个题面定义完整问题合同；SciRel 提供可复用核心能力；agent 负责用公开语言和依赖编写 glue、控制流程和组合。单一正常样例通过只证明该样例可运行。

每个能力至少覆盖正常范围、下界、上界，并在适用时覆盖退化、奇异、分支、失败和组合输入。测试攻击输入类型、形状、单位、边界、状态变化、异常、输出结构和数值不变量，先用测试暴露缺口，再决定哪些重复科学关系应提升为公共能力。题目专属流程保留为显式、可测试 glue。

外部 agent 评测使用干净题包：只提供用户需求/题面、公开输入输出合同和当前 SciRel 公共包，不提供参考答案、隐藏 oracle、既有题目 glue、历史结果或合并路线。主控可在评测结束后用独立 benchmark oracle 做回归比较，但真实用户任务没有预置 oracle。记录实际 API、glue、SciRel 包测试、agent 测试、失败路径和未覆盖关系。十题演示将按此原则从运行 smoke 升级为通用性测试矩阵。

## 2026-10-29 能力边界与角色分工

架构边界已补到 `ARCHITECTURE.md`：题目合同由题目/主控维护，SciRel 维护可复用科学关系和公共组合，外部 agent 维护用户任务图与显式 glue，主控保管参考 oracle，人工专家负责科学、适用性、权利和发布接受。

SciRel 不需要独自解决每道完整题目；它必须提供稳定、可组合、带类型/单位/形状/适用域/失败语义的科学核心。agent 可以用普通编程语言补足数据准备、控制流、格式转换和展示。重复出现在多个独立题目中的科学关系，经过边界与组合测试后才提升为公共能力；单个题目的 glue 不因运行成功自动进入 SciRel。

外部 agent 评测只读取干净用户需求/题面和公开 SciRel 包，参考答案、隐藏 oracle、历史结果和既有 glue 留在主控侧，事后可作为 benchmark 回归证据。真实用户依靠需求、公共能力、普通编程逻辑、约束、不变量、诊断和 agent 自己的测试完成任务。这样同时测试公共能力是否可用、agent 是否能完成任务、测试是否能逼出通用性。

## 2026-10-29 DSH 机制适配与独立 agent 评测

按 reference-adoption 结论，SciRel 只采用 DSH 的机制：技能按触发条件发现并按需加载；关键约束在执行前显式呈现；测试按风险层分组；真实入口、资源生命周期、失败恢复和外部世界读回由 skill 固化。没有复制 DSH 的目录、运行时、依赖或会话实现。依据包括 DSH 的本地 skill catalog/按需加载说明、分层测试政策、真实入口与资源清理规则以及 CI 可靠性 skill。

SciRel 现有拆解、D2 合并、出库和验证 skill 已增加 priority execution card；这些文件位于本地 ignored skill bundle，持久决策同步在 `RULES.md`、`ARCHITECTURE.md`、`HANDOFF.md` 和 Notion。卡片要求触发条件、事实来源、state/evidence card、边界矩阵、失败恢复、停止/重开条件和复现交付。

独立外部 agent 评测结果保存在 `E:/SciRel-lab/_shared/outbound/portfolio-20261027/challenge-agent-20261029/evaluation-summary-20261029.md`：只读干净题包和公开 SciRel 包，q01/q08/q09 完成，q02-q07/q10 明确报告 `HOLD_UNSUPPORTED_PUBLIC_API`，agent 测试 6 passed。该结果是能力入口缺口证据，不是题目无解或科学接受结论；下一步由合并线按重复科学关系和边界测试决定公共能力提取。

## 2026-10-29 内部与外部出库模式

`scirel-solving` 统一承载两种出库模式。内部模式由 SciRel owner 用于测试当前包或准备能力补充；发现公开能力缺口时停在能力边界，记录合同搜索、近似匹配失败、是否可提取为公共能力，并路由到合并/接收线。外部模式面向分发后的普通用户；SciRel 是可选增强，agent 可以用普通编程和公开数值依赖自行补全，并把补全作为可测试、可披露的任务 glue，继续交付用户结果。

两种模式共享需求卡、API 追踪、正常/下界/上界测试、失败与诊断记录。区别是缺口的所有权：内部缺口是 SciRel intake 信号，外部缺口是用户任务实现选择。外部任务不因 SciRel 缺口而阻塞，外部 glue 运行成功也不反向声称 SciRel 已拥有该公共能力。

## 2026-10-29 公开能力缺口 intake

初始评测摘要把 q02-q07/q10 标成 `HOLD_UNSUPPORTED_PUBLIC_API`，但回读 runner 后确认它实际只执行了 q01、q08、q09；其余七题没有真实答题或 API 搜索。因此原摘要保留为历史回执，不能作为公开能力缺失证据。纠正记录见 `E:/SciRel-lab/_shared/outbound/portfolio-20261027/challenge-agent-20261029/evaluation-correction-20261029.md`。

合并线当前应使用同目录的 `capability-gap-intake-20261029-corrected.md/json`。真实 discovery 已补齐 q02、q03、q05、q06、q07、q10：q02 的公开 normalized spectral primitives 已实际返回完整 18 模态并满足增长率迹恒等式，`nu` 转置/对角映射和 ky 校验保留为题目 glue；q03 的公开相对论谱 API 已通过 4 个波矢和边界/失败测试；q05 用显式有限拓扑 glue 完成；q06 复用了中性输运叶子；q07 复用了 `plasma_volume`；q10 复用了自由边界 Picard 组合但与固定 FRC/coil 协议不同。q04 已确认题面表格和闭合规则完整，暂保为 task glue 发现。只有真实发现和运行后仍缺少的可复用关系，才可进入 merge/intake；协议适配和题目编排保持 outbound-owned，不升级成公共 API。

十题合同审查已补齐 q09 的标准 `problem.md`、`output-spec.json`、`acceptance.md` 投影，并删除 q03 验收文件中与频谱输出无关的极化条款；q02、q04-q07、q10 的归一化合同、经验输入、有限拓扑范围、公开叶子边界和有界非收敛语义也已在题面前置说明。完整审计见 `E:/SciRel-lab/_shared/outbound/portfolio-20261027/challenge-agent-20261029/ten-case-capability-closure-audit-20261029.md`。

新的 clean external-agent challenge 已实际覆盖 q01–q10，未读参考答案、隐藏 oracle 或历史 glue。结果为 7/10 完成，q04、q06、q10 在真实非 glue 能力边界处报告 `CONTRACT_MISMATCH`：分别缺少 SAT1/2/3 多尺度饱和与原生剪切输运、有限速度原子 slab solver/orchestrator、固定 FRC Green/boundary 三层反馈协议。详细回执见 `E:/SciRel-lab/_shared/outbound/portfolio-20261027/challenge-agent-20261029/clean-agent-run-20261029/summary.json` 与 `report.md`；最终 intake 见同目录 `capability-gap-intake-20261029-final.md/json`。因此当前不能验收“十题全部闭环”，但已经证明 q01、q02、q03、q05、q07、q08、q09 可由公开能力和显式 glue 完成。

出库 skill 的 gap card 仍要求先披露公开能力边界，再按内部/外部分流。每个真实候选仍需 normal/lower/upper 及适用的退化、分支、失败、组合测试；外部出库可以用可见、可测试的普通 glue，内部出库才把重复公共关系路由到合并线。

## 2026-10-29 十题闭环的推广复盘

这次切片带来的结论不是“十道题已经证明 SciRel 覆盖完整”，而是把三条线的交接边界跑实了：题面先成为完整用户需求合同；拆解线交付 source-free 候选和可复核证据；合并线把重复科学关系提升为公共能力、把题目编排留在 glue；出库线只使用公开包和普通编程完成用户任务；主控再用独立 benchmark 结果做回归，专家单独审查科学语义。

十题的 clean challenge 实际完成 7/10：q01、q02、q03、q05、q07、q08、q09 可由公开能力和显式 glue 完成；q04、q06、q10 在真实运行中到达了明确的 `CONTRACT_MISMATCH`，分别对应 SAT1/2/3 多尺度饱和与原生剪切输运、有限速度原子 slab solver/orchestrator、固定 FRC Green/boundary 三层反馈协议。这三题不是“没有尝试”的能力缺口，下一步应进入合并 intake；q01 等已通过的题目保留为出库回归，不因后来题目失败而反复重测。统一 Docker smoke 的十题都有可解析输出，其中 q10 的有界非收敛是有效结果，不能改写成成功或失败之外的第三种状态。

这次闭环固化了六条推广经验：

1. **运行通过不等于能力入库**：完整题目可以由 agent glue 完成，但只有可复用科学关系才进入 SciRel；一次题目脚本不能反向定义公共 API。
2. **源码跑通不等于公开发现成功**：出库线必须真实查询合同、读取完整能力定义并记录 API 追踪；“应该有”或文件存在都不能算发现。
3. **测试先于通用化**：正常、下界、上界是最低矩阵，随后按风险加入退化、分支、失败和组合；测试暴露缺口后再决定提取、归并还是保留 glue。
4. **三类账必须分开**：source parity、outbound 可运行和 science acceptance 各自有证据和 owner；任何一类不能替代另外两类。
5. **生命周期要跟着交付走**：候选 packet 封定并读回后，拆解 worker 可以归档；合并后只保留 packet、必要证据和可复现入口，具体 successor 才恢复 session，避免长期空转和垃圾 worktree。
6. **规模化靠波次和指标**：先按展示价值与关系复用率选小波次，再扩展到完整来源分母；跟踪分母闭合率、发现成功率、公共能力提升率、干净 agent 完成率和未完成状态分布，而不是追逐题数或文件数。

下一轮工作的入口是：把 q04/q06/q10 的三个真实公共关系缺口拆成最小合并请求，保留 q01/q02/q03/q05/q07/q08/q09 的出库回归；在公共能力合并后重新运行同一份干净题包，比较 API 发现、agent 测试和端到端结果的变化。专家审查包只用于题面、单位、输入输出和科学合理性审阅，不作为公共能力准入证据。
