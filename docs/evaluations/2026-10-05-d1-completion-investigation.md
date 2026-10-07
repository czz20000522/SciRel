# D1 项目完成情况与收敛调查（2026-10-05）

本次调查由用户提出“是否有完成拆解的项目；为什么这么久；需要调查和优化”触发。范围是 Home 当前八个来源项目的容器 D1 批次；不将历史算子、旧开发 wheel 或部分 checkpoint 当作本批整项目完成。

## 后续用户澄清与职责修正

用户随后明确 D1 只忠实复现来源现有功能；科学是否正确和必要修正交后续阶段。
来源实现可以作为包内 C/C++/Fortran 等组件封装，运行脱离原 checkout 即可；D1 可以自行构造
来源可接受输入做行为差分。全链黑盒仍是来源码到 SciRel 包。完成要求调整本身不意味着已有工作浪费。

因此，下文保留的是当时观察和旧门槛解释，不再把原残差失败、物理校准或独立科学 holdout
自动解释为当前 D1 阻塞。具体来源问题交 D2，D1 仍须关闭缺失功能、状态/依赖、源对照和重组。
尚未逐项目重新裁定完成资格，不能因职责调整把旧失败、未验证范围或部分候选改写为整项目完成。
实际执行入口已有直接冲突：旧 D1 skill 要求独立科学挑战和数值正确性，通用实现 skill 又强制
科学残差/收敛验证；本次改为明确 `source_fidelity` 路由，并在 D2 接收来源问题。
权威定义见 [开发流程](../development-process.md) 和共享 stage boundary；无需重跑仍有效数字。

2026-10-05T07:01UTC 四个运行项目已安装新版五 skill 私有副本并更新正常 CLI 续接通知，
部署记录 `.runtime/scirel-d1-fidelity-20261005/deployment.json`。旧 bundle/通知/科学工件保留，
当前进程未中断，停机项目未重启，预算和模型路由未变；方法收取、实际采用及提速仍待后续工件验证。
34 项 extraction 工具测试通过，五入口结构和所改链接通过；这些工具检查不证明模型已采用新方法。

## 当前结论

截至 2026-10-05 13:15 北京时间，本批 **0 个整项目 D1 合格交付**。Pleiades、CQL3D、ORNL aorsa_tokamak、TokaGrad 四项运行；GENRAY、OMAS、Python AORSA3D、PetraM 四项因模型服务失败停止。未发现项目级 handoff，不进入 D2/D3。局部实现、真实源对照和 source-free 执行已大量存在，不能解读为毫无产出。

| 项目 | 实际前沿 / 卡点 | 下一个有效阶段条件 |
| --- | --- | --- |
| Pleiades | cp365；主要 native/callable 路径已有局部对照，WHAM/export、FieldLine、稳定性、全终端路径及独立 holdout/review 等仍开放；同一概括性剩余范围跨 checkpoint 保留 | 将既有 source map 的必需输出/分支逐项绑定到证据和剩余门槛，确认哪些本轮可关闭；不得把额外一般化研究自动变为 D1 前置 |
| CQL3D | 主 frontier-a46 与后续混合前沿；周期 spline/cubic、orbit extremum 有局部验证，真实 regrid、Newton 生命周期、LSODE、终端写出等仍未整合闭合 | 从已有源路径门槛推进完整实际状态/终端输出验证，而非仅累积辅助叶子数据集 |
| ORNL aorsa_tokamak | owner-20261005T050723Z；signed species/EQDSK/插值等证据持续增加，源关系、full main 和全域资格未整体成立 | 对当前真实源范围建立短剩余门槛投影，复用已证实的叶子并关闭主路径与材料分支 |
| TokaGrad | checkpoint705；Candidate47 current，48–52 pending；八个 Greenwald native governing residual 失败保留；固定线性方程的精度/可表示性证明不能替代耦合非线性终端通过 | 科学归因与有依据的受影响修正/明确失败语义处置，保持原容差与默认预算，随后终端复验及独立验证 |
| GENRAY / OMAS | key2 实际 CLI 503 未就绪；原 provider/stream 失败和 checkpoint 保留，持续停机 | 实质路由/上游改变后的有限完整工具就绪验证与合法原 session 接续；不能按小时无条件重试 |
| Python AORSA3D | 10月4日21:30北京时间本代三连续失败耗尽；frontier-a79 及部分 sigmad 工作保留；hot/QL/MPI/full main、物理依据及独立验证等尚缺 | 合法 provider 恢复条件 + 未完成科学队列，不能重置本代预算 |
| PetraM | 10月4日11:50北京时间本代三连续失败耗尽；cp050，候选 composite validation exit1；完整 core/RF/cases 尚缺 | 合法 provider 恢复条件 + composite/native/PDE/依赖验证；serial MFEM 不代表完整 FLAME HPC 路径 |

