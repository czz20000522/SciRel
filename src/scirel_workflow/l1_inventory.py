"""Build a small, reproducible index from saved L1 project artifacts.

The index is an input adapter for the development workflow. It records paths,
digests and explicit gaps; it never copies source projects or infers scientific
metadata from names and implementation code.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from pathlib import Path
from typing import Iterable

from .models import digest


INVENTORY_SCHEMA = "scirel.l1-inventory.dev"
_ASSET_DIRS = ("operators/", "task_graphs/")
_NULL_ASSET_REFS = {"null", "Null", "NULL", "~"}
_ASSET_REF = re.compile(
    r"(?:^|[{,])\s*asset_ref\s*:\s*"
    r'(?:"([^\"]+)"|\'([^\']+)\'|([^,}#\r\n]+))'
)


def _path(value: Path, root: Path) -> str:
    return value.relative_to(root).as_posix()


def _file_digest(files: Iterable[tuple[str, Path]]) -> str:
    hasher = hashlib.sha256()
    for relative, path in sorted(files, key=lambda item: item[0]):
        hasher.update(relative.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(path.read_bytes())
        hasher.update(b"\0")
    return "sha256:" + hasher.hexdigest()


def _read_digest(path: Path) -> str:
    return _file_digest(((path.name, path),))


def _dependency_refs(path: Path) -> tuple[str, ...]:
    if not path.is_file():
        return ()
    refs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        for match in _ASSET_REF.finditer(line):
            ref = next(
                value for value in match.groups() if value is not None
            ).strip().replace("\\", "/")
            if ref and ref not in _NULL_ASSET_REFS and ref not in refs:
                refs.append(ref)
    return tuple(refs)


@dataclass(frozen=True)
class L1AssetEntry:
    """One operator or task graph found under a saved project."""

    project_id: str
    kind: str
    name: str
    asset_path: str
    contract_path: str | None
    implementation_path: str | None
    direct_test_path: str | None
    dependency_refs: tuple[str, ...]
    source_digest: str
    gaps: tuple[str, ...] = ()

    @property
    def asset_id(self) -> str:
        return f"{self.project_id}:{self.kind}:{self.name}"

    def to_dict(self) -> dict[str, object]:
        return {
            "l1_asset_id": self.asset_id,
            "project_id": self.project_id,
            "asset_kind": self.kind,
            "asset_name": self.name,
            "asset_path": self.asset_path,
            "contract_path": self.contract_path,
            "implementation_path": self.implementation_path,
            "direct_test_path": self.direct_test_path,
            "dependency_refs": list(self.dependency_refs),
            "source_digest": self.source_digest,
            "gaps": list(self.gaps),
        }


@dataclass(frozen=True)
class L1ProjectInventory:
    """Inventory for one source project, without embedding its files."""

    project_id: str
    ledger_path: str | None
    framework_map_path: str | None
    ledger_digest: str | None
    framework_map_digest: str | None
    assets: tuple[L1AssetEntry, ...]
    gaps: tuple[str, ...] = ()

    @property
    def operator_count(self) -> int:
        return sum(asset.kind == "operator" for asset in self.assets)

    @property
    def task_graph_count(self) -> int:
        return sum(asset.kind == "task_graph" for asset in self.assets)

    @property
    def project_digest(self) -> str:
        return digest(
            {
                "project_id": self.project_id,
                "ledger_digest": self.ledger_digest,
                "framework_map_digest": self.framework_map_digest,
                "assets": [asset.to_dict() for asset in self.assets],
                "gaps": list(self.gaps),
            }
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "project_id": self.project_id,
            "ledger_path": self.ledger_path,
            "framework_map_path": self.framework_map_path,
            "ledger_digest": self.ledger_digest,
            "framework_map_digest": self.framework_map_digest,
            "project_digest": self.project_digest,
            "operator_count": self.operator_count,
            "task_graph_count": self.task_graph_count,
            "asset_count": len(self.assets),
            "assets": [asset.to_dict() for asset in self.assets],
            "gaps": list(self.gaps),
        }


@dataclass(frozen=True)
class L1Inventory:
    """A deterministic, project-level index suitable for candidate creation."""

    projects: tuple[L1ProjectInventory, ...]
    source_root: str = "saved-l1-projects"

    @property
    def operator_count(self) -> int:
        return sum(project.operator_count for project in self.projects)

    @property
    def task_graph_count(self) -> int:
        return sum(project.task_graph_count for project in self.projects)

    @property
    def asset_count(self) -> int:
        return self.operator_count + self.task_graph_count

    @property
    def inventory_digest(self) -> str:
        return digest({"projects": [project.to_dict() for project in self.projects]})

    @property
    def inventory_id(self) -> str:
        return "l1-inventory-" + self.inventory_digest.removeprefix("sha256:")[:16]

    def _dependency_check(self, project: L1ProjectInventory) -> dict[str, object]:
        known = {asset.asset_path.rstrip("/") for asset in project.assets}
        missing = []
        invalid = []
        issues = []
        graph = {
            asset.asset_path.rstrip("/"): tuple(
                reference.rstrip("/")
                for reference in asset.dependency_refs
                if reference.rstrip("/") in known
                and reference.startswith("task_graphs/")
            )
            for asset in project.assets
            if asset.kind == "task_graph"
        }
        for asset in project.assets:
            for ref in asset.dependency_refs:
                if not ref.startswith(_ASSET_DIRS):
                    invalid.append(f"{asset.asset_id} -> {ref}")
                    issues.append(
                        {
                            "code": "invalid_task_graph_dependency_ref",
                            "severity": "blocking",
                            "asset_id": asset.asset_id,
                            "reference": ref,
                            "automation": "request_rework",
                        }
                    )
                elif ref.rstrip("/") not in known:
                    missing.append(f"{asset.asset_id} -> {ref}")
                    issues.append(
                        {
                            "code": "unresolved_task_graph_dependency",
                            "severity": "blocking",
                            "asset_id": asset.asset_id,
                            "reference": ref,
                            "automation": "resolve_or_request_evidence",
                        }
                    )
        cycles = _dependency_cycles(graph)
        for cycle in cycles:
            issues.append(
                {
                    "code": "task_graph_cycle",
                    "severity": "blocking",
                    "detail": cycle,
                    "automation": "request_rework",
                }
            )
        return {
            "name": "dependency_closure",
            "project_id": project.project_id,
            "status": "passed" if not missing and not invalid and not cycles else "failed",
            "missing": missing,
            "invalid": invalid,
            "cycles": list(cycles),
            "issues": issues,
        }

    def _checks_for_project(self, project: L1ProjectInventory) -> tuple[dict[str, object], ...]:
        asset_gaps = [
            f"{asset.asset_id}: {gap}"
            for asset in project.assets
            for gap in asset.gaps
            if not gap.startswith("missing_test:")
        ]
        asset_issues = [
            {
                "code": "missing_l1_asset_file",
                "severity": "blocking",
                "asset_id": asset.asset_id,
                "detail": gap,
                "automation": "request_rework",
            }
            for asset in project.assets
            for gap in asset.gaps
            if not gap.startswith("missing_test:")
        ]
        missing_tests = [
            asset.asset_id for asset in project.assets if asset.direct_test_path is None
        ]
        record_issues = [
            {
                "code": "missing_l1_project_record",
                "severity": "blocking",
                "project_id": project.project_id,
                "detail": gap,
                "automation": "request_rework",
            }
            for gap in project.gaps
        ]
        test_issues = [
            {
                "code": "missing_direct_test_mapping",
                "severity": "blocking",
                "asset_id": asset_id,
                "automation": "discover_or_generate_test",
            }
            for asset_id in missing_tests
        ]
        return (
            {
                "name": "asset_records",
                "project_id": project.project_id,
                "status": "passed" if not asset_gaps else "failed",
                "gaps": asset_gaps,
                "issues": asset_issues,
            },
            {
                "name": "required_project_records",
                "project_id": project.project_id,
                "status": "passed" if not project.gaps else "failed",
                "gaps": list(project.gaps),
                "issues": record_issues,
            },
            self._dependency_check(project),
            {
                "name": "direct_test_mapping",
                "project_id": project.project_id,
                "status": "passed" if not missing_tests else "failed",
                "missing": missing_tests,
                "issues": test_issues,
            },
        )

    def automated_checks(self) -> tuple[dict[str, object], ...]:
        checks: list[dict[str, object]] = []
        for project in self.projects:
            checks.extend(self._checks_for_project(project))
        return tuple(checks)

    def gaps(self) -> tuple[str, ...]:
        gaps = [
            f"{project.project_id}: {gap}"
            for project in self.projects
            for gap in project.gaps
        ]
        for check in self.automated_checks():
            if check["status"] == "failed":
                for item in (
                    *check.get("missing", ()),
                    *check.get("invalid", ()),
                    *check.get("cycles", ()),
                    *check.get("gaps", ()),
                ):
                    gaps.append(f"{check['project_id']}: {check['name']}: {item}")
        return tuple(dict.fromkeys(gaps))

    def to_l1_payload(self) -> dict[str, object]:
        """Project the index into the existing CandidatePackage L1 shape."""

        assets = [asset.to_dict() for project in self.projects for asset in project.assets]
        return {
            "schema": INVENTORY_SCHEMA,
            "inventory_id": self.inventory_id,
            "inventory_digest": self.inventory_digest,
            "projects": [project.to_dict() for project in self.projects],
            "counts": {
                "projects": len(self.projects),
                "operators": self.operator_count,
                "task_graphs": self.task_graph_count,
                "assets": self.asset_count,
            },
            "assets": assets,
            "automated_checks": list(self.automated_checks()),
            "gaps": list(self.gaps()),
        }

    def to_project_l1_payloads(self) -> tuple[dict[str, object], ...]:
        """Project each source project separately for candidate isolation."""

        payloads = []
        for project in self.projects:
            checks = self._checks_for_project(project)
            project_gaps = list(project.gaps)
            for check in checks:
                if check["status"] == "failed":
                    for item in (
                        *check.get("missing", ()),
                        *check.get("invalid", ()),
                        *check.get("cycles", ()),
                        *check.get("gaps", ()),
                    ):
                        project_gaps.append(f"{check['name']}: {item}")
            payloads.append(
                {
                    "schema": INVENTORY_SCHEMA,
                    "inventory_id": f"{self.inventory_id}:{project.project_id}",
                    "inventory_digest": project.project_digest,
                    "project_id": project.project_id,
                    "projects": [project.to_dict()],
                    "counts": {
                        "projects": 1,
                        "operators": project.operator_count,
                        "task_graphs": project.task_graph_count,
                        "assets": len(project.assets),
                    },
                    "assets": [asset.to_dict() for asset in project.assets],
                    "automated_checks": list(checks),
                    "gaps": list(dict.fromkeys(project_gaps)),
                }
            )
        return tuple(payloads)

    def to_dict(self) -> dict[str, object]:
        return self.to_l1_payload()


def _asset_entry(project_id: str, root: Path, kind: str, directory: Path) -> L1AssetEntry:
    files = {
        "contract": directory / ("operator.md" if kind == "operator" else "task_graph.yaml"),
        "implementation": directory / ("scientific_operator.py" if kind == "operator" else "graph.py"),
        "test": directory / ("test_scientific_operator.py" if kind == "operator" else "test_task_graph.py"),
    }
    gaps = tuple(
        f"missing_{label}:{_path(path, root)}"
        for label, path in files.items()
        if not path.is_file()
    )
    digest_files = [(key, path) for key, path in files.items() if path.is_file()]
    dependency_refs = _dependency_refs(files["contract"]) if kind == "task_graph" else ()
    return L1AssetEntry(
        project_id=project_id,
        kind=kind,
        name=directory.name,
        asset_path=_path(directory, root),
        contract_path=_path(files["contract"], root) if files["contract"].is_file() else None,
        implementation_path=(
            _path(files["implementation"], root)
            if files["implementation"].is_file()
            else None
        ),
        direct_test_path=_path(files["test"], root) if files["test"].is_file() else None,
        dependency_refs=dependency_refs,
        source_digest=_file_digest(digest_files),
        gaps=gaps,
    )


def _dependency_cycles(graph: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    """Return deterministic cycle descriptions for task-graph dependencies."""

    cycles: set[str] = set()
    visiting: list[str] = []
    active: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in active:
            start = visiting.index(node)
            cycle = (*visiting[start:], node)
            rotations = [
                cycle[index:-1] + cycle[:index] + (cycle[index],)
                for index in range(len(cycle) - 1)
            ]
            cycles.add(" -> ".join(min(rotations)))
            return
        if node in visited:
            return
        active.add(node)
        visiting.append(node)
        for dependency in graph.get(node, ()):
            visit(dependency)
        visiting.pop()
        active.remove(node)
        visited.add(node)

    for node in sorted(graph):
        visit(node)
    return tuple(sorted(cycles))


def build_project_inventory(project_root: Path, *, project_id: str | None = None) -> L1ProjectInventory:
    """Index one saved project and preserve missing records as explicit gaps."""

    project_root = project_root.resolve()
    if not project_root.is_dir():
        raise ValueError(f"L1 project directory does not exist: {project_root}")
    project_id = project_id or project_root.name
    ledger = project_root / "extraction_ledger.md"
    framework = project_root / "program_framework_map.md"
    gaps = []
    if not ledger.is_file():
        gaps.append("missing_extraction_ledger")
    if not framework.is_file():
        gaps.append("missing_program_framework_map")
    assets: list[L1AssetEntry] = []
    for kind, dirname in (("operator", "operators"), ("task_graph", "task_graphs")):
        parent = project_root / dirname
        if not parent.is_dir():
            gaps.append(f"missing_{dirname}_directory")
            continue
        for directory in sorted(
            (item for item in parent.iterdir() if item.is_dir()), key=lambda item: item.name
        ):
            assets.append(_asset_entry(project_id, project_root, kind, directory))
    return L1ProjectInventory(
        project_id=project_id,
        ledger_path=_path(ledger, project_root) if ledger.is_file() else None,
        framework_map_path=_path(framework, project_root) if framework.is_file() else None,
        ledger_digest=_read_digest(ledger) if ledger.is_file() else None,
        framework_map_digest=_read_digest(framework) if framework.is_file() else None,
        assets=tuple(assets),
        gaps=tuple(gaps),
    )


def build_inventory(root: Path, *, project_ids: Iterable[str] | None = None) -> L1Inventory:
    """Build an index for all selected child projects under ``root``."""

    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"L1 project root does not exist: {root}")
    selected = set(project_ids or ())
    directories = [item for item in root.iterdir() if item.is_dir() and not item.name.startswith(".")]
    if selected:
        unknown = selected - {item.name for item in directories}
        if unknown:
            raise ValueError(f"unknown L1 projects: {', '.join(sorted(unknown))}")
        directories = [item for item in directories if item.name in selected]
    if not directories:
        raise ValueError("no L1 project directories found")
    projects = tuple(
        build_project_inventory(directory)
        for directory in sorted(directories, key=lambda item: item.name)
    )
    project_keys = [project.project_id.casefold() for project in projects]
    if len(project_keys) != len(set(project_keys)):
        raise ValueError("L1 project IDs must be unique")
    return L1Inventory(projects=projects)
