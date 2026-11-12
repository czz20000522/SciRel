"""领域依赖必须符合 api-spec 的分层规则：向下自由、同层需白名单、私有清单封闭。"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _domain_imports import (  # noqa: E402
    COMPOSITION_LAYER,
    domain_edges,
    domain_imports,
)

SPEC = (
    Path(__file__).resolve().parents[2]
    / "skills/development/scirel-code-style/references/api-spec.md"
)
LAYER_TABLE = "| Layer | Domains |"
WHITELIST_HEADING = "Same-layer dependencies are allowed only from this whitelist:"
PRIVATE_HEADING = "Root-level private modules are not domains"
COMPOSITION_HEADING = "The one upward root dependency is the composition layer"


def _table_rows(lines: list[str], start: int) -> list[list[str]]:
    rows = []
    for line in lines[start:]:
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        rows.append(cells)
    return rows


def _backticked(cell: str) -> list[str]:
    return re.findall(r"`([^`]+)`", cell)


def _section_start(lines: list[str], heading: str, label: str) -> int:
    for index, line in enumerate(lines):
        if line.startswith(heading):
            return index
    raise ValueError(f"api-spec 缺少 {label} 段（以 {heading!r} 开头），依赖规则的依据无法定位")


def load_spec(text: str = None) -> dict:
    """解析 api-spec 的分层表、同层白名单、根级私有清单与组装层例外。"""
    lines = (text or SPEC.read_text(encoding="utf-8")).splitlines()
    layer_start = _section_start(lines, LAYER_TABLE, "分层表")
    layers = {}
    for cells in _table_rows(lines, layer_start + 2):
        match = re.match(r"L(\d+)", cells[0])
        if match:
            for name in _backticked(cells[1]):
                layers[name] = int(match.group(1))

    whitelist_start = _section_start(lines, WHITELIST_HEADING, "同层白名单")
    whitelist = set()
    for cells in _table_rows(lines, whitelist_start + 2):
        for pair in _backticked(cells[1]):
            source, _, target = pair.partition("→")
            whitelist.add((source.strip(), target.strip()))

    private_start = _section_start(lines, PRIVATE_HEADING, "根级私有清单")
    root_private = set()
    for cells in _table_rows(lines, private_start + 2):
        names = _backticked(cells[0])
        if names:
            root_private.add(names[0])

    composition_declared = any(line.startswith(COMPOSITION_HEADING) for line in lines)
    return {
        "layers": layers,
        "whitelist": whitelist,
        "root_private": root_private,
        "composition_declared": composition_declared,
    }


def test_the_rule_section_parses_into_the_expected_tables():
    """解析失败要大声报出来：否则规范改了形状，下面的断言会静默变空。"""
    spec = load_spec()
    assert len(spec["layers"]) == 25, spec["layers"]
    assert len(spec["whitelist"]) == 6, spec["whitelist"]
    assert {"_result", "_numerics", "_validation"} <= spec["root_private"], spec["root_private"]
    assert spec["composition_declared"]


def direction_problems(edges, layers, whitelist) -> list[str]:
    """返回违反「向上禁止、同层需白名单」的边；纯函数，便于用合成边验证。"""
    problems = []
    for source, target, path, line in edges:
        if source == COMPOSITION_LAYER:
            continue
        if target not in layers or source not in layers:
            problems.append(f"{source} -> {target}: 领域不在分层表里  {path}:{line}")
        elif layers[source] < layers[target]:
            problems.append(
                f"{source}(L{layers[source]}) -> {target}(L{layers[target]}): 向上依赖  {path}:{line}"
            )
        elif layers[source] == layers[target] and (source, target) not in whitelist:
            problems.append(f"{source} -> {target}: 同层但不在白名单  {path}:{line}")
    return problems


def test_domain_edges_go_down_or_are_whitelisted():
    spec = load_spec()
    edges, _, _ = domain_edges()
    problems = direction_problems(edges, spec["layers"], spec["whitelist"])
    assert not problems, "领域依赖违反分层规则：\n" + "\n".join(problems)


def test_direction_rule_reds_on_an_upward_and_an_unlisted_same_layer_edge():
    """判据本身会红：合成一条向上边和一条同层未列白名单的边。"""
    layers = {"low": 1, "high": 5}
    problems = direction_problems(
        [("high", "low", "x.py", 1), ("low", "high", "y.py", 2), ("low", "low", "z.py", 3)],
        layers,
        set(),
    )
    assert len(problems) == 2, problems
    assert any("向上依赖" in problem for problem in problems)
    assert any("同层但不在白名单" in problem for problem in problems)


def test_a_spec_without_the_whitelist_section_fails_loudly():
    spec_text = Path(SPEC).read_text(encoding="utf-8").replace(WHITELIST_HEADING, "Removed heading")
    try:
        load_spec(spec_text)
    except ValueError as error:
        assert "同层白名单" in str(error)
    else:
        raise AssertionError("缺少白名单段时 load_spec 必须报错")


def test_whitelist_names_only_edges_the_code_has():
    spec = load_spec()
    layers = spec["layers"]
    pairs = {(source, target) for source, target, *_ in domain_edges()[0]}
    problems = []
    for source, target in sorted(spec["whitelist"]):
        if (source, target) not in pairs:
            problems.append(f"白名单列了代码里不存在的边：{source} -> {target}")
        elif layers.get(source) != layers.get(target):
            problems.append(f"白名单只许管同层：{source} -> {target}")
    assert not problems, "\n".join(problems)


def test_domains_import_only_listed_root_private_modules():
    spec = load_spec()
    records, _ = domain_imports()
    problems = []
    for source, target, path, line, _ in records:
        if source == COMPOSITION_LAYER:
            continue
        parts = target.split(".")
        if len(parts) > 1 and parts[1].startswith("_") and parts[1] not in spec["root_private"]:
            problems.append(f"{source} 导入了清单外的根级私有模块 {parts[1]}  {path}:{line}")
    assert not problems, "\n".join(problems)


def composition_problems(records, layers) -> list[str]:
    """返回组装层不合规的导入；纯函数，便于用合成树验证。

    ``from scirel import equilibrium`` 会同时产出父记录 ``scirel``（没有子模块）
    与目标记录 ``scirel.equilibrium``：父记录不是一次依赖，跳过；被点名的子模块
    另有一条记录，仍然会被检查。
    """
    problems = []
    for source, target, path, line, _ in records:
        if source != COMPOSITION_LAYER:
            continue
        parts = target.split(".")
        unit = parts[1] if len(parts) > 1 else None
        if unit is None or unit == COMPOSITION_LAYER:
            continue  # 包本身与组装层内部的相互导入都不是领域依赖
        if unit.startswith("_") or unit not in layers:
            problems.append(f"组装层导入了非公开领域 {target}  {path}:{line}")
    return problems


def test_composition_layer_only_wires_public_domains():
    spec = load_spec()
    records, _ = domain_imports()
    problems = composition_problems(records, spec["layers"])
    assert not problems, "\n".join(problems)


def test_composition_layer_alias_to_a_public_domain_passes(tmp_path):
    """根包别名是合法写法，不许因为父记录没有子模块而误判红。"""
    source = tmp_path / "src" / "scirel"
    (source / COMPOSITION_LAYER).mkdir(parents=True)
    (source / "equilibrium").mkdir()
    (source / "equilibrium" / "__init__.py").write_text("", encoding="utf-8")
    (source / COMPOSITION_LAYER / "__init__.py").write_text(
        "from scirel import equilibrium\n", encoding="utf-8"
    )

    records, _ = domain_imports(source)

    assert composition_problems(records, {"equilibrium": 5}) == []


def test_composition_layer_private_or_unknown_targets_fail(tmp_path):
    source = tmp_path / "src" / "scirel"
    (source / COMPOSITION_LAYER).mkdir(parents=True)
    (source / "equilibrium").mkdir()
    (source / "equilibrium" / "__init__.py").write_text("", encoding="utf-8")
    (source / COMPOSITION_LAYER / "__init__.py").write_text(
        "from scirel import _result\nimport scirel.not_a_domain\n", encoding="utf-8"
    )

    records, _ = domain_imports(source)

    problems = composition_problems(records, {"equilibrium": 5})
    assert len(problems) == 2, problems
    assert any("_result" in problem for problem in problems)
    assert any("not_a_domain" in problem for problem in problems)