上述 science 状态来自作者工件；本次为协调调查，没有执行新的科学计算或独立科学认证。局部独立数值依据与最终独立 Agent review 是不同门槛。未发现 OOM，不足以推断宿主持续高水位或未来 HPC 容量。

## 为什么没有完成

**模型服务造成真实停工。** 四项停止是实际 provider/CLI 失败，有限预算已经耗尽。其他同 key 项目的 HTTP200 不能恢复这些 session 的 compaction/stream 条件。停工时间与仍运行项目的方法成本要分别看，不能统一归因于科学计算。

**协调把活动当作了方向健康的主要信号。** worker3 的普通 continuation prompt 只有“继续整个 D1”和保留证据；小时 monitor 主要采样容器、runner、工具活动和路由。没有稳定、可比较的“当前必需门槛已关闭/仍开放”投影。因此持续局部实验可以长期保持活动，而协调者未及时判断是否接近整项目交付。这是协调方法的缺口。

**接续材料持续膨胀，增加重复导航与压缩。** 实测 TokaGrad checkpoint705 为 1,408,892 字节，`next_internal_frontier` 包含 219 条历史事项；上一完整回合自报核验 7,289 个引用哈希。CQL3D 的一个 evidence binding 为 12,995,018 字节，ledger 为 409,494 字节；claude-007 日志出现 30 次 compact_boundary 和一个报告 3,926 num_turns 的 result event。日志内中间 result 不能当作 worker 最终退出；实际 runner 仍运行。这些数据证明接续成本问题，不证明所有哈希或实验都多余，也不能据此估计可节省百分比、真实 token 成本或完成日期。

**来源科学错误和验证范围仍需厘清。** TokaGrad 真实残差失败、Pleiades writer/模型适用性问题不能略过。与此同时，剩余记录含“一般 continuum/全域/物理校准”等宽泛表述；它们与确切来源当前合同的关系需要 owner 明确。未执行逐项来源审查前，不断言这些门槛均为不必要；也不能自动删掉。正确方向是保留完整源范围，区分必需拆解、明确的原始失败行为、外部证据缺口和来源之外的研究扩展。

独立 holdout/review 仍缺，但不是只差最后 review：几项主路径/分支科学门槛仍未关闭。历史 Pleiades 优化试验曾因遗漏终端物理输出被独立审查否决，说明降低分母或把局部 PASS 改叫完成不能解决问题。

## 已落实的纠偏与验证

1. 在四个运行容器的正常 resumed CLI 入口部署项目级收敛通知，保留原 session、正在执行的计算和三连续 provider 失败预算。通知要求来源绑定的缺口核对、有限工作组、有效证据复用、delta 范围核验，以及简短的项目接续投影。
2. 禁止把所有历史 next_action/manifest/ledger 重复送进当前上下文。原科学记录继续保留只读；owner 新增短入口引用它们。正常续接核验受影响闭包，完整交付/异常恢复时仍核验确切整包身份。
3. 小时 monitor 增加通知收取回执和 owner closure projection。后续判断依据实际关闭了哪些必需门槛、哪项未变化及原因；缺投影记为缺证据，不能臆造百分比或继续仅以活动判健康。
4. 已停止项目保持停止，等待既有合法恢复条件。没有启动额外模型探针、增加并发、换 key 或模拟科学批准。

