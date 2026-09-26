# FIDASIM -08 method-boundary review and Spark runner handoff (2026-09-27)

状态:SciRel `入库链路` 对 FIDASIM `-08` 方法边界审查的 SciRel 侧结论与外部 runner 交接需求。本文件只陈述已核对的证据与归属,不批准 `-08` 派发、不放宽任何证据门禁、不宣称严格冻结或合格 L1。`-08` 保持 `DO_NOT_DISPATCH`;旧 veto(接收回执 SHA-256 `410d7cad55afe760f507576fa28e29e5dab80f8a4491857ad82f4da801cb4762`)与勘误(`sealedholdout08_veto_erratum.json`,SHA-256 `ccb09f1f50224fba7ab2846ba30b8585d2c9c397351938d76fee932fc2b8743a`)原样保留。

## 1. 权威方法文本的准确读法(对照部署副本逐字节核验)

权威源:`skills/extraction/scientific-computation-asset-extraction/references/coordinator_led_extraction.md`(SciRel 主仓与 intake 工作树逐字节一致;Spark 部署副本 `CodeFusion/application/codefusion-application-product/skills/scientific-computation-asset-extraction/references/coordinator_led_extraction.md` 与权威源 **IDENTICAL**,部署通知 `scirel-d1-skill-bundle-deployed-20260925.txt` 记录 bundle 摘要 `sha256:bb55b252…`)。

- 第 96 行(Assert attempt write ownership 节):*"After an attempt emits a receipt or evidence that must remain auditable, freeze that attempt's writable roots."* —— 即**有回执的 attempt 其可写根必须冻结**。这是硬要求,不是建议。
- 第 64-65 行(Work packet 节):packet 携带 *"target relation, capability, path, edge, or candidate identities"* 与 *"frozen source/evidence and current candidate/dependency digests"* —— 即**允许**向 worker 提供目标 ID/digest。第 76-77 行的 allowlist 是共享读合同。
- 第 78-82 行:*"When the claim requires an output-blind or otherwise independent context, the packet must prohibit candidate reads."* —— 禁止 candidate 读只适用于**声明 output-blind/独立上下文**的 packet,不是普遍 target-blind/no-digest 要求。历史勘误(`sealedholdout08_veto_erratum.json`)正是把 V3/V4 从"普遍 target-blind/no-digest"收窄为"exact assessment 的独立性风险";本审查沿用该收窄,不再外扩。
- 第 20-23 行:launcher 合同四要件 —— 原子容量准入、**把每个 worker 的写限制在 packet lane 内**、共享集成 coordinator-only、持久 exit/handoff 回执;*"If those controls are absent or reject the launch, return the packet to the same queue and use the serial fallback."*

结论:权威方法**已经**写了 post-receipt attempt 写根冻结(96 行)与 launcher 写边界(lane 内、20-23 行),对 target ID/digest 明确允许(64-65 行),对 output-blind 上下文才禁止 candidate 读(78-82 行)。**方法文本本身没有缺口**;缺口在执行层 launcher 未实现 96 行的冻结语义。

## 2. Spark runner 的真实缺陷(只读核验,未改对方代码)

部署 runner:`CodeFusion/build/coordination/three-day-20260925/tooling-cap-20260925/run-worker.sh`(ROOT=/home/opc/codefusion-decomposition,Spark Stage1 部署;`.orig` 变体与现行为同长度同构)。逐行核验:

- `run-worker.sh:136`:`mkdir -p "$LANE_DIR/attempts"` —— lane 根下创建整个 `attempts/` 目录。
- `run-worker.sh:300`:`LANDLOCK_ARGS+=(--rw "$LANE_DIR/attempts")` —— Landlock 策略把**整个 lane 级 `attempts/` 目录**以读写授予 worker,覆盖其整个会话生命周期。因此 worker 在本次会话内**可以在发出回执之后继续修改本 lane 任何旧 attempt 的 `attempts/ATTEMPT_ID/{scratch,evidence}` 内容**(包括早前 attempt 的回执文件),不触发任何 Landlock 拒绝。
- `run-worker.sh:96-99` 的单 attempt 守卫只检查 lane 根的 `worker-events.jsonl`/`worker.exit.code` 是否已存在(一个 lane 一个 worker 会话),**不提供 per-attempt 的 post-receipt 冻结**。
- `run-worker.sh:265`(worker prompt)把 *"a native attempts/ATTEMPT_ID/{scratch,evidence} root"* 列为允许的 changed_paths 声明 —— 与 300 行的 rw 授予一致,但同样没有 post-receipt 只读转换。
- 对照 `coordinator_led_extraction.md:96`:post-receipt 冻结要求"有回执后 attempt 可写根冻结";对照 :102-106:并发写污染的 attempt 必须整体废弃 —— 但如果旧 attempt 在回执后仍可被(本会话或后续会话的)worker 写入,污染检测只能在事后人工读回发现,运行时没有阻止。这正是 `-08` veto V1/V2 的已证阻塞事实:receipt 后仍可改旧 attempt,输出盲独立上下文的独立性无法由该 runner 证明。

