# 原子题的两个独立静态条件候选

版本`2026-10-27-atomic-condition-addendum-1`；仍在原题根/id `kn-atomic-slab-analytic-cx`。
A、B都是**本轮静态条件候选，主审pending**，各自从原基准独立实例化。
[索引](index.json)和下表明确区分三种条件：

| 条件 | 唯一实例变化 | 公开入口 |
|---|---|---|
| 原基准 | 原50点、3eV单能入口、解析电子率、SIMPLE_CX=true、elastic-off | [inputs](../inputs.json)、[原题面](../problem.md) |
| A | 只选已有任意分布入口；其原分支自动由输入最小正物理vx生成E0 | [condition](A/condition.json)、[全部有限样本](A/input.json)、[完整入口算子](A/arbitrary-inlet.md) |
| B | 只令SIMPLE_CX=false，入口继续原3eV | [condition](B/condition.json)、[完整直接CX算子](B/direct-cx.md) |

A不采用B的直接CX，B不采用A的任意分布；没有组合A+B的第三条件。
它们不增加题根或物理族，不产生参考或科学通过。原7份公开文件保持独立完整、字节不改，
本附录版本只增加明确输入/分支实例；旧文件中的“当前固定题”仍指原3eV/simpleCX基准。

## 完整输入绑定及基准实例措辞的范围

路径相对声明它的文件解析。A读取本题[inputs.json](../inputs.json)中condition.json枚举的九节：
profiles、configuration、solver、molecular_inputs、pipe_diameter_m、constants、precision、units、axis_order。
其中原50点x/Ti/Te/ne/vxi及mu、配置、初始化、常数和单位原值照用；入口改用A/input.json的完整边界数据。
A/input.json与A/arbitrary-inlet.md是该入口的唯一数值/数学定义，不在原incident上继续叠加3eV。

B读取整个同一基准的科学输入，唯一覆盖项是`configuration.collisions.SIMPLE_CX:false`。
原incident.mode、1e15m^-3入射密度、3eV和份额1都保留；B/direct-cx.md给出此分支的全部实际截面、
核积分、损失、每代出生、输出中CX项及失败顺序。该文稿明确实际默认Janev而非另一拟合选项，
没有另添加一个可调截面参数。

两条件都使用本题原三个完整算子：
[边界、代次、输出](../operators/boundary-generations.md)、
[电子率与碰撞](../operators/collisions.md)、
[网格、有限格、Maxwell与投影](../operators/mesh-projection.md)。
它们的共同定义不复制成另一套。具体实例范围按下表唯一限定：

| 原文件语境 | A | B |
|---|---|---|
| problem.md“单能原子氘入射”“任意分布未代表”；boundary-generations.md §1单能组分构造及任意支不参与 | 激活同根A完整log-cubic任意入口；替换单能上层构造 | 原单能入口不改 |
| mesh-projection.md §1的E0=[3]、§2的“one positive added energy” | E0按A给出的最小正物理vx能量公式，仍一个正附加能量；两次建网均用它 | 原E0=[3]及两次建网配方不改 |
| problem.md、boundary-generations.md及collisions.md“当前启用简化/Maxwellian-weighted CX”；其它直接CX不参与 | 继续原SIMPLE_CX=true | 激活B完整直接CX；所有活跃alpha_cx和beta_cx以及诊断中的这些符号取B定义 |
| 网格构造使用解析Maxwell加权C(Ti,Emin) | 保持这个原启发式 | 同样保持这个原启发式；不能随direct输运分支切换 |
| 各文件“固定有限候选不代表全部条件” | 仅补这一4×4输入样本 | 仅补这一直接CX/3eV实例；elastic仍全关 |

A/B的profiles不从另一题取得；A/B所需新定义与全部系数也都在本题根。
求解者不需要私有来源或耦合题；同根三个原模型加选中附录即形成完整规范。
没有将其它未选ADAS/JH/弹性/管壁分支变成隐式输入。

## 保持的参数、状态、停止和输出

两条件均mu=2、原50点背景和零vxi、mesh_size6/grid_fctr.3、解析`ion_rate=janev`、
H_P_CX=true、H_H_EL/H_P_EL/H2_H_EL=false、recombination/ion_density_correction=true、
PipeDia=0、compute_errors/ci_test/alpha_cx_test=false、debug/debrief=0。
各自从原零原子seed/分子分布/显式原子源/分子离子密度、1eV分子离子温度开始，
只按原顺序覆盖该条件左正向边界；右负向外部入射为0。
没有新背景漂移、弹性外轮、外部源、侧壁或新的自洽反馈。

原空间/速度网格必须未来按公开解析生成配方构造，不给固定求解格或Tnorm值。
A的4×4物理采样轴是入口普通输入，不是求解速度网格。
原mesh启发式、有限体积、Maxwell补偿、传播格式、正速度空间步长检查都保持。
只在A按原advanced分支改变E0；B的直接CX损失可能影响原spacing检查是否通过，
不能为保证成功反复改网格。

原truncate=.001，严格代次截断和50代失败检查顺序、停止后最后代beta累计与所有输出矩保持。
没有新增外层cap、物理停止量、碰撞/数值容差或强行延长代数。
原异常、非有限和不终止/失败位置照规范记录；静态HOLD报告不构成对来源的修复。

[输出规范](../output-spec.json)和[验收](../acceptance.md)逐条件使用原值。
交付标记condition_id，各自产生自己的生成坐标、分布/矩和边界；不得把两个条件串联的结果混在一起。
A额外审阅材料明确区分原样本、上层密度归一化shape、推导G和下层实际施加边界；
N0是入射半分布密度，G是其原离散矩推导的下层权威通量，不是独立新输入。
B输出中的CX项使用直接核，但输出量、单位、轴序、定义与原规范一致。
当前并未求出任何这些量或边界矩。

## 静态资格及剩余项

两条件主审pending，source/solver/reference/capture/replay及NumPy数值求值均NOT_RUN。
无新速率、核、网格、插值、flux或解；没有隐藏答案选参。来源对照与公开盲读只检验指定模型/输入闭包，
不证明空间步长接受、50代收敛、精度、算法/物理正确性或全族覆盖。
其它入口轴/分布、同位素、漂移、elastic/非零管壁及其它科学分支仍不由A/B代表。

本题解析电子率已有完整公开定义，无受限表数值作为隐式输入。
原生来源程序的ADAS导入期依赖、可能的JH构造加载和未来runtime封装，
与默认外部ADAS/PEC表公开再分发许可分别记录；它们不改变本选定解析模型的普通输入。
个人本地已有SCD/ACD的事实不等于公开授权。本轮无下载/安装/新运行环境/容器/WSL，
任何实际科学求值仍需另exactrequest/freshgrant。
