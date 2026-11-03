# 测试结果：
# 工作目录：<task-graph package directory>
# 命令：<relative command from the task-graph directory>
# 环境变量：<none or declared variables>
# 结果：<N passed / failed summary>
# 对照依据：<direct source parity / fixture / formula / invariant / boundary>
# 源码对照状态：<direct_source_runnable / source_unavailable: reason>
# 证据来源：<source-relative path:line-line::symbol or oracle description>
# 数值差异：<per-output metric and value>
# 运行环境：<portable runtime identifier and dependency versions>

from pathlib import Path

from graph import run_graph


# 验证：用端到端 oracle 替换此模板失败项，并证明声明的节点、边和状态反馈被实际执行。
def test_task_graph():
    assert Path(__file__).with_name("task_graph.yaml").read_text(encoding="utf-8")
    run_graph()
