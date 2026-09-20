import importlib.util
from pathlib import Path
import tempfile
import unittest


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "validate_import_intake_package.py"
)
SPEC = importlib.util.spec_from_file_location("validate_import_intake_package", SCRIPT)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class ImportIntakeLanguageContractTest(unittest.TestCase):
    def test_operator_contract_allows_a_trailing_known_gap_section(self) -> None:
        sections = "\n".join(
            f"## {heading}\n有效内容。" for heading in VALIDATOR.CHINESE_OPERATOR_HEADINGS
        )
        markdown = (
            "---\nlanguage: zh-CN\n---\n# 示例算子\n"
            f"{sections}\n## 已知缺口与待确认事项（Known Gaps and Open Questions）\n具体科学问题。\n"
        )
        errors: list[str] = []
        VALIDATOR._validate_chinese_operator_contract(
            markdown,
            source_path="operators/example/operator.md",
            errors=errors,
        )
        self.assertEqual(errors, [])

    def test_independent_implementation_evidence_does_not_require_invented_source_anchor(self) -> None:
        for declaration in (
            "source_unavailable: 历史源码无法核实，使用独立公式验证。",
            "示例是闭式公式核算，不声明历史源码逐值一致。",
        ):
            errors: list[str] = []
            VALIDATOR._validate_operator_evidence(
                "## 验证与溯源\n当前实现 scientific_operator.py:6-21。" + declaration,
                source_path="operators/example/operator.md", source_index=None, errors=errors,
            )
            self.assertEqual(errors, [], errors)

    def test_local_implementation_reference_alone_does_not_claim_original_source_evidence(self) -> None:
        errors: list[str] = []
        VALIDATOR._validate_operator_evidence(
            "## 验证与溯源\n当前实现 scientific_operator.py:6-21。",
            source_path="operators/example/operator.md", source_index=None, errors=errors,
        )
        self.assertTrue(any("original-source anchor" in error for error in errors), errors)

    def test_rejects_english_project_document(self) -> None:
        errors = self._validate_project_document("en-US")

        self.assertIn(
            "program_framework_map.md requires language: zh-CN during intake",
            errors,
        )

    def test_accepts_chinese_project_document(self) -> None:
        errors = self._validate_project_document("zh-CN")

        self.assertNotIn(
            "program_framework_map.md requires language: zh-CN during intake",
            errors,
        )

    def _validate_project_document(self, language: str) -> list[str]:
        temp_root = Path.cwd() / ".runtime" / "tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as temporary_directory:
            path = Path(temporary_directory) / "program_framework_map.md"
            path.write_text(f"---\nlanguage: {language}\n---\n", encoding="utf-8")
            return VALIDATOR.validate_import_intake_package(Path(temporary_directory))["errors"]

    def test_source_unavailable_still_requires_task_graph_structure(self) -> None:
        temp_root = Path.cwd() / ".runtime" / "tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as temporary_directory:
            root = Path(temporary_directory)
            task_graph_dir = root / "task_graphs" / "missing_structure"
            task_graph_dir.mkdir(parents=True)
            task_graph_file = task_graph_dir / "task_graph.md"
            sections = "\n".join(
                f"## {heading}\n源码对照状态：source_unavailable: 原始材料稍后补充"
                for heading in VALIDATOR.CHINESE_TASK_GRAPH_HEADINGS
            )
            task_graph_file.write_text(
                f"---\nlanguage: zh-CN\n---\n{sections}\n",
                encoding="utf-8",
            )
            errors: list[str] = []

            VALIDATOR._validate_task_graph_package(
                task_graph_dir,
                task_graph_file,
                root=root,
                errors=errors,
            )

            self.assertTrue(any("task_graph.yaml" in error for error in errors), errors)
            self.assertTrue(any("graph.py" in error for error in errors), errors)

    def test_rejects_scientifically_empty_operator_documentation(self) -> None:
        markdown = """
## 输入参数
- r_grid：这是一个尚未说明物理对象、轴含义或关系角色的通用数值输入说明；形状由接口决定；单位沿用约定；约束为有限。
- z_grid：这是一个尚未说明物理对象、轴含义或关系角色的通用数值输入说明；形状由接口决定；单位沿用约定；约束为有限。

## 输出参数
- field：数值输出；形状：与输入兼容；单位：沿用约定；约束：输出必须有限。

## 行为与边界
接口接收上述输入并返回输出，具体关系参见实现。

## 示例
最小调用：`from scientific_operator import scientific_operator`，按“语法”传入列出的参数并消费返回字段；包级有限输入与边界样例见 `test_scientific_operator.py`。
"""
        errors: list[str] = []
        VALIDATOR._validate_operator_documentation_quality(
            markdown,
            source_path="operators/example/operator.md",
            errors=errors,
        )

        self.assertTrue(
            any("repeated field boilerplate" in error for error in errors), errors
        )
        self.assertTrue(VALIDATOR._defers_scientific_behavior(markdown))
        self.assertGreaterEqual(len(errors), 2)

    def test_accepts_stage_one_contract_without_application_example(self) -> None:
        errors: list[str] = []
        VALIDATOR._validate_operator_documentation_quality(
            "## 解决的问题\n计算正交磁场分量的幅值。\n"
            "## 实现对应\n实现逐点计算两个分量的平方和平方根。\n"
            "## 行为与边界\n输入分量必须同形且有限。\n",
            source_path="operators/example/operator.md", errors=errors,
        )
        self.assertFalse(
            VALIDATOR._defers_scientific_behavior(
                "## 行为与边界\n输入分量必须同形且有限。\n"
            )
        )
        self.assertEqual(errors, [])

    def test_allows_a_physical_example_without_requiring_it(self) -> None:
        errors: list[str] = []
        VALIDATOR._validate_operator_documentation_quality(
            "## 示例\n具体使用参见 test_scientific_operator.py，输入满足约束即可。\n",
            source_path="operators/example/operator.md", errors=errors,
        )
        self.assertEqual(errors, [])

    def test_allows_candidate_local_executable_evidence(self) -> None:
        markdown = """
---
language: zh-CN
---
## 输入参数
- br：径向磁场，shape `[1,2]`，单位 T；约束：与 `bz` 同 shape 且有限。
## 输出参数
- B：极向场幅值，shape `[1,2]`，单位 T；约束：逐点不小于零。
## 行为与边界
逐点计算 `sqrt(br**2 + bz**2)`，并在零场处使用声明的下限。
## 示例
```python
result = scientific_operator([[3.0, 0.0]], [[4.0, 0.0]])
np.testing.assert_allclose(result["B"], [[5.0, 1.0e-30]])
```
"""
        errors: list[str] = []
        VALIDATOR._validate_operator_documentation_quality(
            markdown,
            source_path="operators/example/operator.md",
            errors=errors,
        )

        self.assertEqual(errors, [])

    def test_rejects_scirel_import_in_stage_one_candidate(self) -> None:
        errors: list[str] = []
        VALIDATOR._validate_operator_documentation_quality(
            "## SciRel 调用\n```python\nfrom scirel.geometry import circle_area\n```\n",
            source_path="operators/example/operator.md",
            errors=errors,
        )
        self.assertTrue(
            any("must not import the maintained SciRel package" in error for error in errors),
            errors,
        )

    def test_ignores_display_math_when_checking_human_facing_language(self) -> None:
        markdown = r"""
## 输入参数
- radius：半径网格；shape `[2]`；单位 m；约束：有限且非负。
## 输出参数
- area：面积；shape scalar；单位 m^2；约束：有限且非负。
## 科学或数值定义
计算圆面积：
\[
area = pi * radius^2
\]
## 行为与边界
半径必须为有限非负值。
## 实现对应
候选实现逐点计算圆面积关系。
"""
        errors: list[str] = []
        VALIDATOR._validate_operator_documentation_quality(
            markdown,
            source_path="operators/example/operator.md",
            errors=errors,
        )

        self.assertNotIn(
            "human-facing explanatory prose must use the declared zh-CN profile",
            "\n".join(errors),
        )

    def test_ignores_front_matter_and_bare_signature_when_checking_language(self) -> None:
        markdown = """
---
language: zh-CN
asset_kind: scientific_operator
---
# 双温镜不变量分布函数
## 语法
scientific_operator(v_parallel_m_s, magnetic_field_t) -> mapping
## 说明
计算给定速度和磁场下的分布函数。
"""

        self.assertFalse(VALIDATOR._contains_untranslated_prose(markdown))

    def test_rejects_actual_english_explanatory_prose_outside_front_matter(self) -> None:
        markdown = """
---
language: zh-CN
asset_kind: scientific_operator
---
## 说明
Evaluate the physical invariant distribution here.
"""

        self.assertTrue(VALIDATOR._contains_untranslated_prose(markdown))

        errors: list[str] = []
        VALIDATOR._validate_operator_documentation_quality(
            markdown,
            source_path="operators/example/operator.md",
            errors=errors,
        )
        language_error = next(
            error for error in errors if "human-facing explanatory prose" in error
        )
        self.assertRegex(language_error, r"offending lines:\s+\d+(?:,\s*\d+)*")

    def test_rejects_source_alias_as_public_port_meaning(self) -> None:
        markdown = """
## 解决的问题
该算子直接复现源码变量 `Vth` 的 source-order 计算。
## 输入参数
- thermal_speed_m_s：源码变量 `Vth` 的热速度；shape scalar；单位 m/s；约束：有限且为正。
## 输出参数
- flux：通量；shape scalar；单位 m^-2 s^-1；约束：有限。
## 科学或数值定义
通量由速度积分得到。
## 行为与边界
速度轴越界时失败。
## 实现对应
实现对速度轴进行积分并返回通量。
"""
        errors: list[str] = []
        VALIDATOR._validate_operator_documentation_quality(
            markdown,
            source_path="operators/example/operator.md",
            errors=errors,
        )

        self.assertTrue(any("source aliases" in error for error in errors), errors)

    def test_long_identifier_findings_are_chunked_without_losing_fields(self) -> None:
        identifiers = [f"very_long_return_field_{index:02d}" for index in range(40)]
        errors: list[str] = []

        VALIDATOR._append_identifier_findings(
            errors,
            "operator.md Outputs must enumerate the returned mapping fields",
            identifiers,
            "operators/example/operator.md",
        )

        self.assertGreater(len(errors), 1)
        self.assertTrue(all(len(error.encode("utf-8")) <= 480 for error in errors))
        self.assertTrue(all(identifier in "\n".join(errors) for identifier in identifiers))
