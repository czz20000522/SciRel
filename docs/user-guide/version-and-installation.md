# 本版范围与安装

## 版本绑定

| 项目 | 本指南对应内容 |
| --- | --- |
| Python 包 | `scirel` |
| 版本 | `0.2.0.dev2+review20261008` |
| 科学源码提交 | `fcf97c237adf799124e5a56cc4062c54302b2b33` |
| wheel SHA-256 | `998b88f2c54cd75f5fcc1310789e280fa96ccc69181b708a4ce31141d06a9874` |
| 历史参考计算环境 | Linux x86_64、CPython 3.12.14、CPU；仅描述该证据的环境，不是接收平台的宿主要求 |
| 内容范围 | TokaGrad 来源的托卡马克约化模型兼容接口；32 个公共入口、7 份详细合同 |

这是开发包的使用指南。已记录的是有限来源保真、安装和数值对照；本版未完成整个来源项目的 D1，
也不能据此声称所有输运、优化或磁平衡模型已获得独立科学认可。Q1/Q2/Q3 小例子已有该 wheel 的实际参考输出。

## 安装与加载

平台先检查实际运行条件，再准备兼容的 Python 执行环境与所选功能依赖。不得假设宿主已安装 Python。
可在宿主的隔离环境，或由平台管理的兼容容器、虚拟机、远程 worker 中运行；实际平台链路必须能够读取输入和回传结果。
不限定接收平台使用 Ubuntu 或其他某个 OS。

本版 wheel 的 `Requires-Python` 为 `>=3.10`；这不保证每个 Python 3.10 环境都能安装全部可选依赖，
还须满足所选 NumPy/JAX 等依赖各自的版本与平台条件。科学依赖约束和原容差保持不变。

运行环境准备好后，可从测试材料所在目录安装依赖和 wheel。以下 `python` 指该执行环境的解释器：

```bash
python -m pip install -r requirements.txt
python -m pip install scirel-0.2.0.dev2+review20261008-py3-none-any.whl
```

```python
import scirel
print(scirel.__version__)  # 0.2.0.dev2+review20261008

import jax
jax.config.update("jax_enable_x64", True)
from scirel.fusion.grid import make_grid, radial_gradient
```

第一组剖面任务使用 NumPy/JAX 数值依赖。测试材料列出的闭包为
`numpy==2.5.3`、`jax==0.11.2`、`jaxlib==0.11.2`、`scipy==1.18.1`、`ml_dtypes==0.6.0`、`opt_einsum==3.4.0`。
这个清单绑定已有参考运行，不指定平台宿主必须复刻其 OS 或预装状态；其他组合的支持需实际验证。
绘图可由平台使用自己的工具，或自行安装兼容的绘图库以交付 PNG；这些数值函数不要求安装 CodeFusion、SciRel 开发工具或原来源 checkout。

## 按功能选择依赖

| 功能 | 注意事项 |
| --- | --- |
| 径向网格、梯度、边界补点 | 使用测试材料的 NumPy/JAX 依赖；参考容差需要先启用 JAX 64 位 |
| 约化初始化、时间演化、诊断 | 还需按实际模型选择核对完整运行闭包；不要以最小网格例子可跑推断所有模型可跑 |
| G-EQDSK 几何 | 部分等值线与缺失边界重建路径使用 Matplotlib；最小 `fusion` extra 不代表完整 G-EQDSK 环境 |
| 优化 | 入口以 Optax 为可选优化依赖；具体 pytree 类型和模型执行环境需另行核对 |
| QLKNN 神经代理 | 需要外部 `fusion_surrogates` 后端及模型；本 wheel 不分发受限权重，最小任务未验证该后端 |

包模块采用延迟导入：`import scirel` 成功只证明顶层可加载，不证明某个可选功能的依赖齐全。
原依赖失败、模型失败和非有限返回保持原实现行为；使用方必须查看所选功能的限制和输出。

## 文档的长期版本规则

领域主题保持稳定，新增实现接入相应主题；函数参考随实际 wheel 更新。
HTML、Markdown 和 Agent 索引由同一源生成，并记录科学包与文档摘要。
新 wheel 的功能和验证状态以它自己的版本文档为准，不能沿用本版结论。
