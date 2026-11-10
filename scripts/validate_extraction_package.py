#!/usr/bin/env python3
"""Validate an extraction package against the frozen SciReL commit it was built on.

The package format is in
``skills/extraction/scientific-computation-asset-extraction/references/package-format.md``.
The same command is run by the extraction worker before archiving and by the maintenance line
before merging.

Checks, in order (each prints what it counted):

1. structure: the required files and directories exist;
2. PACKAGE.md: status, scope, frozen commit, full-check line, reconciliation line, open items;
3. manifest.md: one allowed conclusion per relation, contract IDs and domains, counts against
   the reconciliation line;
4. disposition.md: category and reason for every part not taken;
5. tickets/: every ticket follows the format and is still ``open``;
6. leak scan: no source identity (names listed in ``private/source.md``), private path or secret
   outside ``private/``, patch included;
7. patch: ``git am`` applies on the frozen commit; the patched catalog is a valid document set;
   every contract the patch adds or changes (its JSON, or the source module its ``public_api``
   names) is classified in manifest.md (added: 全新; changed: 新 method, or 已有 marked 物理纠正);
   every new or extended contract lives in the domain its ID names, has its
   ``verification.tests`` files and an ``evidence/<id>.md`` table;
8. full check: ``check_all.py`` on the patched tree;
9. mutation: ``mutation_check.py`` on every new or extended contract.

``--fast`` skips 8 and 9. They are then reported as NOT_RUN and the exit status is 2, never 0:
a fast run is a development aid, not acceptance.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ROOT / "skills/development/scirel-acceptance/scripts"))

import tickets  # noqa: E402
from precommit_check import FORBIDDEN  # noqa: E402
from validate_asset_documents import ASSET_ID_RE, AssetDocumentError, load_document_set  # noqa: E402

CONCLUSIONS = ("已有", "新 method", "全新", "不收")
IMPLEMENTED = ("新 method", "全新")
STATUSES = ("in_progress", "partial", "done")
DISPOSITION_CATEGORIES = (
    "画图",
    "IO / 路径 / 命令行",
    "流程编排",
    "包装类",
    "物理无关工具",
    "装置数据",
    "已有",
    "其他",
)
EVIDENCE_CATEGORIES = ("正常", "下界", "上界", "退化", "分支", "失败", "终止", "组合")
EVIDENCE_BASES = ("解析", "文献", "守恒", "来源输出")
RESULT_STATES = ("passed", "failed", "blocked", "NOT_RUN", "inapplicable")
LAYER_RE = re.compile(r"^L[0-5]$")
TEXT_SUFFIXES = {".md", ".py", ".json", ".toml", ".yaml", ".yml", ".txt", ".rst", ".patch", ".sh"}


class Report:
    def __init__(self) -> None:
        self.sections: list[tuple[str, str, str]] = []
        self.errors: list[str] = []

    def section(self, name: str, state: str, detail: str) -> None:
        self.sections.append((name, state, detail))

    def fail(self, name: str, message: str) -> None:
        self.errors.append(f"{name}: {message}")


def _field(text: str, label: str) -> str | None:
    match = re.search(rf"^- {re.escape(label)}[：:]\s*(.+?)\s*$", text, re.MULTILINE)
    return match.group(1) if match else None


def _section(text: str, heading: str) -> list[str] | None:
    match = re.search(
        rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL
    )
    if not match:
        return None
    return [line.strip() for line in match.group(1).splitlines() if line.strip().startswith("- ")]


def _table(text: str, first_column: str) -> tuple[list[str], list[list[str]]] | None:
    """Return the header and rows of the first Markdown table whose first column is given."""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.strip().startswith("|") and cells and cells[0] == first_column:
            rows = []
            for row in lines[index + 2 :]:
                if not row.strip().startswith("|"):
                    break
                rows.append([c.strip() for c in row.strip().strip("|").split("|")])
            return cells, rows
    return None


def check_structure(package: Path, report: Report) -> bool:
    required_files = ("PACKAGE.md", "manifest.md", "disposition.md", "private/source.md")
    required_dirs = ("patch", "evidence", "tickets", "private")
    missing = [p for p in required_files if not (package / p).is_file()]
    missing += [p + "/" for p in required_dirs if not (package / p).is_dir()]
    for item in missing:
        report.fail("structure", f"missing {item}")
    report.section(
        "structure",
        "FAIL" if missing else "PASS",
        f"{len(required_files) + len(required_dirs)} required entries, {len(missing)} missing",
    )
    return not missing


def check_package_md(package: Path, report: Report) -> dict:
    text = (package / "PACKAGE.md").read_text(encoding="utf-8")
    info: dict = {}
    errors_before = len(report.errors)
    status = _field(text, "状态")
    if status not in STATUSES:
        report.fail("PACKAGE.md", f"状态 must be one of {', '.join(STATUSES)}; got {status!r}")
    info["status"] = status
    if not _field(text, "范围"):
        report.fail("PACKAGE.md", "范围 is missing")
    commit = _field(text, "冻结 SciReL commit")
    if not commit or not re.fullmatch(r"[0-9a-f]{7,40}", commit):
        report.fail("PACKAGE.md", f"冻结 SciReL commit must be a hex commit id; got {commit!r}")
    info["commit"] = commit
    recon = _field(text, "对账") or ""
    match = re.fullmatch(
        r"关系卡\s*(\d+)\s*=\s*已有\s*(\d+)\s*\+\s*新 method\s*(\d+)\s*\+\s*全新\s*(\d+)\s*\+\s*不收\s*(\d+)",
        recon,
    )
    if not match:
        report.fail(
            "PACKAGE.md", "对账 must read '关系卡 N = 已有 a + 新 method m + 全新 n + 不收 d'"
        )
    else:
        total, *parts = (int(g) for g in match.groups())
        info["reconciliation"] = dict(zip(CONCLUSIONS, parts))
        if total != sum(parts):
            report.fail("PACKAGE.md", f"对账 does not add up: {total} != {sum(parts)}")
    full_check = _field(text, "完整检查") or ""
    info["full_check"] = full_check
    open_items = _section(text, "未完成项")
    if open_items is None:
        report.fail("PACKAGE.md", "section '## 未完成项' is missing")
    elif status == "done":
        real = [i for i in open_items if i not in ("- 无", "- （无）")]
        if real:
            report.fail("PACKAGE.md", f"状态 done but {len(real)} open items are listed")
        steps = re.search(r"steps\s*(\d+)\s*/\s*(\d+)", full_check)
        failed = re.search(r"失败\s*(\d+)", full_check)
        if "NOT_RUN" in full_check or not steps or not failed:
            report.fail(
                "PACKAGE.md", "状态 done needs a full-check line with steps x/y and 失败 count"
            )
        elif steps.group(1) != steps.group(2) or failed.group(1) != "0":
            report.fail("PACKAGE.md", f"状态 done but the full check is not green: {full_check}")
    elif not open_items:
        report.fail("PACKAGE.md", f"状态 {status} must list what is still open under '## 未完成项'")
    report.section(
        "PACKAGE.md",
        "FAIL" if len(report.errors) > errors_before else "PASS",
        f"status {status}, frozen commit {commit}",
    )
    return info


def check_manifest(package: Path, report: Report, info: dict) -> list[dict]:
    table = _table((package / "manifest.md").read_text(encoding="utf-8"), "关系")
    errors_before = len(report.errors)
    entries: list[dict] = []
    if table is None:
        report.fail("manifest.md", "no table whose first column is 关系")
        report.section("manifest.md", "FAIL", "no table")
        return entries
    header, rows = table
    expected = ["关系", "结论", "合同 ID", "领域 / 层", "族 / method", "题库题号", "备注"]
    if header != expected:
        report.fail("manifest.md", f"columns must be {' | '.join(expected)}")
        report.section("manifest.md", "FAIL", "wrong columns")
        return entries
    counts = dict.fromkeys(CONCLUSIONS, 0)
    for number, row in enumerate(rows, start=1):
        if len(row) != len(expected):
            report.fail(
                "manifest.md", f"row {number} has {len(row)} cells, expected {len(expected)}"
            )
            continue
        relation, conclusion, asset_id, domain_layer, family, _problem, note = row
        where = f"row {number} ({relation})"
        if conclusion not in CONCLUSIONS:
            report.fail(
                "manifest.md",
                f"{where}: 结论 must be one of {', '.join(CONCLUSIONS)}; got {conclusion!r}",
            )
            continue
        counts[conclusion] += 1
        entry = {
            "relation": relation,
            "conclusion": conclusion,
            "asset_id": asset_id,
            "note": note,
        }
        if conclusion == "不收":
            if asset_id not in ("—", "-", ""):
                report.fail("manifest.md", f"{where}: 不收 has no contract ID")
            entries.append(entry)
            continue
        if not ASSET_ID_RE.fullmatch(asset_id):
            report.fail("manifest.md", f"{where}: invalid contract ID {asset_id!r}")
            continue
        parts = [p.strip() for p in domain_layer.split("/")]
        if len(parts) != 2 or not LAYER_RE.fullmatch(parts[1]):
            report.fail(
                "manifest.md",
                f"{where}: 领域 / 层 must read like 'field / L3'; got {domain_layer!r}",
            )
        else:
            entry["domain"], entry["layer"] = parts
            if asset_id.split(".")[1] != parts[0]:
                report.fail(
                    "manifest.md",
                    f"{where}: ID domain {asset_id.split('.')[1]!r} != 领域 {parts[0]!r}",
                )
        if conclusion == "新 method" and family in ("—", "-", ""):
            report.fail("manifest.md", f"{where}: 新 method must name its family and method")
        entries.append(entry)
    recon = info.get("reconciliation")
    if recon and recon != counts:
        report.fail("manifest.md", f"counts {counts} do not match PACKAGE.md 对账 {recon}")
    detail = ", ".join(f"{k} {v}" for k, v in counts.items())
    report.section(
        "manifest.md",
        "FAIL" if len(report.errors) > errors_before else "PASS",
        f"{len(rows)} relations: {detail}",
    )
    return entries


def check_disposition(package: Path, report: Report, entries: list[dict]) -> None:
    table = _table(
        (package / "disposition.md").read_text(encoding="utf-8"), "来源部分（模块或文件的中性描述）"
    )
    errors_before = len(report.errors)
    rows = []
    if table is None:
        report.fail(
            "disposition.md", "no table whose first column is 来源部分（模块或文件的中性描述）"
        )
    else:
        rows = table[1]
        for number, row in enumerate(rows, start=1):
            if len(row) != 3:
                report.fail("disposition.md", f"row {number} needs 3 cells")
                continue
            if row[1] not in DISPOSITION_CATEGORIES:
                report.fail(
                    "disposition.md",
                    f"row {number}: 类别 must be one of {', '.join(DISPOSITION_CATEGORIES)}",
                )
            if not row[2] or (row[1] == "其他" and len(row[2]) < 4):
                report.fail("disposition.md", f"row {number}: 理由 is missing")
    rejected = sum(e["conclusion"] == "不收" for e in entries)
    if len(rows) < rejected:
        report.fail(
            "disposition.md",
            f"{rejected} relations are 不收 but only {len(rows)} disposition rows exist",
        )
    report.section(
        "disposition.md",
        "FAIL" if len(report.errors) > errors_before else "PASS",
        f"{len(rows)} rows, {rejected} 不收 relations",
    )


def check_tickets(package: Path, report: Report) -> None:
    files = sorted((package / "tickets").glob("*.md"))
    errors_before = len(report.errors)
    for path in files:
        for error in tickets.check(path.read_text(encoding="utf-8"), allowed_statuses=("open",)):
            report.fail("tickets", f"{path.name}: {error}")
    report.section(
        "tickets", "FAIL" if len(report.errors) > errors_before else "PASS", f"{len(files)} tickets"
    )


def _identity_tokens(package: Path) -> list[str]:
    text = (package / "private/source.md").read_text(encoding="utf-8")
    tokens = []
    for label in ("名称", "禁止出现"):
        value = _field(text, label)
        if value:
            tokens += [t.strip() for t in re.split(r"[,，、]", value) if len(t.strip()) >= 3]
    return tokens


def check_leaks(package: Path, report: Report) -> None:
    tokens = _identity_tokens(package)
    errors_before = len(report.errors)
    if not tokens:
        report.fail(
            "leak scan",
            "private/source.md must give '- 名称：<source name>' so its identity can be scanned for",
        )
    scanned = 0
    for path in sorted(package.rglob("*")):
        relative = path.relative_to(package)
        if not path.is_file() or relative.parts[0] == "private":
            continue
        if path.suffix not in TEXT_SUFFIXES and relative.parts[0] != "patch":
            continue
        scanned += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        lowered = text.lower()
        for token in tokens:
            if token.lower() in lowered:
                report.fail("leak scan", f"{relative}: contains source identity {token!r}")
        for label, pattern in FORBIDDEN.items():
            if match := pattern.search(text):
                report.fail("leak scan", f"{relative}: {label}: {match.group(0)}")
    report.section(
        "leak scan",
        "FAIL" if len(report.errors) > errors_before else "PASS",
        f"{scanned} files, {len(tokens)} identity tokens",
    )


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.update(
        GIT_AUTHOR_NAME="extraction-validator",
        GIT_AUTHOR_EMAIL="validator@invalid",
        GIT_COMMITTER_NAME="extraction-validator",
        GIT_COMMITTER_EMAIL="validator@invalid",
    )
    return subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True)


def apply_patch(
    package: Path, repo: Path, commit: str, workdir: Path, report: Report
) -> tuple[Path | None, set[str], list[str]]:
    patches = sorted((package / "patch").glob("*.patch"))
    tree = workdir / "tree"
    if not patches:
        report.fail("patch", "patch/ contains no *.patch files from git format-patch")
        report.section("patch", "FAIL", "0 patches")
        return None, set(), []
    if _git(["cat-file", "-e", f"{commit}^{{commit}}"], repo).returncode:
        report.fail("patch", f"frozen commit {commit} is not in {repo}")
        report.section("patch", "FAIL", "unknown commit")
        return None, set(), []
    done = _git(["worktree", "add", "--detach", str(tree), commit], repo)
    if done.returncode:
        report.fail("patch", f"cannot check out {commit}: {done.stderr.strip()}")
        report.section("patch", "FAIL", "checkout failed")
        return None, set(), []
    frozen_ids = {p.stem for p in (tree / "catalog/examples").glob("*.json")}
    done = _git(["am", "--keep-cr", *map(str, patches)], tree)
    if done.returncode:
        report.fail("patch", f"git am failed on {commit}: {(done.stdout + done.stderr).strip()}")
        report.section("patch", "FAIL", f"{len(patches)} patches, not applicable")
        return None, frozen_ids, []
    changed = _git(["diff", "--name-only", commit, "HEAD"], tree).stdout.split()
    leaked = [p for p in changed if p.startswith(("private/", "tickets/"))]
    for path in leaked:
        report.fail("patch", f"the patch must not add {path}")
    report.section(
        "patch",
        "FAIL" if leaked else "PASS",
        f"{len(patches)} patches applied, {len(changed)} files changed",
    )
    return tree, frozen_ids, changed


CORRECTION_NOTE = "物理纠正"


def _changed_contracts(
    changed: list[str], documents: dict[str, dict], frozen_ids: set[str]
) -> tuple[set[str], set[str], set[str], list[str]]:
    """Split the contracts a patch touches into added, modified and deleted.

    A contract counts as modified when its JSON changes or when a changed file under ``src/`` is
    the module its ``public_api`` names. Changed source files that are no contract's module are
    returned so the report can list them.
    """
    json_ids = {
        Path(p).stem for p in changed if p.startswith("catalog/examples/") and p.endswith(".json")
    }
    added = {i for i in json_ids if i not in frozen_ids}
    deleted = {i for i in json_ids if i in frozen_ids and i not in documents}
    modified = {i for i in json_ids if i in frozen_ids and i in documents}
    by_module: dict[str, set[str]] = {}
    for asset_id, document in documents.items():
        by_module.setdefault(document["public_api"]["python"]["module"], set()).add(asset_id)
    unmapped = []
    for path in changed:
        if not (path.startswith("src/") and path.endswith(".py")):
            continue
        module = ".".join(Path(path).with_suffix("").parts[1:])
        module = module.removesuffix(".__init__")
        owners = by_module.get(module, set()) - added
        if owners:
            modified |= owners & frozen_ids
        elif not by_module.get(module):
            unmapped.append(path)
    return added, modified, deleted, unmapped


def check_contracts(
    package: Path,
    tree: Path,
    frozen_ids: set[str],
    entries: list[dict],
    changed: list[str],
    report: Report,
) -> list[str]:
    errors_before = len(report.errors)
    try:
        documents = {d["asset_id"]: d for d in load_document_set(tree / "catalog/examples")}
    except AssetDocumentError as error:
        report.fail("contracts", f"patched catalog is not a valid document set: {error}")
        report.section("contracts", "FAIL", "invalid catalog")
        return []
    added, modified, deleted, unmapped = _changed_contracts(changed, documents, frozen_ids)
    by_id = {e["asset_id"]: e for e in entries if e["conclusion"] != "不收"}
    for asset_id in sorted(deleted):
        report.fail(
            "contracts", f"the patch deletes {asset_id}; extraction never removes contracts"
        )
    for asset_id in sorted(added):
        conclusion = by_id.get(asset_id, {}).get("conclusion")
        if conclusion != "全新":
            report.fail(
                "contracts",
                f"the patch adds {asset_id} but manifest.md marks it {conclusion or 'nowhere'};"
                " an added contract must be a 全新 row",
            )
    for asset_id in sorted(modified):
        entry = by_id.get(asset_id, {})
        conclusion = entry.get("conclusion")
        corrected = conclusion == "已有" and CORRECTION_NOTE in entry.get("note", "")
        if conclusion != "新 method" and not corrected:
            report.fail(
                "contracts",
                f"the patch changes {asset_id} but manifest.md marks it {conclusion or 'nowhere'};"
                f" a changed contract must be a 新 method row, or 已有 with 备注 {CORRECTION_NOTE}",
            )
    implemented = []
    source_only = []
    for entry in entries:
        asset_id, conclusion = entry["asset_id"], entry["conclusion"]
        if conclusion == "不收" or "domain" not in entry:
            continue  # 不收 has no contract; a row without a parsed domain was already reported
        if asset_id not in documents:
            report.fail(
                "contracts", f"{asset_id} ({conclusion}) has no contract in the patched catalog"
            )
            continue
        if conclusion == "已有":
            if asset_id not in frozen_ids:
                report.fail(
                    "contracts", f"{asset_id} is marked 已有 but is not in the frozen catalog"
                )
            if asset_id not in modified:
                continue  # unchanged and already in the library: nothing new to verify
        if conclusion == "全新" and asset_id in frozen_ids:
            report.fail(
                "contracts", f"{asset_id} is marked 全新 but already exists in the frozen catalog"
            )
        if conclusion == "新 method" and asset_id not in frozen_ids:
            report.fail(
                "contracts",
                f"{asset_id} is marked 新 method but the frozen catalog has no such family entry",
            )
        implemented.append(asset_id)
        api = documents[asset_id]["public_api"]["python"]
        module_domain = api.get("canonical_module", api["module"]).split(".")[1]
        if module_domain != asset_id.split(".")[1]:
            report.fail(
                "contracts", f"{asset_id}: ID domain differs from module domain {module_domain!r}"
            )
        for test in documents[asset_id]["verification"]["tests"]:
            if not (tree / test).is_file():
                report.fail("contracts", f"{asset_id}: verification test {test} does not exist")
        evidence = package / "evidence" / f"{asset_id}.md"
        if not evidence.is_file():
            report.fail("contracts", f"{asset_id}: evidence/{asset_id}.md is missing")
            continue
        table = _table(evidence.read_text(encoding="utf-8"), "用例")
        if table is None or not table[1]:
            report.fail("contracts", f"{asset_id}: evidence has no 用例 table rows")
            continue
        bases = set()
        for number, row in enumerate(table[1], start=1):
            if len(row) != 5:
                report.fail("contracts", f"{asset_id}: evidence row {number} needs 5 cells")
                continue
            _case, category, basis, origin, result = row
            if category not in EVIDENCE_CATEGORIES:
                report.fail(
                    "contracts",
                    f"{asset_id}: evidence row {number}: 类别 {category!r} not in {', '.join(EVIDENCE_CATEGORIES)}",
                )
            if basis not in EVIDENCE_BASES:
                report.fail(
                    "contracts",
                    f"{asset_id}: evidence row {number}: 依据 {basis!r} not in {', '.join(EVIDENCE_BASES)}",
                )
            if not origin:
                report.fail("contracts", f"{asset_id}: evidence row {number}: 依据出处 is empty")
            if result not in RESULT_STATES:
                report.fail(
                    "contracts",
                    f"{asset_id}: evidence row {number}: 结果 {result!r} not in {', '.join(RESULT_STATES)}",
                )
            bases.add(basis)
        if bases == {"来源输出"}:
            source_only.append(asset_id)
    if unmapped:
        report.section(
            "changed helpers",
            "PASS",
            f"{len(unmapped)} changed source files are no contract's module; only the full check"
            f" covers them: {', '.join(unmapped)}",
        )
    detail = f"{len(documents)} contracts in set, {len(implemented)} new or extended, {len(source_only)} with source-output evidence only"
    if source_only:
        detail += f" ({', '.join(source_only)})"
    report.section("contracts", "FAIL" if len(report.errors) > errors_before else "PASS", detail)
    return implemented


def run_full_check(tree: Path, report: Report) -> None:
    script = tree / "skills/development/scirel-acceptance/scripts/check_all.py"
    done = subprocess.run([sys.executable, str(script)], cwd=tree, capture_output=True, text=True)
    lines = (done.stdout + done.stderr).strip().splitlines()
    if done.returncode:
        # Name each failing step and the lines that say why, so a worker can act without rerunning.
        stripped = [line.strip() for line in lines]
        # Step names and causes first, then the individual failing tests.
        causes = [
            line
            for line in stripped
            if line.startswith(("FAIL ", "ERROR:")) or re.match(r"\w+Error: ", line)
        ]
        tests = [line for line in stripped if line.startswith(("FAILED tests", "ERROR tests"))]
        reasons = causes + tests
        for line in reasons[:25]:
            report.fail("full check", line)
        if len(reasons) > 25:
            report.fail(
                "full check",
                f"... {len(reasons) - 25} more lines; rerun check_all.py on the patched tree",
            )
    report.section(
        "full check", "FAIL" if done.returncode else "PASS", lines[-1] if lines else "no output"
    )


def run_mutation(tree: Path, asset_ids: list[str], report: Report) -> None:
    if not asset_ids:
        report.section("mutation", "PASS", "no new or extended contracts")
        return
    done = subprocess.run(
        [sys.executable, str(SCRIPTS / "mutation_check.py"), "--root", str(tree), *asset_ids],
        capture_output=True,
        text=True,
    )
    lines = (done.stdout + done.stderr).strip().splitlines()
    if done.returncode:
        for line in lines[:-1]:
            if not line.startswith("PASSED"):
                report.fail("mutation", line)
    report.section(
        "mutation", "FAIL" if done.returncode else "PASS", lines[-1] if lines else "no output"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("package", type=Path)
    parser.add_argument(
        "--repo", type=Path, default=ROOT, help="git repository that contains the frozen commit"
    )
    parser.add_argument(
        "--fast", action="store_true", help="skip the full check and mutation (exit 2, never 0)"
    )
    args = parser.parse_args()
    package, repo = args.package.resolve(), args.repo.resolve()
    report = Report()
    if check_structure(package, report):
        info = check_package_md(package, report)
        entries = check_manifest(package, report, info)
        check_disposition(package, report, entries)
        check_tickets(package, report)
        check_leaks(package, report)
        workdir = Path(tempfile.mkdtemp(prefix="scirel-package-"))
        try:
            tree, frozen, changed = (None, set(), [])
            if info.get("commit"):
                tree, frozen, changed = apply_patch(package, repo, info["commit"], workdir, report)
            if tree is not None:
                implemented = check_contracts(package, tree, frozen, entries, changed, report)
                if args.fast:
                    report.section("full check", "NOT_RUN", "--fast")
                    report.section("mutation", "NOT_RUN", "--fast")
                else:
                    run_full_check(tree, report)
                    run_mutation(tree, implemented, report)
        finally:
            if (workdir / "tree").exists():
                _git(["worktree", "remove", "--force", str(workdir / "tree")], repo)
            shutil.rmtree(workdir, ignore_errors=True)
    for name, state, detail in report.sections:
        print(f"{state:8} {name}: {detail}")
    for error in report.errors:
        print(f"ERROR    {error}")
    states = [state for _, state, _ in report.sections]
    passed = states.count("PASS")
    print(
        f"sections {len(states)}: passed {passed}, failed {states.count('FAIL')}, NOT_RUN {states.count('NOT_RUN')}"
    )
    if report.errors or "FAIL" in states:
        return 1
    return 2 if "NOT_RUN" in states else 0


if __name__ == "__main__":
    raise SystemExit(main())
