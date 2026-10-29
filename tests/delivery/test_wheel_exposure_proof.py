"""Final-wheel identity, integrity and public/held distribution boundaries."""
from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import stat
import sys
import warnings
from zipfile import ZipFile, ZipInfo

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts import check_wheel_exposure as checker  # noqa: E402

DIST_INFO = "scirel-0.0.1.dist-info"
RECORD = DIST_INFO + "/RECORD"


@pytest.fixture
def intake(tmp_path: Path):
    public = tmp_path / "public"
    held = tmp_path / "held"
    public.mkdir()
    held.mkdir()
    for asset, module, symbol in (
        ("public", "scirel.domain.core", "evaluate"),
        ("reexport", "scirel.domain.facade", "reexported"),
    ):
        (public / f"{asset}.json").write_text(json.dumps({
            "asset_id": f"scirel.{asset}",
            "public_api": {"python": {
                "module": module, "symbol": symbol,
                "canonical_module": "scirel.domain", "canonical_symbol": symbol,
            }},
        }), encoding="utf-8")
    (held / "held.json").write_text(json.dumps({
        "asset_id": "scirel.held",
        "public_api": {"python": {
            "module": "scirel.domain.held", "symbol": "held_solver",
            "canonical_module": "scirel.domain", "canonical_symbol": "held_solver",
        }},
    }), encoding="utf-8")
    project = tmp_path / "pyproject.toml"
    project.write_text('[project]\nname="scirel"\nversion="0.0.1"\n'
                       'requires-python=">=3.11"\ndependencies=["numpy==2.5.4"]\n',
                       encoding="utf-8")
    files = {
        "scirel/__init__.py": b'raise RuntimeError("the inspector must not import the wheel")\n',
        "scirel/domain/__init__.py": (
            b'from importlib import import_module as _import_module\n'
            b'_LAZY_EXPORTS = {"evaluate": ("core", "evaluate"), '
            b'"reexported": ("facade", "reexported")}\n'
            b'def __getattr__(name):\n'
            b'    if name in _LAZY_EXPORTS:\n'
            b'        module_name, attribute_name = _LAZY_EXPORTS[name]\n'
            b'        module = _import_module(f".{module_name}", __name__)\n'
            b'        value = getattr(module, attribute_name)\n'
            b'        globals()[name] = value\n'
            b'        return value\n'
            b'    raise AttributeError(name)\n'
        ),
        "scirel/domain/core.py": b'def evaluate():\n    return 2\n',
        "scirel/domain/facade.py": b'from .core import evaluate as reexported\n',
        DIST_INFO + "/METADATA": (
            b'Metadata-Version: 2.4\nName: scirel\nVersion: 0.0.1\n'
            b'Requires-Python: >=3.11\nRequires-Dist: numpy==2.5.4\n\n'
        ),
        DIST_INFO + "/WHEEL": b'Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n',
        DIST_INFO + "/licenses/licenses/NOTICE": b'Attribution bytes\n',
    }

    def write_wheel(members=None, *, record_rows=None, suffix="final"):
        members = dict(files if members is None else members)
        rows = []
        for name, data in members.items():
            digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
            rows.append([name, "sha256=" + digest, str(len(data))])
        rows.append([RECORD, "", ""])
        stream = io.StringIO(newline="")
        csv.writer(stream, lineterminator="\n").writerows(rows if record_rows is None else record_rows)
        members[RECORD] = stream.getvalue().encode()
        wheel = tmp_path / f"scirel-0.0.1-{suffix}-py3-none-any.whl"
        with ZipFile(wheel, "w") as archive:
            for name, data in members.items():
                info = ZipInfo(name)
                # Keep deliberately unsafe archive names intact on Windows,
                # where ZipInfo normally replaces backslashes before writing.
                info.filename = name
                archive.writestr(info, data)
        return wheel

    def inspect(wheel, **kwargs):
        return checker.inspect_wheel(wheel, public_catalog=public, held_catalog=held, project_file=project, **kwargs)

    return files, write_wheel, inspect


