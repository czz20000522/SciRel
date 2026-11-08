"""Rules a new maintainer relies on, checked rather than promised."""

import json
from pathlib import Path
import re
import subprocess
import tomllib

import pytest

ROOT = Path(__file__).resolve().parents[2]
REQUIRED = (
    "README.md",
    "AGENTS.md",
    "ARCHITECTURE.md",
    "RULES.md",
    "CONTRIBUTING.md",
    "catalog/README.md",
    "catalog/AUDIT.md",
    "examples/README.md",
    "examples/PLAN.md",
)
TEXT_SUFFIXES = {".md", ".py", ".json", ".toml", ".yaml", ".yml", ".txt", ".rst", ".js", ".html"}
PRIVATE_PATH = re.compile(r"/Users/[a-z]|/home/[a-z]+/|[A-Z]:[/\\]software|/srv/scirel")
PRIVATE_DEPENDENCY = re.compile(r"\bNotion\b|Mac checkout|\bE drive\b")
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s#]+)(?:#[^)]*)?\)")
THIS_FILE = "tests/architecture/test_repository_skeleton.py"
PATTERN_FILES = {
    THIS_FILE,
    "skills/development/scirel-acceptance/scripts/precommit_check.py",
    "tests/tooling/test_precommit_check.py",
}


def tracked() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    return [ROOT / item for item in out.split("\0") if item and (ROOT / item).is_file()]


def texts():
    for path in tracked():
        if path.suffix in TEXT_SUFFIXES and path.relative_to(ROOT).as_posix() not in PATTERN_FILES:
            yield path, path.read_text(encoding="utf-8", errors="replace")


def _strip_code(text: str) -> str:
    return re.sub(r"`[^`\n]*`", "", re.sub(r"^```.*?^```[ \t]*$", "", text, flags=re.M | re.S))


@pytest.mark.parametrize("name", REQUIRED)
def test_handover_documents_are_tracked(name):
    assert ROOT / name in tracked(), name


def test_no_private_machine_paths_in_the_tree():
    hits = [
        f"{p.relative_to(ROOT)}: {m.group(0)}"
        for p, text in texts()
        for m in [PRIVATE_PATH.search(text)]
        if m
    ]
    assert hits == []


def test_no_dependency_on_private_records():
    hits = [str(p.relative_to(ROOT)) for p, text in texts() if PRIVATE_DEPENDENCY.search(text)]
    assert hits == []


def test_markdown_relative_links_resolve():
    broken = []
    for path, text in texts():
        if path.suffix != ".md" or "negative-demo" in path.as_posix():
            continue
        for target in LINK.findall(_strip_code(text)):
            if not re.match(r"[a-z]+:", target) and not (path.parent / target).exists():
                broken.append(f"{path.relative_to(ROOT)} -> {target}")
    assert broken == []


def test_tests_and_tools_do_not_read_old_git_objects():
    pattern = re.compile(r"git'?\"?,\s*'?\"?show'?\"?.{0,20}[0-9a-f]{40}")
    hits = [
        str(p.relative_to(ROOT))
        for p, text in texts()
        if p.suffix == ".py" and pattern.search(text)
    ]
    assert hits == []


# 文档里不许手写目录规模：规模由生成物给出，写进散文就会随树漂移。
CATALOG_SIZE = re.compile(
    r"\b\d{3} (admitted|public|contracts|assets|exposed|held)\b|共 \d{3} (份|个)合同"
)


def test_catalog_size_is_not_hand_written_into_documents():
    hits = [
        str(p.relative_to(ROOT))
        for p, text in texts()
        if p.suffix == ".md" and CATALOG_SIZE.search(text)
    ]
    assert hits == []


def test_catalog_size_guard_catches_the_wording_that_escaped_it():
    """回归：`256 exposed contracts` 曾因数字后紧跟 exposed 而绕过守卫。

    `exposed` 和 `held` 都是这类句子里的常见词；漏掉任意一个，手写规模
    就会换个词继续留在文档里。
    """
    for escaped in (
        "all 256 exposed contracts",
        "300 held contracts under `catalog/review/`",
        "261 admitted assets",
        "共 300 份合同",
    ):
        assert CATALOG_SIZE.search(escaped), escaped


def test_python_floor_is_consistent_with_the_pinned_dependencies():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["requires-python"] == ">=3.12"
    assert not any("3.11" in item for item in project["classifiers"])
    assert f"`{project['requires-python']}`" in (ROOT / "CONTRIBUTING.md").read_text(
        encoding="utf-8"
    )


def test_plotting_stays_out_of_the_runtime_dependencies():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert not any("matplotlib" in item for item in project["dependencies"])
    assert not list((ROOT / "src").rglob("*.png"))


def test_review_contract_code_is_outside_the_installed_package():
    for path in sorted((ROOT / "catalog/review/examples").glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        module = document["public_api"]["python"]["module"].split(".")
        assert not (ROOT / "src").joinpath(*module).with_suffix(".py").exists(), path.stem


def test_usage_directory_holds_exactly_the_delivered_skills():
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    source = (ROOT / "scripts/build_pure_delivery.py").read_text(encoding="utf-8")
    raw_names = re.search(r"SKILL_NAMES = \((.*?)\)", source).group(1)
    delivered = {name.strip().strip("\"'") for name in raw_names.split(",") if name.strip()}
    present = {p.name for p in (ROOT / "skills/development/usage").iterdir() if p.is_dir()}
    assert present == delivered - {""}


def test_each_role_names_an_entry_skill_that_exists():
    text = (ROOT / "skills/README.md").read_text(encoding="utf-8")
    for role in ("Supplier", "Merger", "Consumer"):
        assert f"**{role}**" in text
    for target in re.findall(r"\]\(([^)]*SKILL\.md)\)", text):
        assert (ROOT / "skills" / target).is_file(), target
