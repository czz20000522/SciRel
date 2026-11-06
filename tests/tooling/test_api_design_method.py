"""The API method's scripts catch what they claim, on a package made for the test, and stay general."""

import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills/development/api-design-method"
SCRIPTS = SKILL / "scripts"

GOOD = '''
__all__ = ["area"]


def area(radius):
    """Compute a circle's area.

    Parameters
    ----------
    radius : float
        Radius [m].

    Returns
    -------
    float
        Area [m^2].

    Raises
    ------
    ValueError
        If the radius is negative.

    See Also
    --------
    sum : Not related; here to fill the section.

    Examples
    --------
    >>> round(area(1.0), 3)
    3.142
    """
    if radius < 0:
        raise ValueError("radius must be nonnegative")
    return 3.14159265 * radius**2
'''

BAD = '''
__all__ = ["bad", "other"]


def bad(values, ignored, flag=False, table=[], **options):
    """Do something.

    Parameters
    ----------
    values : float
        No unit stated here.
    gone : float
        Not a parameter.

    Examples
    --------
    >>> 1 + 1
    3
    """
    try:
        values = values or 0.5
    except Exception:
        pass
    return values


def other():
    return 1
'''


def _run(script, *args, cwd=None):
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPTS / script), *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def _package(tmp_path, body, name="demo_pkg"):
    package = tmp_path / name
    package.mkdir()
    (package / "__init__.py").write_text(body)
    return name


def test_inventory_flags_interface_problems_and_compares_a_documented_list(tmp_path):
    name = _package(tmp_path, BAD)
    documented = tmp_path / "documented.txt"
    documented.write_text(f"{name}.bad\n{name}.removed\n")
    done = _run(
        "api_inventory.py",
        name,
        "--src",
        str(tmp_path),
        "--documented",
        str(documented),
        "--name-pattern",
        "[a-z]{4,}",
        "--json",
    )
    assert done.returncode == 1, done.stderr
    report = json.loads(done.stdout)
    bad = next(row for row in report["public"] if row["name"].endswith(".bad"))
    assert {"var-keyword", "mutable-default:table", "positional-flag:flag"} <= set(bad["flags"])
    problems = "\n".join(report["problems"])
    assert "name outside the pattern" in problems
    assert f"public but undocumented: {name}.other" in problems
    assert f"documented but not public: {name}.removed" in problems


def test_scan_finds_silent_patterns_and_the_baseline_only_lets_known_hits_pass(tmp_path):
    source = tmp_path / "src"
    source.mkdir()
    (source / "code.py").write_text(BAD)
    done = _run("scan_hazards.py", str(source), "--json")
    assert done.returncode == 1
    rules = {hit["rule"] for hit in json.loads(done.stdout)}
    assert {
        "broad-except",
        "swallowed-exception",
        "mutable-default",
        "var-keyword",
        "bare-default-none-or",
        "unused-parameter",
    } <= rules
    baseline = tmp_path / "baseline.json"
    assert _run("scan_hazards.py", str(source), "--write-baseline", str(baseline)).returncode == 0
    assert _run("scan_hazards.py", str(source), "--baseline", str(baseline)).returncode == 0
    (source / "new.py").write_text("def f(a=[]):\n    return a\n")
    again = _run("scan_hazards.py", str(source), "--baseline", str(baseline))
    assert again.returncode == 1
    assert "new.py" in again.stdout and "code.py" not in again.stdout


def test_docs_check_passes_a_complete_docstring(tmp_path):
    name = _package(tmp_path, GOOD)
    done = _run("check_docs_sync.py", name, "--src", str(tmp_path), "--unit-regex", r"\[[^\]]+\]")
    assert done.returncode == 0, done.stdout


def test_docs_check_does_not_require_a_returns_section_for_a_class(tmp_path):
    name = _package(
        tmp_path,
        '''
__all__ = ["Config"]


class Config:
    """Represent one reviewed configuration value.

    Parameters
    ----------
    value : int
        Stored configuration value [count].

    Raises
    ------
    TypeError
        If value is not an integer.

    See Also
    --------
    dict : Related built-in mapping.

    Examples
    --------
    >>> Config(3).value
    3
    """

    def __init__(self, value):
        if not isinstance(value, int):
            raise TypeError("value must be an integer")
        self.value = value
''',
    )
    done = _run("check_docs_sync.py", name, "--src", str(tmp_path))
    assert done.returncode == 0, done.stdout


def test_docs_check_reports_each_kind_of_disagreement(tmp_path):
    name = _package(tmp_path, BAD)
    done = _run("check_docs_sync.py", name, "--src", str(tmp_path), "--unit-regex", r"\[[^\]]+\]")
    assert done.returncode == 1
    for message in (
        "missing section Returns",
        "parameter ignored not documented",
        "documents unknown parameter gone",
        "states no unit",
        "Examples fail as doctests",
        f"{name}.other: no docstring",
    ):
        assert message in done.stdout, message


def test_docs_check_scope_is_a_ratchet(tmp_path):
    name = _package(
        tmp_path,
        BAD.replace('"bad", "other"', '"bad", "other", "fine"')
        + GOOD.replace("area", "fine").split('__all__ = ["fine"]')[1],
    )
    scope = tmp_path / "scope.txt"
    scope.write_text(f"{name}.fine\n")
    assert (
        _run("check_docs_sync.py", name, "--src", str(tmp_path), "--scope", str(scope)).returncode
        == 0
    )


def test_method_is_written_for_any_library():
    project = re.compile(r"scirel|tokamak|mirror|bootstrap|kappa|G-EQDSK|contract_sync", re.I)
    hits = []
    for path in SKILL.rglob("*"):
        if path.suffix in (".md", ".py"):
            hits += [
                f"{path.name}: {m.group(0)}"
                for m in project.finditer(path.read_text(encoding="utf-8"))
            ]
    assert hits == []


def test_method_links_resolve():
    for path in SKILL.rglob("*.md"):
        for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", path.read_text(encoding="utf-8")):
            assert (path.parent / target).exists(), target
