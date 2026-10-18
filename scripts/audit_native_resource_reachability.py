"""Audit native resource reachability without changing the package closure.

This is a conservative, source-side audit.  It records declared native
entrypoints, statically visible local-resource edges, and files that are not
reachable from those entrypoints.  Dynamic dispatch and source-tree copies
are represented as explicit dynamic roots so an audit result never authorizes
deleting a resource.  The report is diagnostic input for a later split of
runtime resources from retained provenance/compatibility sources.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "release/wheel/native-resource-closure.json"
SCHEMA = "scirel.native-resource-reachability.v1"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _strip_comments(text: str) -> str:
    """Remove Octave comments while preserving quoted strings."""

    rows: list[str] = []
    for line in text.splitlines():
        quoted = False
        output: list[str] = []
        index = 0
        while index < len(line):
            char = line[index]
            if char == "'":
                output.append(char)
                if index + 1 < len(line) and line[index + 1] == "'":
                    output.append("'")
                    index += 2
                    continue
                quoted = not quoted
            elif char == "%" and not quoted:
                break
            else:
                output.append(char)
            index += 1
        rows.append("".join(output))
    return "\n".join(rows)


def _resource_paths(root: Path, manifest: dict[str, Any]) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    source_root = root / manifest["source_root"]
    for group in manifest["groups"]:
        for relative in group["files"]:
            path = source_root / relative
            if relative in paths:
                raise ValueError(f"duplicate native resource: {relative}")
            if not path.is_file() or path.is_symlink():
                raise ValueError(f"native resource is missing: {relative}")
            paths[relative] = path
    return paths


def _static_edges(paths: dict[str, Path]) -> dict[str, list[str]]:
    by_name: dict[str, list[str]] = {}
    for relative in paths:
        by_name.setdefault(Path(relative).name, []).append(relative)
    stems = {Path(relative).stem for relative in paths}
    edges: dict[str, list[str]] = {}
    for relative, path in paths.items():
        text = _strip_comments(path.read_text(encoding="utf-8", errors="replace"))
        names: set[str] = set()
        for literal in re.findall(r"['\"]([^'\"]+)['\"]", text):
            name = Path(literal).name
            if name in by_name:
                names.add(name)
        for token in re.findall(r"\brun\s*(?:\(\s*)?([^\s;,\)]+)", text):
            name = Path(token.strip("'\"" )).name
            if name in by_name or name + ".m" in by_name:
                names.add(name)
        for stem in stems:
            if stem != path.stem and re.search(rf"(?<![A-Za-z0-9_]){re.escape(stem)}\s*\(", text):
                names.add(stem)
        targets: set[str] = set()
        for name in names:
            targets.update(by_name.get(name, ()))
            if not name.endswith(".m"):
                targets.update(by_name.get(name + ".m", ()))
        edges[relative] = sorted(targets)
    return edges


def _dynamic_edges(paths: dict[str, Path]) -> dict[str, list[str]]:
    """Resolve bounded ``feval(method, ...)`` dispatch from method literals.

    Octave entrypoints sometimes validate a finite method set and then call
    ``feval(method, ...)``.  A direct-call scan cannot see those edges, so
    retain the literal method names that also name resources in this closure.
    This is diagnostic metadata only; it never authorizes deleting a source
    file or infers dispatch for an unbounded value.
    """

    by_name: dict[str, list[str]] = {}
    for relative in paths:
        by_name.setdefault(Path(relative).name, []).append(relative)
    edges: dict[str, list[str]] = {}
    for relative, path in paths.items():
        text = _strip_comments(path.read_text(encoding="utf-8", errors="replace"))
        if not re.search(r"\bfeval\s*\(\s*method\b", text):
            continue
        names: set[str] = set()
        for literal in re.findall(r"['\"]([^'\"]+)['\"]", text):
            name = Path(literal).name
            if name in by_name or name + ".m" in by_name:
                names.add(name)
        # A method literal can also name a direct branch (for example,
        # ``fb_special`` handles ``zfun`` without ``feval``).  Keep only
        # names that are not visibly invoked directly in this source; the
        # result remains conservative for opaque dispatch.
        names = {
            name
            for name in names
            if not re.search(rf"(?<![A-Za-z0-9_]){re.escape(name)}\s*\(", text)
        }
        targets: set[str] = set()
        for name in names:
            targets.update(by_name.get(name, ()))
            if not name.endswith(".m"):
                targets.update(by_name.get(name + ".m", ()))
        if targets:
            edges[relative] = sorted(targets)
    return edges


def _group_entries(group_id: str, files: list[str]) -> tuple[list[str], str]:
    if group_id == "fluidbw-octave":
        names = {"fb_special.m", "fb_evaluate.m", "fb_bonk.m", "fb_assemble.m", "fb_em.m", "fb_materials.m"}
        return sorted(path for path in files if Path(path).name in names), "Python fluidbw.py _run entrypoints"
    if group_id == "pdrk-examples":
        names = {"fluid_plot_scan.m", "em1d_plot.m", "whamp_data.m", "whamp_overlay.m", "pdrf_SI.in"}
        return sorted(path for path in files if Path(path).name in names), "_example_native action registry"
    if group_id == "pdrk-finiteN":
        return [path for path in files if path.endswith("finiteN/action.m")], "_example_native finiteN action"
    if group_id == "pdrk-shared-plot-helper":
        return list(files), "example renderers call scirel_prepare_plot"
    if group_id == "pdrk-current-core":
        return sorted(path for path in files if "/code/" not in path), "magnetized.py wrappers and original program"
    if group_id == "pdrk-current-fixtures":
        return list(files), "declared SCENARIOS and setup_name/wpdat dynamic selection"
    if group_id == "pdrk-rational-legacy":
        return list(files), "rational.py model/script dynamic dispatch"
    return [], "no declared entrypoint"


def _dynamic_entries(group_id: str, files: list[str]) -> list[str]:
    """Return resources selected by runtime dispatch rather than static calls."""

    if group_id == "fluidbw-octave":
        # fb_special.m executes feval(method, ...), so the four named response
        # branches are runtime roots even though no literal call edge exists.
        names = {"RASY.m", "RINT.m", "RTAY.m", "RYLA.m"}
        return sorted(path for path in files if Path(path).name in names)
    return []


def audit(root: Path = ROOT, manifest_path: Path = MANIFEST) -> dict[str, Any]:
    manifest = _read_json(manifest_path)
    if manifest.get("schema") != "scirel.native-resource-closure.v1":
        raise ValueError("unexpected native closure schema")
    paths = _resource_paths(root, manifest)
    edges = _static_edges(paths)
    dynamic_edges = _dynamic_edges(paths)
    groups: dict[str, Any] = {}
    for group in manifest["groups"]:
        group_id = group["id"]
        files = sorted(group["files"])
        entrypoints, reason = _group_entries(group_id, files)
        dynamic_entries = _dynamic_entries(group_id, files)
        reachable = set(entrypoints) | set(dynamic_entries)
        todo = list(reachable)
        while todo:
            current = todo.pop()
            for target in (*edges.get(current, ()), *dynamic_edges.get(current, ())):
                if target in files and target not in reachable:
                    reachable.add(target)
                    todo.append(target)
        # Fixture, legacy and current code roots are selected dynamically by
        # public wrappers; retaining the entire declared root is deliberate.
        dynamic_root = group_id in {"pdrk-current-fixtures", "pdrk-rational-legacy"}
        if dynamic_root:
            reachable.update(files)
        groups[group_id] = {
            "entrypoints": entrypoints,
            "dynamic_entrypoints": dynamic_entries,
            "entrypoint_reason": reason,
            "reachable_files": sorted(reachable),
            "unreachable_candidates": [] if dynamic_root else sorted(set(files) - reachable),
            "dynamic_root": dynamic_root,
        }
    return {
        "schema": SCHEMA,
        "source_root": manifest["source_root"],
        "resource_count": len(paths),
        "groups": groups,
        "static_edges": {key: value for key, value in sorted(edges.items()) if value},
        "dynamic_edges": {key: value for key, value in sorted(dynamic_edges.items()) if value},
        "limitations": [
            "Dynamic dispatch and source-tree copies are represented as roots and are not deletion evidence.",
            "An unreachable candidate requires reverse-call confirmation and a negative runtime test before packaging changes.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.root.resolve(), args.manifest.resolve())
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