入口变更在 Home Linux 容器内使用合成 route/fake exec 验证：原 prompt 保留并追加通知、routing env 保留、通知摘要回执、非 resume/version 不注入、通知缺失行为保留、disabled route 拒绝，共六项通过，真实模型请求为零。实际四容器入口文件摘要均核对一致。aorsa_tokamak 原入口为 vendor symlink，原链接元数据已保存，新增入口仍 exec 同一 vendor binary。

**部署不代表已被当前长回合读取，也不代表优化已经有效。** 通知在下一次正常原 session CLI 续接进入 prompt，监控按实际回执确认收取；此处不为插入通知中断正在运行的科学任务。效果必须由后续短投影与原证据中的门槛变化证明。若三个连续项目工作批次未关闭同一必需门槛，需要来源/方法/外部条件归因和相应纠偏，不能只增加测试数。

## 工件与接续

本次只读审计、frontier 投影、部署回执与脚本保存在本仓库私有运行目录 `.runtime/scirel-investigation-20261005/`，主要入口为 `audit.json`、`frontiers.json`、`current-monitor.json`、`deployment.json`。每项目通知和后续短投影在其独占输出的 `/work/infra/closure-review-20261005/`；这是协调材料，不混入 source-free callable 公共合同。

人类不需要逐个 leaf 审核。下一次有意义的汇报是：实际关闭的项目门槛、确切不能自修的阻塞，或真正合格整项目交付。现有资料不足以可靠给出完成日期或百分比。


## 用户要求的安全暂停与项目重点复核（2026-10-05 16:20–16:29 北京时间）

四个在运行的科学会话已在工具结果落盘、没有前台子进程的边界暂停。没有停止项目容器或计算子进程。
旧监督进程单独保留为停止状态，避免自动启动旧研究队列。行政暂停的中断不记 provider 失败；
同 credential generation 已有失败数保留。GENRAY、OMAS、Python AORSA3D、PetraM 的原阻塞与停机不变。

协调者读取了当前 checkpoint、来源映射、进度记录和保存脚本。以下为已观测工作，不能解释为完整 D1：

| 项目 | 当前证据与偏移 | 下一批的重点 |
| --- | --- | --- |
| Pleiades | cp389/A385 修 FITPACK，cp390/A386 验证修正版组合；开放项仍含 continuum、物理 inverse 校准等 | 沿现有全来源 map 分开 literal 与修正版，优先闭合 WHAM/设备/导出及 FieldLine/Boundary 原行为、状态、异常和独立运行 |
| CQL3D | tail/regrid 已有有界对照；LSODE 状态未闭合。保存脚本反复全验约75k历史绑定；mesh/Jacobian/maximum 已作科学修正 | 直接封装原 Fortran LSODE 与真实 workspace/history/restart/status，闭合原 orbit/writer；普通批次仅核对 delta 与依赖闭包 |
| ORNL aorsa_tokamak | 原 BESSJ/PV 疑点已有 source parity；当前 successor143 仍修 Smithe/nzfun2 | 随包封装原 Fortran；保留原 NaN/status/负J1，补实际已定义分支、消费顺序和 Main/CQL/species 组合及 MPI 范围处置 |
| TokaGrad | cp761 累积237前沿，snapshot53继续修 density/geometry/Newton/Picard | 绑定53db253原 bytes，分离科学修正版，闭合原 eager/JIT/AD、状态/历史/默认预算/失败及包内运行；按实际新来源核定七支持脚本缺口 |

这些方向保持完整来源范围。科学修正版及独立数学证据保留供 D2；分类变化本身不等于保真验证通过。
完整来源未对照、隐藏依赖未闭合、失败语义被抽取改写，仍是 D1 真缺口。外部缺料必须指出实际来源位置、
功能影响和取得条件，不能猜补。这里没有生成新全源 census、逐 leaf 微计划或完成百分比。