结论:`-08` 的 `DO_NOT_DISPATCH` 维持正确;缺陷归属是 **Spark/CodeFusion 部署 runner**,不是 SciRel 方法文本,也不是 worker prompt 措辞(prompt 已声明 fresh-attempt 规则,但 Landlock 权限与声明不一致 —— 声明防君子,权限才是合同)。

## 3. SciRel 侧归属与是否需要窄改动

SciRel 侧资产与消费关系(已核):

- `scripts/build_extraction_skill_bundle.py` / `install_extraction_skill_bundle.py` 存在于 SciRel **主仓**(`D:/…/workspace/SciRel/scripts/`),打包五个 skill 为 `scirel.extraction-skill-bundle.v1`;intake 工作树不含这两个脚本(intake 只消费已部署的 bundle)。installer 有防篡改/防外来 skill 目录测试(`skills/extraction/tests/test_extraction_skill_bundle.py`,含 tampered payload、foreign skill directory、active-bundle path 等反例)。
- 方法文本(SKILL.md 242 行 intake 版 / 344 行主仓版;references)已覆盖:attempt 写所有权(96-106 行)、launcher 四要件(20-23 行)、output-blind 禁 candidate 读(78-82 行)、"do not infer isolation from lane-only writes"(82 行)。
- **判定:无需为 -08 新增 SciRel 方法条款**。权威文本已包含可执行的方法要求;缺的是 launcher 对 96 行的实现。给方法文本再加一条重复声明属于文字假修复;已按用户指示不做。唯一需要的 SciRel 侧动作就是本文件:把 -08 的方法边界结论、runner 缺陷定位和交接需求落在权威侧可追溯的记录里(即本文件),供 bundle 下次重打包时随行(本文件位于 intake 工作树 `docs/coordination/`,不在五 skill 打包范围,属 SciRel 项目文档)。

## 4. 给 Spark/CodeFusion 部署负责人的精确需求与验收证据

需求(对 `run-worker.sh` 或其后续部署版本;由 Spark 原负责人实现,SciRel 不代改):

0. **会话内 receipt 时序合同(堵住 -08 veto 的核心窗口;单一方案,无可选分支)。** 冻结不能只在 worker 退出后做:同一 worker 会话完全可能先宣告 receipt 再继续运行,该窗口内本次与旧 attempt 仍可被写——这正是 -08 veto V1/V2 的阻塞事实。合同是**一 worker 会话仅拥有一个新 attempt 根的写权**,且时序固定为:
   1. worker 只产出**待封存内容**(draft evidence);worker 写的任何 receipt 命名文件在 seal 前一律只是草稿,系统不承认其为可审计回执;
   2. runner 等待 **worker 进程确实退出**并回收其写权——`output-last-message` 落盘**不等于**进程退出,不得作为收权时点;
   3. 由 worker 无法撤销的独立 owner/封存副本机制对整个 attempt 根 seal(内容 digest 快照 + worker 不可撤销的只读强制,见需求 2);
   4. seal 完成后,runner 发布**绑定 seal digest 的 auditable receipt**。
   不变式:**不存在"可审计 receipt 已被系统承认而其写入者(或同 attempt 的任何写入者)仍持写权"的状态**。不引入"运行中动态收权/双层 landlock wrapper"等未经验证的实现猜测(普通 Landlock 规则不能由 runner 事后收紧另一存活进程的已授规则);除非负责人给出部署实证,不得列为备选。
