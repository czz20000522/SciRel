# Language Profiles

本文件定义算子包的固定实现语言。`operator.md` 固定使用 `language: zh-CN`；实现文件只允许使用下面两种 profile 之一。

## Core Rule

- 正式算子包只接受两种实现 profile：Python 和 C。
- Python 是解释性/参考实现轨道；C 是高性能/可嵌入实现轨道。
- C++、Fortran、MATLAB/Octave、Julia、Rust 等可以作为源码证据语言，但正式输出不得使用这些语言作为正式算子实现，除非用户明确改变项目标准。
- 不把创建者机器路径写进模板、参考案例或可共享产物。
- 测试命令必须能从算子包目录内相对运行。
- 外部源码、数据表或验证 fixture 用环境变量声明，例如 `SOURCE_ROOT=<source root>`。
- 源码证据引用优先使用 source-root-relative 行号，例如 `pkg/module.f90:20-80`。
- 运行环境写工具链和关键依赖，不写本机绝对路径。
- 最终算子目录不得保留测试/构建副产物；运行测试产生的缓存、字节码、临时可执行文件、对象文件和覆盖率输出必须在交付前清理。

## Language Selection

选择 Python profile，当：

- 原始源码是 Python，直接源码对照最可靠；
- 算子依赖 NumPy/SciPy 级别的线性代数、特殊函数、插值、优化、SVD、样条或稀疏矩阵；
- 需要受控补全、结构化诊断、失败原因、rank/residual/convergence 等 reviewer 可读输出；
- 科学合同还在稳定，优先保证正确性和可审查性；
- 目标是参考实现、验证 oracle、复杂源码改写过渡层或高可读性审查实现。

选择 C profile，当：

- 算子是稳定、局部、性能敏感的数值核；
- 输入输出能表达为标量、连续数组、显式长度和结构体；
- 主要依赖 ISO C、`math.h` 和少量包内常量/表数据；
- 需要被 Python、C/C++、Fortran 或其他系统通过稳定 ABI 调用；
- 可以用源码对照、golden fixture、独立公式、不变量和边界测试证明改写正确。

不要选择 C profile，当：

- 需要未声明的 BLAS/LAPACK、特殊函数库、复杂内存布局、隐式全局状态、设备对象、文件路径、绘图/交互或运行时配置；
- 从 Fortran/C++/MATLAB 改写到 C 时无法证明数组顺序、索引基准、精度、边界条件或单位约定；
- C 实现会迫使 Agent 发明缺失的表数据、闭合关系、调参常数、插值策略或物理边界条件。

## Python Profile

```text
<operator_name>/
  operator.md
  scientific_operator.py
  test_scientific_operator.py
```

Recommended test command:

```text
python -m pytest test_scientific_operator.py -q
```

Python 测试可使用 `SOURCE_ROOT=<source root>` 做源码对照。允许依赖测试环境已声明的 NumPy/SciPy/pytest。若需要其他依赖，必须在测试头和 `operator.md` 中说明。

## C Profile

```text
<operator_name>/
  operator.md
  scientific_operator.h
  scientific_operator.c
  test_scientific_operator.c
```

Recommended test command:

```text
cc scientific_operator.c test_scientific_operator.c -lm -o test_scientific_operator && ./test_scientific_operator
```

After recording the test result header, remove the generated `test_scientific_operator` executable before delivery unless the user explicitly requested compiled binaries as a separate artifact.

C profile 约定：

- 公开函数声明放在 `scientific_operator.h`，实现放在 `scientific_operator.c`。
- 测试必须编译并运行 `test_scientific_operator.c`，不能只检查编译成功。
- 优先使用 ISO C + `math.h`；非标准库、编译器扩展、OpenMP、BLAS/LAPACK、SIMD、平台特定选项必须在 `operator.md` 和测试头中声明。
- 数组输入必须显式传入长度、维度和 strides/布局约定；默认布局必须写清楚，例如 row-major。
- 返回错误时使用明确状态码、输出参数或结构体，不允许静默写全局变量。
- 如果源语言不是 C，测试必须覆盖源语言到 C 的改写正确性：索引基准、数组布局、边界条件、单位、精度和代表性数值。

## Test Evidence Header

Use the target language's native comment syntax. The labels stay stable:

```text
测试结果：
工作目录：<operator package directory or "this operator directory">
命令：<relative command from that directory>
环境变量：<none | NAME=<meaning>>
结果：<N passed / failed summary>
对照依据：<direct source parity | source-runnable subdomain parity + repaired boundary path | standard-case derived fixture | source-derived fixture | equation | invariant | boundary failure>
源码对照状态：<direct_source_runnable | source_unavailable: reason>
证据来源：<source-root-relative/path.ext:start-end::symbol or generated oracle description>
运行环境：<compiler/interpreter/runtime and key dependency versions>
```

Use `direct_source_runnable` for any test that imports, compiles, or subprocess-runs the source and compares candidate values. Put compile/run details in `对照依据`, `命令`, and `运行环境`; do not create extra status tokens.

If source parity only covers a source-runnable subdomain because the original source crashes or is undefined on a repaired path, keep `direct_source_runnable` only when the source actually runs, name the domain limit in `对照依据`, and cover the repaired path with a separate test.

Python comments use `#`. C comments should use a top-of-file `/* ... */` block with the same labels.

Each test function, test case, or test block must have a nearby Chinese comment explaining its reviewer-facing purpose.