四个原 session 已启动有上限的方向审核：只允许读已有工件和写私有 owner-ack，禁止 Bash/科学改动/构建/测试。
收到报告后由协调者核对来源归属与首批输出，再按有限目标接续；不能仅凭通知复制或接口200声称实际采用。
控制与原始证据：`.runtime/scirel-safe-pause-20261005/`，其中 `audit-current.json`、`focus-docs.json`、
`status.json`、`supervisor-hold.json`、`audit-launch.json`、`directions.json` 与后续 owner 报告分别绑定真实状态。


截至本轮复核，Pleiades、CQL3D、TokaGrad 均完成八次工具调用的方向审核，明确接受 source_fidelity，
各只写一份私有 owner-ack。协调者已审核其材料归属和首批退出条件，并放行一个有48 turn上限的有限批次，
完成/控制上限即返回，不恢复旧无限研究队列。ORNL aorsa_tokamak 的原会话方向审核尚在返回过程中。

owner 复核补充了重要归属：CQL3D 当前 tail validation 已记76952绑定的 custody-only pass，但混合
Decimal2200 修正 maximum 的 regrid-tail 不能整体视为 literal 来源保真；TokaGrad 七脚本 omitted
属于历史 snapshot03，既有后续支持脚本执行/打包证据存在，当前是否缺料需本次来源 manifest 对账。
这些纠正已进入后续方向；它们不改变旧记录或创建新科学通过。


16:45 北京时间实际 metadata 核验：三个有限保真批次运行；ORNL aorsa_tokamak 方向审核曾遇实际524，
counter由1增至2，最后一次原generation许可内6turn审核正在进行，尚未放行科学修改。
它的原会话压缩记录为168476→26996 tokens，用时482246ms；这是运行开销，不是科学进度。
初次失败完整日志/回执保留，行政暂停0扣费与真实provider失败1次分别记账，无预算重置。
其余四个原provider停机项目未重启，gateway观测峰值均≤3，无整项目合格交付。


2026-10-05 17:04 北京时间的实际控制结果：四个原 owner 的新边界确认均已返回，协调者已分配有限项目方向。Pleiades 已封装 literal 来源并做输出/异常捕获，CQL3D 已在原 Fortran LSODE 状态/COMMON/重启差分上实施；这只是工作观察，未声明整项目门槛关闭。TokaGrad 首批已完整返回并停止，协调者只读核对了 actual-progress 中19项工件摘要全部匹配，并读取 comparison、build、source/package capture 与 sandbox 记录：两个 reduced 案例33条观察、1840数组叶一致、原无效 selector 异常一致，选定包组合在 Landlock 来源读取拒绝下运行。网络拒绝仍是 Python audit，完整默认neural和其他路径未通过，不是独立Agent审查或整体D1。下一重点已经保存在 Home next-direction.md：来源支持的neural加载/默认/缺失/fallback/推理/AD及依赖闭包，尚未启动。

ORNL最后一次短方向audit实际完整成功，但执行尝试22/23/24均为完整无工具回应，持续声明继承上一轮行政audit的上级只读限制；尝试显式覆盖及CLI --system-prompt配置后仍无实际实施。三次均不是新的科学/上游失败，实际524与预算历史保留，完整CLI回合按原运行器规则更新普通连续失败计数，协调者未人工清零。现已保存control-block并将runner真实状态设为paused_control_context_conflict，停止同样任务重发。原session、来源、旧成果、已分配原Fortran方向均保留；恢复前须核实实际CLI系统/恢复上下文中的已结束audit限制真实解除，不另建会话、不换key、不探针。不把拒绝回应的CLI success称为已执行或已完成。证据见.runtime/scirel-safe-pause-20261005/current-control.json、aorsa-control-system-replacement.json、focused-activity.json、tokagrad-evidence-review.json。


