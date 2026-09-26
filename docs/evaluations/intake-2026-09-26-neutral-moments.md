# KN1DPy 中性矩诊断族开发整合记录

状态:**隔离开发版本,非可信版、非公开发行**。本记录对照保存的 KN1DPy 提取包
(`D1待重审历史产物/KN1DPy-631d0bf1`,严格 D1 资格已撤回);合格 L1 交付根
(`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`)复核为空,
未消费任何合格 L1 输入。原始比较与专家决策请求见
[候选文档](../../review_candidates/2026-09-26-neutral-moments/review.md)。

## 关系族选择

本批次整合保存源中性矩归约/输运频率层的十一个叶(r59 前各批次缓付清单中
"中性矩归约/频率组装"一组)。对照 r59 基线(`39416f5`,99 资产 dev31)与
未发布候选池:基线与池中均无同类资产,十一叶均为**新增能力**。全部逐位复现
保存 formal 实现;四项声明的 fail-closed 收窄(见下)由三轮只读预审反例驱动,
保存臂行为留证。

四项收窄:NaN 速度轴、通道求和溢出、NaN 归一化温度/质量/体积、以及全部
11 资产的输出有限性门控。逐模块极端输入审计(保存臂 vs 实现)确认每份
exact document 的 runtime_failure 声明真实成立;差异记录于
`identity.assumptions` 并有回归钉死。未弱化任何既有数值断言。

保留的保存行为(开放专家问题):sigma_zz = sigma_yy 柱对称认定;
source_default 零密度切片语义;零管径壁面损失为零。

## 科学证据

- 双臂复放:11 个保存实现文件逐一 SHA-256 绑定,声明域内输出逐位一致
  (`assert_array_equal`),拒绝行为一致(声明的收窄处除外)。
- 独立 oracle:冻结常数重算、圆柱体积积分重算、平移 Maxwellian 流速/温度
  恢复见证、独立梯形积分、零管径壁面损失、负值/取消见证。
- 逐文件测试计数(`pytest --collect-only`):11+6+14+8+12 = 51。

## 开发验证(r60)

- 110/110 文档源码态与安装态校验通过(含示例执行)。
- 干净 venv `build/venv-r60-clean`(本地 wheelhouse,`--no-index
  --no-deps --force-reinstall`,隔离探针 under-prefix)。
- catalog `complete: 110/110`,root digest
  `sha256:1c982a546a392b2e60a4c9e026344f82502918c25609e96c905836ee9a53c8dd`。
- 内部 wheel SHA-256
  `e89eccc362ad030473721395e66497a545bbe5c0499f3473038153669967680e`。
- 全部命令 pwsh 7.6.6(早期探索命令为 Git Bash,如实记录于评审说明)。

## 边界与待决

- 不宣称:合格 L1 消费、对外部物理参考的正确性、专家认可、可信晋级、公开发行。
- 继续缓付:壁面源序列图、自适应网格、跨网格插值、BoltzmannRHS、SIG 矩阵、
  分子 sigv 表组装、平移 Maxwellian 矩补偿。
- 许可证状态均为 `pending-human-decision`。