1. **Per-attempt 写根,而非 lane 级 attempts 写根。** `LANDLOCK_ARGS` 不得再包含 `--rw "$LANE_DIR/attempts"`(现 :300)。改为:启动前由 runner 生成本次 attempt 的独立根 `$LANE_DIR/attempts/$ATTEMPT_ID/`(含 `{scratch,evidence}`),只把 `--rw "$LANE_DIR/attempts/$ATTEMPT_ID"` 授予 worker;若 worker 需读旧 attempt 作对照,以 `--ro` 只读授予显式列出的旧 attempt 路径(默认不授)。
2. **Seal 机制必须独立于 worker 的撤销能力。** runner 在 worker 进程确实退出并回收写权后立即 seal 该 attempt 根。注意:`chmod -R a-w` 单独**不构成持久强制隔离**——同 uid 的文件 owner 可以随时 `chmod +w` 撤销,worker 若与 runner 同 uid(当前部署即如此)则该机制形同虚设。可接受机制(以部署环境可用为准,可组合):独立非特权 owner 持有 attempt 根(worker uid 无写权,root 或专用 seal-owner 所有)、只读 bind mount/`chattr +i`(具备 CAP_FILE_ATTR 的 seal-owner 施加,worker 无法解除)、或 seal 时把 attempt 内容复制到 worker 永不可写的封存路径并只对外发布封存副本 digest。seal 动作与结果(路径、机制、时间、前后 digest、施加者 uid)写入 auditable receipt 或 runner 日志;seal 完成前 runner 不得向 coordinator 报告该 attempt 的 handoff 为可审计。
3. **跨会话持久性。** 冻结必须在文件系统层持久(而非仅 Landlock 进程策略),使下一次 `run-worker.sh` 会话(哪怕同 lane 新 attempt、同 uid)也无法以读写方式写旧 attempt 根;`--ro` 重挂载读旧 attempt 时应能在 runner 日志中区分"只读对照读"与"写"。
4. **守卫扩展。** 现 :96-99 的单会话守卫保持;新增:若 `$LANE_DIR/attempts/$ATTEMPT_ID` 已存在且未冻结(例如上次运行崩溃在冻结前),拒绝复用该 ATTEMPT_ID,要求新 attempt ID(与 prompt 中 exit 73/74 语义一致)。
5. **不改语义。** 本需求只收缩写权限与增加冻结动作,不改变 read allowlist(:243-247)、handoff 合同(:255-267)或 slot-manager 合同;`.orig` 变体同步与否由负责人决定,但部署副本必须以 digest 记录进 run 协调记录。

验收证据(全部由 Spark 侧产生,SciRel 只消费结论;每项需可复跑并给出 receipt/digest):

- **A(worker 存活期间不存在被系统承认的可审计 receipt;同会话写旧 attempt 必拒)**:worker 进程存活的整个窗口内,系统层面不存在承认该会话任何输出为可审计 receipt 的记录(运行中宣告的 receipt 只是草稿);worker 自写 receipt 同名文件不改变这一点,内容仍按待封存草稿处理;同会话尝试写同 lane 旧 attempt 的任何文件必须失败。所有拒绝与草稿定性均需留痕(receipt/digest)。
- **B(跨会话、同 uid 反例)**:第二次 worker 会话(与第一次同 uid)尝试写第一个已 seal attempt 的任何文件必须失败——证明强制不依赖 `chmod a-w` 可被同 uid owner 撤销的性质,而依赖独立 owner/只读挂载/封存副本等机制。
- **C(对照读可用)**:后续会话按 packet 显式 allowlist 以只读方式读已 seal attempt 的 receipt 文件成功(证明 seal 不是简单屏蔽),而写尝试被拒。
- **D(崩溃恢复,时序点 = seal 前)**:模拟 worker 已产出待封存内容后、runner seal 前被 kill;该 attempt 不可被复用(下次 launcher 启动同 ATTEMPT_ID 以"未封存"拒绝,exit 73/74 语义),且**不存在该 attempt 的任何可审计 receipt**;新 attempt ID 正常。
- **E(canary 回归,不干扰活跃 lane)**:在隔离 canary lane(真实 packet 形状、真实 runner 参数,不挂在任何现役科学 run 下)完成回归:read allowlist 行为不变、handoff 合同不变、slot-manager 计数不变。现役 FIDASIM/fluidBW/PDRF 活跃 lane **不做空载试运行**;其新 runner 行为验证由原负责人在各 run 实际进入下一自然阶段时按本合同核对。
- **F(digest 记录)**:新 `run-worker.sh` 的 SHA-256 与部署位置记入 run 协调记录(与 `scirel-d1-skill-bundle-deployed-20260925.txt` 同等级别的通知),SciRel 侧凭该记录更新 -08 状态评估。

以上 A-F 全部通过前,`-08` 维持 `DO_NOT_DISPATCH`;`TARGET-HOLDOUT-INDEPENDENCE` 维持 open。通过后由 FIDASIM 原 coordinator 发起新的 sealed-holdout 独立验证尝试(新 attempt、新 receipt), SciRel 侧届时按 method :78-82 的独立性语义评估其证据,不以本次交接预支任何 pass。

## 5. 处置摘要

- `-08`:**DO_NOT_DISPATCH 维持**;阻塞事实为 runner 层 post-receipt attempt 写根未冻结(run-worker.sh:300),不是方法文本缺口。
- 旧 veto + erratum:原样保留,本文件不改写其任何字节或结论。
- SciRel 方法文本:**无窄改动**(要求已存在且已部署,部署副本与权威源一致);SciRel 侧新增本审查记录一份。
- 执行层修复:移交 Spark 原负责人,需求与验收见第 4 节;SciRel 不代改 CodeFusion/Spark 代码。
- 证据门禁:无放宽;严格冻结与合格 L1 主张继续以正式 bundle 部署与有效反例验证为前提。