最终调度快照09:04UTC：Pleiades也已交回本批并停下，17选定病例及2次补捕获、305数组的原行为对照记录返回；协调者核对其literal ZIP及comparison/continuation/source-issues/evidence archive共6个摘要匹配，但未开展独立完整性审查。CQL3D达到有限控制上限并停下，未写actual-progress，counter2保持，partial/后台和科学结果须另核实，不把limit当上游失败或PASS。因此四科学CLI此刻均返回/暂停；四容器运行、旧PID1停止，不代表四项科学在执行。Home三项next-direction已明确保存但未启动：Pleiades原导出/analysis可达分支与安装闭包；CQL先保存核验现有LSODE部分工作/状态再原orbit链；Toka实际neural来源加载/缺失/默认/依赖闭包。原ORNL方向保留，受控制冲突阻塞。没有整项目合格交付，后续继续按实际来源门槛决定受控批次，不默认恢复旧研究队列。


2026-10-05 10:10–10:31UTC 的新实际调查补充：四容器运行但科学CLI此前均已返回，不能继续沿用“正在拆解”的旧观察。CQL的原有限批次确实留下25项LSODE routine来源对照（保存记录的最大误差比0），先核验无后台科学工作，再经原session有限metadata收尾写actual-progress、resume与identity-closeout。协调者核对identity/assessment摘要一致；没有新求解、重建或科学修正。原STOP exit0继续记native_termination，原a2完整当时身份回执、交错reference raw、D1MACH/诊断history和checkout-free独立重建缺口均保留，不能倒写旧receipt或称整体通过。

Pleiades/TokaGrad新方向第二批实际返回，却分别只做5次Read和0工具，继续拒绝继承的首批限制；这是控制接续缺陷，不是源码拆解或provider失败。实际安装的CLI帮助说明，system-prompt-snapshot默认on：记录首次系统提示，后续resume即使传入新system/append文本也继续使用旧记录，直至compaction。此前仅改system文本的尝试因此不构成新控制已生效的证明。保存快照payload未独立直接读取，此机制由已安装CLI主证据及改动后实际行为相符验证。

协调者将本批原session启动入口显式设为system-prompt-snapshot off，保留完整安全、私有项目、源码只读、路由/并发和有限批次约束，不改全局配置、不另建会话、不人工重置失败预算。Pleiades、TokaGrad和ORNL AORSA已实际读取当前release、新skill并写恢复进度；Pleiades/ORNL还实际Bash核查来源/既有工件，原拒绝状态已解除。CQL metadata复核后也放行原callback/caller到orbit/writer的32turn有限方向；其新回合10:31观察尚无工具，不提前宣称采用成功。其他三项分别限定42/47/30turn，结束或控制上限后返回复核，不恢复旧无限队列。四个旧PID1仍停止，四个provider停机项目未重启。

当前只证明调度控制转换与有限记录可接续，不证明新源码保真门槛关闭或拆解提速；后续仍须看实际差分、包依赖及完整来源处置。证据为.runtime/scirel-focused-followup-20261005/{verification,current-control,context-refresh-launch,cql-context-launch,context-refresh-verification,snapshot-help}.json；本轮无整项目合格D1交付，不发送D2/D3。

10:34UTC复核实际/proc命令行：四个新CLI均为各自原session、system-prompt-snapshot off，四旧PID1均为T。CQL新回合也已实际22次源码/既有记录工具调用；其本批短进度尚未写，不能将源码阅读当新门槛关闭。Pleiades/TokaGrad已新增私有prepare脚本并实际Bash准备对应来源包/依赖，ORNL已实际Bash核查原生依赖与已有fixture。没有新完整源码差分或整项目D1完成主张。实际进程回执见.runtime/scirel-focused-followup-20261005/actual-control-process.json。


2026-10-05 12:12UTC 最小全检查：四个有限科学CLI均已返回/达到控制上限，没有运行中的科学后台任务；旧PID1仍停止，provider四项停机及预算规则不变。协调者随后读取实际源码差分、包、状态/异常和失败记录，而非用容器running或API200判断进展。

这批出现可复用的有限保真证据：CQL九项原生callback/caller片段/writer片段及九项受限包对照，13来源和100新增派生/安装/证据绑定匹配；ORNL原语言组件20项对照及独立包重建，64custody绑定匹配；TokaGrad24加载/路径记录、1833私有模型浮点叶及12受限包调用。它们均未闭合整项目、完整默认轨迹或独立Agent审查。CQL错误restart_capacity标签不能证明分支，未定义scratch不是确定性科学状态；Toka的AD打印对照不证明完整未打印Jacobian，QLKNN输出后摘要读取失败仍保留。

