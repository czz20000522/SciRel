"""两两领域不得互相依赖，函数体内的导入与相对导入同样计入。"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _domain_imports import (  # noqa: E402
    domain_edges,
    imported_targets,
    strongly_connected,
)


def test_no_two_domains_depend_on_each_other():
    edges, _, scanned = domain_edges()
    assert scanned > 100, f"只扫描到 {scanned} 个文件，检查可能没有指向源码树"
    cycles = strongly_connected(edges)
    assert not cycles, "领域之间存在循环依赖（含函数体内导入）：\n" + _describe(cycles, edges)


def test_import_scan_reaches_function_bodies_and_relative_imports():
    """解析器本身要能下钻：否则顶层导入的绿是假绿。"""
    domains = frozenset({"alpha", "beta"})
    tree = ast.parse(
        "from scirel.beta import value\n"
        "def inside():\n"
        "    from . import helper\n"
        "    from ..beta.deep import other\n"
        "    import scirel.alpha.sub\n"
        "from scirel import beta as beta_package\n"
        "from .. import alpha as alpha_package\n"
    )
    found = sorted(imported_targets(tree, "scirel.alpha.module", domains, is_package=False))
    assert found == [
        ("alpha", 3, True),
        ("alpha", 5, True),
        ("alpha", 7, False),
        ("beta", 1, False),
        ("beta", 4, True),
        ("beta", 6, False),
    ], found


def test_cycle_visible_only_through_root_package_aliases_is_detected(tmp_path):
    """只在 ``from scirel import X`` 这种根包别名下存在的环，也必须被抓到。"""
    source = tmp_path / "src" / "scirel"
    for name in ("alpha", "beta"):
        (source / name).mkdir(parents=True)
    (source / "alpha" / "__init__.py").write_text("from scirel import beta\n", encoding="utf-8")
    (source / "beta" / "__init__.py").write_text("from scirel import alpha\n", encoding="utf-8")

    edges, _, scanned = domain_edges(source)

    assert scanned == 2
    assert strongly_connected(edges) == [["alpha", "beta"]], edges


def _describe(cycles, edges) -> str:
    lines = []
    for component in cycles:
        lines.append("环：" + " <-> ".join(component))
        members = set(component)
        for source, target, path, line in edges:
            if source in members and target in members:
                lines.append(f"  {source} -> {target}  {path}:{line}")
    return "\n".join(lines)
