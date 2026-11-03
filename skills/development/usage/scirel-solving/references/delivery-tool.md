# 交付辅助工具（可选）

[scripts/delivery.py](../scripts/delivery.py) 对保存的 CSV 表做数值一致性检查：读入数据，计算有界的数值陈述，生成 `ANSWER.md`、`REPORT.md` 和可选的图，并能回放核对。它没有科学求解器，也不判断文字、模型、单位声明是否正确。

它生成的 `ANSWER.md` 和 `REPORT.md` 是检查输出，不是给用户看的报告。用户报告仍按[报告格式](report-format.md)写。把这些输出放在 `checked/` 目录作为验证记录。

## 规格文件

在输出 CSV 旁边写一个 UTF-8 的 JSON 规格。路径相对于规格文件（也可用绝对路径）。只接受下面列出的字段；不能填入预期结果、PASS 标记或自由文字结论。

```json
{
  "schema": "scirel.result-delivery",
  "tables": {
    "measurements": {
      "path": "measurements.csv",
      "units": {"time_s": "s", "temperature_K": "K"},
      "coordinates": ["time_s"],
      "expected_rows": 3
    }
  },
  "claims": [
    {"op": "range", "table": "measurements", "column": "temperature_K"},
    {"op": "threshold", "table": "measurements", "column": "temperature_K", "relation": ">", "value": 350}
  ],
  "plots": [{"table": "measurements", "x": "time_s", "y": "temperature_K"}]
}
```

这只是输入格式的示意，不是默认模型或判据。列、单位和判据要来自用户确认的需求和所选的科学合同。CSV 列名必须是标识符；单位是简短的 ASCII 表达式（`1` 表示无量纲），不做隐式换算。未声明的多余列可以保留，但被陈述、坐标或图用到的列都要声明单位。所有值必须有限，行格式完整。

## 覆盖范围与前提

- `expected_rows` 按用户要求的输出覆盖范围设定，不按求解器碰巧返回的行数设定。
- 需要特定的坐标组时，给表加 `expected_groups`，例如 `{"columns":["coordinate_a","coordinate_b"],"values":[[0,0],[0,1]],"rows_each":3}`。实际集合和重数必须完全一致，这样能发现把终点诊断当成整段扫描的情况。不要给只有一行的诊断表加整段扫描的范围。
- 可选的顶层 `premises` 是 `{"path":"request.txt","quote":"该文件中的原文"}` 列表。把用户请求和澄清如实保存，再原样引用，不加推断出的条件。工具只检查原文包含关系并绑定字节；对话本身的真实性由宿主负责。这些是引用的输入，不是验证过的物理。

## 数值陈述

每个操作作用于整张声明的表，没有隐藏的行过滤：

- `range`：`op, table, column`；返回最小值、最大值、最大绝对值和实际行范围。
- `threshold`：再加 `relation`（`>`、`>=`、`<`、`<=`）和有限的 `value`；统计满足条件的行数。计数为零只说明保存的值里没有满足条件的，科学判据要来自澄清过的需求。
- `relative_deviation`：再加 `at`，一个坐标到值的映射，恰好确定一行参考值；可选非负 `coordinate_atol` 允许坐标舍入（默认 0）。报告参考值和最大相对偏差；参考值为零时拒绝。它不判断工程适用性或标度律。
- `compare`：再加 `reference`（另一张表）、`keys`（坐标列）、非负的 `atol`、`rtol`。要求键集合唯一且完全相同、单位相同，然后计算 `abs(actual-reference) <= atol + rtol*abs(reference)`。比较失败就是失败。两表字节相同时会注明；比较成功不等于独立的物理验证。简并谱需要多重集匹配时另做科学检查，不要为凑唯一键而丢掉模式。

诊断量可以存成单独的表，带它实际的坐标，陈述只覆盖那张表的范围。工具不解释残差，不把后向误差换算成前向精度，也不根据列名推断独立性。

## 构建、回放与交付

```sh
python3 <本 skill 目录>/scripts/delivery.py build result-spec.json --out checked
python3 <本 skill 目录>/scripts/delivery.py verify result-spec.json --out checked --answer checked/ANSWER.md
```

输出 `ANSWER.md`、`REPORT.md`、`checks.json` 和可选的 `figure-1.png` 等。图直接读保存的坐标，不重新缩放，标注使用声明的列和单位。只有画图需要 matplotlib；图上用 ASCII 标签，避免缺少中文字体的警告。

`verify` 会重新读入当前的 CSV 和前提，重算陈述和图，并与已交付的文件比对。CSV、前提、规格、报告、答案或图有任何改动，回放都会失败。这些本地哈希只是一致性绑定，不是签名或权威证明。

退出码 `0`：有界陈述一致。`3`：报告有效但数值比较失败，要如实说明，不能声称完成。`2`：输入无效、不完整或输出被改动。修正真正的原因后重建；不要编辑生成的 PASS 标记、为通过而改容差，或在失败后沿用旧报告。

引用这些陈述里的数字时保持原样；额外的科学解释需要另外的依据和明确的限制。如果宿主平台能提供答案草稿文件，可以把它传给 `--answer` 做一致性检查；这只检查这一份草稿，不检查之后发出的其他消息。