Pleiades新实际流程缺陷：两个后台工具输出明确为[killed]，当前无对应进程，pip报告不证明安装成功，既定九项delta尚未执行。旧进度还有一个末尾逗号；原字节保留，另存可解析投影，没有倒补运行或成功。不能假设有限CLI返回后后台通知会恢复实施；具体终止机制未独立确定。下一批控制要求等待实际任务终态再返回，有限恢复部分安装、复用缓存/固定输入与判据，新增派生包/对照，不改旧脚本或记录。

据此沿四原session分别放行一个40turn有限方向：Pleiades九项原导出/analysis与安装闭包；CQL修抽取trace并推进真实初始化/orbit闭合到writer；ORNL将literal组件接入sigma/Main及cache/gradient/wave消费状态链；Toka推进原solver/default/history/cache/restart/mixed-cadence，相关序列化修复不替代功能闭合。release绑定前批实际身份，snapshot off、原预算/路由和旧PID1停止保持；不恢复无限队列。当前仍0整项目D1，不送D2/D3。详细证据：.runtime/scirel-bounded-review-20261005T1212/{coordinator-review,evidence,delta-bindings,close-review,pleiades-task-terminal,launch}.json。提交是调度事实，采用及实际门槛另据后续日志核实。

12:28:54UTC实际核验四新CLI均原session/snapshot off，四旧PID1仍T；新direction/release与prompt-delivery摘要匹配，并已真实读取当前控制。CQL/ORNL/Toka写了初始短进度，Pleiades当时只读控制/skill。尚无本新批差分门槛关闭证据，初始进度不代表完成。


2026-10-05 14:15UTC 全检查：四有限CLI已交回（CQL控制上限），无科学后台进程，旧PID1仍T，gateway ready、峰值≤3，停机四项/路由/真实失败预算保持。ORNL新增六generic sigma消费序列/24完整状态及包内重建对照，172delta绑定匹配，保留共享cache、gradient跳过/失败、wave先变顺序；Toka新增选定Newton/PC/cache/history/restart及30完整成对观察，3577数组9900坐标相符，29delta绑定匹配。Toka两个整体capture超时-9仍是部分，不倒推未保存source诊断/AD，不称整项目完成。

Pleiades一次被中断安装恢复仍在480秒上限被终止-9，文件检查143终止，九项未执行；CQL三个trace/定义消费状态差分关闭抽取标签缺陷，但后续full orbit新header编译140秒/25秒超时、尚无orbit对照，旧started进度不能代表其实际部分。来源错误和科学修正版未改，工作批次/安装/编译超时不是新的provider失败。

实际本地文件系统诊断：同一Pleiades容器、48个4KiB文件逐write/stat/read，Windows bind /work共3.504秒、Linux overlay共0.00185秒。小样本只证明明显小文件开销差异，不能将安装/编译所有耗时都归因于此。此前把大量venv/编译小文件写入跨系统挂载属于可纠正的运行方法；仅提高timeout或重复同安装无法验证优化。新有限方向将同字节/版本/输入/判据的密集安装/构建放项目独占Linux staging，重要包、锁定依赖/可取得条件、输入/原结果/构建和恢复证据以自包含归档保存回Home持久/work；/tmp不能成为交付隐藏依赖，旧部分环境和失败只读保留。

ORNL/Toka后续重点从重复局部对照转为完整来源功能到可安装候选的收敛：既有map绑定主要功能的callable、状态/默认/重要分支、依赖和真实未完成处置，补最能打通完整原API的缺口，保留所有源码范围。原默认代码/参数保真与某个昂贵全时长运行是否执行分开说明；不追加科学校准、所有组合穷尽或性能扫描的通用D1门槛，也不补造未跑全轨迹的数值PASS。当前仍0整项目D1，无独立完整性审查或D2/D3接收。证据.runtime/scirel-bounded-review-20261005T1414/{monitor,evidence,delta-inspect,cql-partial,io-diagnostic,coordinator-review,launch}.json。新release沿原session与generation，旧PID1/无限队列不恢复。

