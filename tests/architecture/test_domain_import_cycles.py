"""两两领域不得互相依赖，函数体内的导入与相对导入同样计入。"""

from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / "src" / "scirel"

# 组装层是根级私有包，但它 import 公开领域；把它单独作为一个节点参与判环，
# 其余根级私有模块（_result/_numerics 等）是叶子，不参与领域图。
COMPOSITION_LAYER = "_framework_compositions"


def module_name(path: Path, source: Path = SOURCE) -> str:
    """返回 ``source`` 下某个文件对应的点分模块名。"""
    relative = path.relative_to(source.parent)
    parts = (
        list(relative.parent.parts)
        if path.name == "__init__.py"
        else list(relative.with_suffix("").parts)
    )
    return ".".join(parts)


def public_domains(root: Path = SOURCE) -> frozenset[str]:
    """返回参与依赖图的单位：公开领域目录 + 组装层。

    下划线开头的其他私有目录是叶子模块，不属于任何领域，不进图。
    """
    units = {
        child.name for child in root.iterdir() if child.is_dir() and not child.name.startswith("_")
    }
    if (root / COMPOSITION_LAYER).is_dir():
        units.add(COMPOSITION_LAYER)
    return frozenset(units)


def domain_of(module: str, domains: frozenset[str]) -> str | None:
    """返回模块所属的单位（公开领域或组装层），不在图里时返回 ``None``。"""
    parts = module.split(".")
    if len(parts) < 2 or parts[1] not in domains:
        return None
    return parts[1]


def imported_targets(tree: ast.AST, module: str, domains: frozenset[str], *, is_package: bool):
    """产出 ``(目标领域, 行号, 是否在函数体内)``，覆盖 import / from 与相对导入。

    ``ast.walk`` 会进入函数体内，因此函数里写的导入同样被检查；相对导入按当前
    模块所在的包解析。
    """
    package = module if is_package else module.rsplit(".", 1)[0]
    for node, in_function in _walk_with_function_context(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                target = domain_of(alias.name, domains)
                if target is not None:
                    yield target, node.lineno, in_function
        elif isinstance(node, ast.ImportFrom):
            absolute = _absolute_target(node, package)
            if absolute is None:
                continue
            seen = set()
            candidates = [absolute] + [
                f"{absolute}.{alias.name}" for alias in node.names if alias.name != "*"
            ]
            for candidate in candidates:
                target = domain_of(candidate, domains)
                if target is not None and target not in seen:
                    seen.add(target)
                    yield target, node.lineno, in_function


def _walk_with_function_context(node: ast.AST, in_function: bool = False):
    for child in ast.iter_child_nodes(node):
        deeper = in_function or isinstance(
            child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)
        )
        yield child, deeper
        yield from _walk_with_function_context(child, deeper)


def _absolute_target(node: ast.ImportFrom, package: str) -> str | None:
    """把 ``from`` 导入解析成绝对模块名；不是 scirel 内部的导入返回 ``None``。"""
    target = node.module or ""
    if node.level:
        base = package
        for _ in range(node.level - 1):
            base = base.rsplit(".", 1)[0]
        target = f"{base}.{target}" if target else base
    return target if target == "scirel" or target.startswith("scirel.") else None


def domain_edges(root: Path = SOURCE):
    """返回 ``(边, 函数体内边)``，边形如 ``(源领域, 目标领域, 文件, 行号)``。"""
    domains = public_domains(root)
    edges = []
    nested = []
    files = sorted(root.rglob("*.py"))
    for path in files:
        module = module_name(path, root)
        source = domain_of(module, domains)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        is_package = path.name == "__init__.py"
        for target, line, in_function in imported_targets(
            tree, module, domains, is_package=is_package
        ):
            if source is None or target == source:
                continue
            edge = (source, target, str(path.relative_to(root.parent.parent)), line)
            edges.append(edge)
            if in_function:
                nested.append(edge)
    return edges, nested, len(files)


def strongly_connected(edges) -> list[list[str]]:
    """返回规模大于 1 的强连通分量，也就是有向图里真实存在的环。"""
    graph = defaultdict(set)
    for source, target, *_ in edges:
        graph[source].add(target)
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    components: list[list[str]] = []
    counter = [0]

    def visit(node: str) -> None:
        index[node] = low[node] = counter[0]
        counter[0] += 1
        stack.append(node)
        on_stack.add(node)
        for neighbour in graph[node]:
            if neighbour not in index:
                visit(neighbour)
                low[node] = min(low[node], low[neighbour])
            elif neighbour in on_stack:
                low[node] = min(low[node], index[neighbour])
        if low[node] == index[node]:
            component = []
            while True:
                member = stack.pop()
                on_stack.discard(member)
                component.append(member)
                if member == node:
                    break
            if len(component) > 1:
                components.append(sorted(component))

    for node in sorted(graph):
        if node not in index:
            visit(node)
    return components


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