def test_inspects_exact_bytes_without_importing_the_wheel(intake) -> None:
    files, write, inspect = intake
    wheel = write()
    report = inspect(wheel)

    assert report["status"] == "PASS", report["errors"]
    assert report["sha256"] == hashlib.sha256(wheel.read_bytes()).hexdigest()
    assert report["size_bytes"] == wheel.stat().st_size
    assert report["record"]["verified_files"] == len(files)
    assert report["record"]["entries"] == len(files) + 1
    assert report["public_api"]["asset_count"] == 2
    assert report["public_api"]["bindings_checked"] == 4
    assert report["held_asset_count"] == 1
    assert report["metadata"]["dependency_names"] == ["numpy"]
    assert report["pure_wheel"]["tags"] == ["py3-none-any"]
    assert report["runtime_status"] == "NOT_RUN"
    assert report["scientific_validation_status"] == "NOT_RUN"
    assert report["source_binding"]["status"] == "NOT_RUN"
    assert report["licenses"] == [{
        "path": DIST_INFO + "/licenses/licenses/NOTICE",
        "sha256": hashlib.sha256(b"Attribution bytes\n").hexdigest(),
        "size_bytes": len(b"Attribution bytes\n"),
    }]


def test_optional_source_binding_rejects_old_module_bytes_without_rebuilding_wheel(intake, tmp_path) -> None:
    files, write, inspect = intake
    source_root = tmp_path / "src"
    for name, data in files.items():
        if name.startswith("scirel/"):
            path = source_root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    excluded = source_root / "scirel/_framework_compositions/__init__.py"
    excluded.parent.mkdir()
    excluded.write_bytes(b"# Explicitly excluded by package policy.\n")
    with (tmp_path / "pyproject.toml").open("a") as project:
        project.write('\n[tool.setuptools.packages.find]\n'
                      'include=["scirel", "scirel.*"]\n'
                      'exclude=["scirel._framework_compositions", "scirel._framework_compositions.*"]\n')
    wheel = write()
    matched = inspect(wheel, source_root=source_root)
    assert matched["status"] == "PASS", matched["errors"]
    assert matched["source_binding"]["source_content_sha256"] == matched["source_binding"]["wheel_content_sha256"]
    (source_root / "scirel/domain/core.py").write_bytes(b"def evaluate():\n    return 3\n")

    report = inspect(wheel, source_root=source_root)

    assert report["status"] == "FAIL"
    assert report["record"]["status"] == "PASS"
    assert report["source_binding"]["changed_members"] == ["scirel/domain/core.py"]


@pytest.mark.parametrize("private_member", ["_private_dependency.py", "_data/example.in"])
def test_source_binding_catches_omitted_private_dependency_or_declared_data(intake, tmp_path, private_member) -> None:
    files, write, inspect = intake
    source_root = tmp_path / "src"
    for name, data in files.items():
        if name.startswith("scirel/"):
            path = source_root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    missing = "scirel/domain/" + private_member
    path = source_root / missing
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"# Private runtime dependency, not a public contract entry.\n")
    with (tmp_path / "pyproject.toml").open("a") as project:
        project.write('\n[tool.setuptools.package-data]\n"scirel.domain"=["_data/*"]\n')
    wheel = write()

    report = inspect(wheel, source_root=source_root)

    assert report["record"]["status"] == "PASS"
    assert report["source_binding"]["status"] == "FAIL"
    assert report["source_binding"]["missing_members"] == [missing]