14:28:02UTC新实际核验四原session/snapshot off、旧PID1T、release/delivery一致，新方向已真实读取。Pleiades开始Linux staging安装/九项命令，CQL已保存准确部分checkpoint，ORNL读取原Main/compiler，Toka当时只Read。阶段/方法采用不等于安装或保真门槛完成，提速只由后续真实结果证明。

## 16:16 UTC：安装门槛实际关闭，收尾与编译仍需分别处理

本轮最小检查四有限 CLI 均已返回或到控制上限，旧 PID1 均保持 T，无科学后台；gateway ready，现有每 key 峰值不超过 3，停机四项目与 key2/key5 探针计数不变。证据入口 `.runtime/scirel-bounded-review-20261005T1616/coordinator-review.json`。

Pleiades 使用同 30 冻结 wheel 在 Linux staging 一次离线安装 exit0、2.2689 秒，九原—已安装包观察 135 数组/25380 元素、八 EQDSK 文件 bytes 精确对齐，原失败忠实保留。持久自包含归档 297 成员 hash 本轮协调重新核对无不符，11 进度绑定匹配。原 Windows bind 安装 480 秒被终止的失败仍只读保留；这证明本次安装方法有实际效果，不能当只有路径变化的严格性能实验或整项目 D1 通过。后续转向既有全功能映射和具体重要缺口，避免再装或重跑九案例。

CQL3D 的相同 source/header/flags 已位于 Linux，但唯一原侧 monolithic native build 90 秒仍实际 -9，安装侧与六 orbit 输入未执行。编译单元、CPU/RSS/IO 阶段原因未知；warning 不是原因证明。本次放行改变为按 unit 可观测单线程编译和有效对象摘要复用，单 unit180 秒、总工作600 秒上限，有实际卡 unit 即保存对象/诊断返回；不重发整链或仅提高总 timeout。

ORNL 已保存原 full make/link exit0、literal native wheel 安装及 bounded selector/Main input/CQL reader 对照与否定读取控制，但旧短进度仍 startup，未有完整持久交付。Main 抽取 input body 是有限来源投影，非 fullMain 独立运行；NetCDF fixture 原—包 exit3 无效 dimension 属保真失败，不能说完整 reader 成功。先收尾原语言候选、实际范围图与自包含归档，不重复 primitive 或 solver。

TokaGrad 八 build/install/child 均正常 exit0；五 installed useful tasks 的1107数组/2455坐标按原2e-10 exact。依赖 payload 导出 task bm0kfygji 原输出 [killed]、无进程，持久 payload-manifest 缺失，旧进度却 pending/live1。终止机制与原 exit 未独立确认；不算 provider 或 source 失败。新记录先准确 partial，后续改为 Linux 组装 tar/stream 后单文件持久 export，禁止把巨量文件 copytree 到 bind 的长期后台当完成。旧 bytes 不回写，有效 installed 数字复用。

四原 session 的下一批仅按上述真实缺口有界放行，f1 目录 `/work/infra/functional-closeout-followup-20261005-f1`，Pleiades40/CQL32/ORNL24/Toka24turn；snapshot off、key/generation/失败历史、旧 PID1 T 不变。当前只是 submitted，采用与新门槛须实际工具/终态核实。全来源范围保持，整项目合格 D1=0，不送 D2/D3。

16:26:40 UTC 实际最终控制核验四 f1 均原 SID/snapshot off/旧PID1T，delivery 与 direction 摘要匹配并实际工具采用：PL功能合同读取/Bash、CQL真实partial与旧对象检查、ORNL收尾checkpoint与实际安装记录读取、Toka读取原killed并保存准确partial。均未由这些工具活动推断新科学/编译/归档门槛闭合。


2026-10-07 实际复核：四个原 session 的 F1 已正常返回，旧 PID1 仍 T，无科学后台；10 月 5 日的 heartbeat 时间不能充当当前运行事实。来源保真进度已有实质收敛：CQL3D 同 flags/header/COMMON 的逐 translation-unit 编译产生 36 个有效对象和两个 native executable，配对 build/link 全部 exit0，18.2766 秒。六个来源正常调用与六个受限安装调用对照通过，其中四个真正返回 orbit/consumer，两个忠实保留原 STOP exit0，不是求解成功。旧 monolithic 超时的具体机制仍 unknown，不能反向归因。有效对象及原输入/raw 可复用，后续只补原 producer/full writer 等实际缺口。

Pleiades 的一组 kinetic/anisotropic/Hall 原—包对照保存 14 场景、786 数组、41344 元素及状态/异常原样一致；两步 convergedFalse 和 compatibilityValueError 保留，不宣称科学收敛。现有功能图用于具体剩余能力收敛，326 callable 行不是完成比例。ORNL 与 TokaGrad 已保存自包含持久归档并真实进行新位置 offline 安装/import；Toka 的旧 killed 导出仍是原始失败记录。协调者本轮重新核四份 archive 文件摘要、读取实际 build/normal/restricted/recovery 记录，未开展独立科学或独立 Agent 审查。整项目合格 D1 仍为 0。

下一批明确到项目功能方向：Pleiades 可变 device/coil/mesh，CQL 原输入生产到完整 writer，ORNL 原语言可复用 geometry/current/orbit，Toka waveform→optimizer；各仅一个有限批次，复用有效数字/安装，不重普查或修原科学错误。来源已复现的失败、供应源码之外广告或特定长轨迹未执行必须正确处置，不循环当成必须修成成功的 D1 门槛。归档成员数不证明功能完整，完整入口也不替代局部 callable。

当前 gateway 的实际硬上限是每 key 3，并不能从 metadata 宣称全局 3。最新指令要求总模型请求最多 3，因此本批选择一个 owner CLI 在运行的单次串行准入，内部所有请求仍由该 key 硬限 3；等 streamEOF 与实际任务终态后再准入下一已审方向。四方向一次预先审定，后续没有自动新方向或旧无限队列。准入进程创建不等于模型启动/收取，须按实际 dispatcher、argv、deliverySHA 与真实工具核验。证据入口 `.runtime/scirel-bounded-review-20261007T1555/coordinator-review.json`。


## 10月8日用户追问：日历推进不等于实际执行

当前记录显示：CQL3D、ORNL、TokaGrad 的 F1 runner 在北京时间10月6日00:33—00:37交回，直到10月8日00:16实际查询仍没有新 CLI 批次，间隔约47.7小时；Pleiades F1在10月6日00:50交回，G1在10月8日00:05启动，约47.3小时没有新登记 CLI 批次。这是有限批次等待协调复核/准入的实际长空档，不能描述成连续多天执行源码拆解。可取得的记录不足以判断 root heartbeat 提前接续未发生的底层调度原因，不能猜应用离线、服务故障或用户因素。协调与状态汇报必须对这段停工负责。证据 `.runtime/scirel-status-20261007T1616/elapsed-time-investigation.json`。

已经发生的失效还包括D1混入科学修正、旧系统提示继承行政限制、跨系统小文件安装开销、CLI返回后后台任务不接续，以及反复历史导航。当前为0并不能证明D1本身需要如此长时间。四项外部provider停止与四项协调等待应分别统计；原始成果继续只读保留。

余下的真实缺口是部分功能端口/原输入生产与完整输出/组合状态及可取得运行依赖，还需稳定候选完整性审查。已忠实复现的原失败、供应源码之外广告、每种配置组合穷尽及任意昂贵长轨迹不能作为必需D1成功门槛。字节相同且依赖不变的保留实现，应复用源绑定与已有代表性对照，不能按getter/branch无限追加微实验。今后有限批次返回后未及时进入协调复核/已审准入，需要明确记作可行动的协调停滞，不能因容器running或旧tool活动继续标健康。已落实的一次四方向G1 Home串行准入只解决当前预先审定工作组内接续，不能宣称永久解决 root review availability 或整项目完工问题。