def test_detects_modified_content_against_original_record(intake) -> None:
    _, write, inspect = intake
    original = write()
    with ZipFile(original) as archive:
        members = {name: archive.read(name) for name in archive.namelist()}
    members["scirel/domain/core.py"] = b'def evaluate():\n    return 3\n'
    tampered = original.with_name("tampered.whl")
    with ZipFile(tampered, "w") as archive:
        for name, data in members.items():
            archive.writestr(name, data)

    report = inspect(tampered)

    assert report["status"] == "FAIL"
    assert any("core.py: hash mismatch" in error for error in report["record"]["errors"])
    assert report["sha256"] != inspect(original)["sha256"]


def test_detects_members_omitted_from_record(intake) -> None:
    _, write, inspect = intake
    wheel = write()
    with ZipFile(wheel, "a") as archive:
        archive.writestr("scirel/extra.dat", b"unbound")

    report = inspect(wheel)

    assert report["status"] == "FAIL"
    assert any("missing from RECORD" in error for error in report["record"]["errors"])


@pytest.mark.parametrize("corruption", ["size", "empty-hash", "weak-hash", "self-hash", "missing-self"])
def test_rejects_record_entries_that_cannot_bind_all_member_bytes(intake, corruption) -> None:
    _, write, inspect = intake
    wheel = write()
    with ZipFile(wheel) as archive:
        rows = list(csv.reader(io.StringIO(archive.read(RECORD).decode())))
    if corruption == "size":
        rows[0][2] = str(int(rows[0][2]) + 1)
    elif corruption == "empty-hash":
        rows[0][1] = ""
    elif corruption == "weak-hash":
        rows[0][1] = "md5=anything"
    elif corruption == "self-hash":
        rows[-1][1] = "sha256=anything"
    else:
        rows.pop()

    report = inspect(write(record_rows=rows))

    assert report["status"] == "FAIL"
    assert report["record"]["status"] == "FAIL"


def test_rejects_duplicate_archive_and_record_members(intake) -> None:
    _, write, inspect = intake
    wheel = write()
    with ZipFile(wheel) as archive:
        rows = list(csv.reader(io.StringIO(archive.read(RECORD).decode())))
    duplicate_record = write(record_rows=rows + [rows[0]], suffix="duplicate-record")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with ZipFile(wheel, "a") as archive:
            archive.writestr("scirel/domain/core.py", b'def evaluate():\n    return 99\n')

    assert inspect(wheel)["archive"]["duplicate_members"] == ["scirel/domain/core.py"]
    report = inspect(duplicate_record)
    assert report["status"] == "FAIL"
    assert any("duplicate RECORD paths" in error for error in report["record"]["errors"])


@pytest.mark.parametrize("unsafe", [
    "../outside", "/outside", "C:/outside", "C:outside", "scirel\\outside",
    "scirel/./outside", "scirel//outside", "scirel/outside\x00hidden", "scirel//",
])
def test_rejects_archive_path_escapes(intake, unsafe) -> None:
    files, write, inspect = intake
    report = inspect(write({**files, unsafe: b"unsafe"}))
    assert report["status"] == "FAIL"
    assert report["archive"]["unsafe_members"] == [unsafe]


def test_rejects_symlinks(intake) -> None:
    _, write, inspect = intake
    wheel = write()
    link = ZipInfo("scirel/link")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    with ZipFile(wheel, "a") as archive:
        archive.writestr(link, "../../outside")

    report = inspect(wheel)
    assert report["status"] == "FAIL"
    assert report["archive"]["symlink_members"] == ["scirel/link"]


@pytest.mark.parametrize("field,value", [("Requires-Python", ">=3.12"), ("Requires-Dist", "numpy==0.0.1"), ("Version", "0.0.2")])
def test_rejects_metadata_outside_the_candidate_contract(intake, field, value) -> None:
    files, write, inspect = intake
    lines = files[DIST_INFO + "/METADATA"].decode().splitlines()
    modified = "\n".join(f"{field}: {value}" if line.startswith(field + ":") else line for line in lines).encode()
    report = inspect(write({**files, DIST_INFO + "/METADATA": modified}))
    assert report["status"] == "FAIL"
    assert report["metadata"]["status"] == "FAIL"


@pytest.mark.parametrize("member,content", [
    ("scirel/domain/held.py", b'def held_solver():\n    return 1\n'),
    ("scirel/domain/core.py", b'def evaluate():\n    return 2\n\nheld_solver = evaluate\n'),
    ("scirel/domain/__init__.py", b'from .core import evaluate, evaluate as reexported\n__all__ = ["held_solver"]\n'),
    ("catalog/review/candidates/held.json", b'{}'),
])
def test_rejects_held_code_symbols_or_candidate_material(intake, member, content) -> None:
    files, write, inspect = intake
    report = inspect(write({**files, member: content}))
    assert report["status"] == "FAIL"
    assert (report["held_modules_present"] or report["held_symbol_references_present"] or report["candidate_paths_present"])


def test_requires_both_public_module_and_resolvable_symbol(intake) -> None:
    files, write, inspect = intake
    missing = dict(files)
    del missing["scirel/domain/core.py"]
    missing_report = inspect(write(missing, suffix="missing"))
    assert missing_report["status"] == "FAIL"
    assert missing_report["public_api"]["missing_modules"] == ["scirel.domain.core"]
    unresolved_report = inspect(write({**files, "scirel/domain/core.py": b'def wrong():\n    return 2\n'}))
    assert unresolved_report["status"] == "FAIL"
    assert len(unresolved_report["public_api"]["unresolved_symbols"]) == 4


@pytest.mark.parametrize("getter", [b"", b'def __getattr__(name):\n    raise AttributeError(name)\n'])
def test_lazy_export_table_requires_supported_attribute_forwarding(intake, getter) -> None:
    files, write, inspect = intake
    initializer = files["scirel/domain/__init__.py"].split(b'def __getattr__')[0] + getter
    report = inspect(write({**files, "scirel/domain/__init__.py": initializer}))
    assert report["status"] == "FAIL"
    assert len(report["public_api"]["unresolved_symbols"]) == 2


@pytest.mark.parametrize("root", ["purelib", "platlib"])
def test_relocated_package_code_cannot_bypass_held_module_exclusion(intake, root) -> None:
    files, write, inspect = intake
    member = f"scirel-0.0.1.data/{root}/scirel/domain/held.py"
    report = inspect(write({**files, member: b'implementation_present = True\n'}))
    assert report["status"] == "FAIL"
    assert report["pure_wheel"]["relocated_package_members"] == [member]


def test_malformed_lazy_all_literal_is_a_structured_failure(intake) -> None:
    files, write, inspect = intake
    initializer = files["scirel/domain/__init__.py"]
    table = initializer.index(b'_LAZY_EXPORTS = ')
    getter = initializer.index(b'def __getattr__')
    initializer = (initializer[:table] + b'__all__ = 1\n'
                   b'_LAZY_EXPORTS = {name: ("core", name) for name in __all__}\n' + initializer[getter:])
    report = inspect(write({**files, "scirel/domain/__init__.py": initializer}))
    assert report["status"] == "FAIL"
    assert len(report["public_api"]["unresolved_symbols"]) == 2


@pytest.mark.parametrize("member,content", [
    (DIST_INFO + "/WHEEL", b'Root-Is-Purelib: false\nTag: cp314-cp314-linux_x86_64\n'),
    ("scirel/hidden.pyc", b'compiled code cannot be checked as source'),
])
def test_pure_wheel_flags_do_not_hide_uninspectable_code(intake, member, content) -> None:
    files, write, inspect = intake
    report = inspect(write({**files, member: content}))
    assert report["status"] == "FAIL"
    assert report["pure_wheel"]["status"] == "FAIL"


def test_cli_requires_an_explicit_final_wheel() -> None:
    with pytest.raises(SystemExit) as error:
        checker.main([])
    assert error.value.code == 2
