"""Validate a SciRel wheel with a completely offline dependency wheelhouse.

This command consumes an already-built SciRel wheel and a directory of
dependency wheels.  It creates a temporary clean virtual environment, installs
the wheel using only the supplied wheelhouse, and then delegates the installed
package checks to :mod:`validate_installed_wheel`.

The command never builds a wheel and never changes release metadata.  Its
receipt is intentionally separate from the historical ``dev9`` Linux receipt:
it records whether dependency resolution was actually completed with
``--no-index`` and ``--only-binary=:all:``.

Without ``--source-revision`` the receipt is a standalone technical receipt.
Pass the exact lowercase Git commit when preparing a future candidate that
will bind this receipt into ``release/CURRENT.json``; the release validator
then checks that binding instead of trusting the wheel filename alone.

Typical Linux amd64 / CPython 3.14 invocation::

    python -I scripts/validate_offline_wheelhouse.py \
        --expected-platform linux-x86_64-cp314 \
        --wheel /artifacts/scirel-0.1.0.dev9-py3-none-any.whl \
        --wheelhouse /artifacts/linux-x86_64-cp314-wheelhouse \
        --output offline-wheelhouse-validation.json

The wheelhouse must contain wheels for the SciRel runtime dependencies and all
of their transitive dependencies selected by pip.  Source archives are not
used: ``--only-binary=:all:`` makes a missing binary dependency fail closed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any, Sequence


SCHEMA = "scirel.offline-wheelhouse-validation.v1"
DEFAULT_EXPECTED_PYTHON = "3.14"
VALIDATOR = Path(__file__).resolve().with_name("validate_installed_wheel.py")
_SOURCE_REVISION = re.compile(r"[0-9a-f]{40}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_regular_file(path: Path, *, label: str) -> None:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{label} must be a regular file: {path}")


def _wheelhouse_inventory(path: Path) -> list[dict[str, Any]]:
    """Return deterministic identity rows for every wheel in ``path``.

    A wheelhouse may contain auxiliary files used by a local mirror, but only
    regular ``.whl`` files participate in this acceptance.  Symlinked wheels
    are rejected so the receipt binds bytes at a stable path rather than a
    mutable link target.
    """

    path = path.resolve()
    if not path.is_dir() or path.is_symlink():
        raise ValueError(f"wheelhouse must be a regular directory: {path}")
    rows: list[dict[str, Any]] = []
    for wheel in sorted(path.glob("*.whl"), key=lambda value: value.name):
        _require_regular_file(wheel, label="wheelhouse member")
        rows.append(
            {
                "filename": wheel.name,
                "sha256": _sha256(wheel),
                "bytes": wheel.stat().st_size,
            }
        )
    if not rows:
        raise ValueError(f"wheelhouse contains no wheel files: {path}")
    return rows


def _pip_install_command(python: Path, wheel: Path, wheelhouse: Path) -> list[str]:
    """Build the fail-closed pip command used for offline installation."""

    return [
        str(python),
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-cache-dir",
        "--no-index",
        "--only-binary=:all:",
        "--find-links",
        str(wheelhouse),
        str(wheel),
    ]


def _pip_install_extra_command(
    python: Path, extra: str, wheelhouse: Path
) -> list[str]:
    """Build the offline command that resolves one installed package extra."""

    extra = extra.strip().lower()
    if not extra:
        raise ValueError("extra name must not be empty")
    return [
        str(python),
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-cache-dir",
        "--no-index",
        "--only-binary=:all:",
        "--find-links",
        str(wheelhouse),
        f"scirel[{extra}]",
    ]


def _run(
    command: Sequence[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=cwd,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def _trim(value: str | None, limit: int = 8000) -> str:
    return (value or "").strip()[-limit:]


def _venv_python(venv: Path) -> Path:
    if os.name == "nt":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def _clean_environment() -> dict[str, str]:
    """Remove import-path and pip-index overrides from child processes."""

    env = dict(os.environ)
    for key in (
        "PYTHONPATH",
        "PIP_INDEX_URL",
        "PIP_EXTRA_INDEX_URL",
        "PIP_FIND_LINKS",
        "PIP_NO_INDEX",
        "PIP_TRUSTED_HOST",
    ):
        env.pop(key, None)
    return env


def _normalise_source_revision(value: str | None) -> str | None:
    if value is None:
        return None
    if _SOURCE_REVISION.fullmatch(value) is None:
        raise ValueError("source revision must be a 40-character lowercase Git commit")
    return value


def validate_offline_wheelhouse(
    *,
    wheel_path: Path,
    wheelhouse_path: Path,
    expected_platform: str | None = None,
    expected_python: str = DEFAULT_EXPECTED_PYTHON,
    source_revision: str | None = None,
    validator_path: Path = VALIDATOR,
    extras: Sequence[str] = (),
) -> dict[str, Any]:
    """Install and validate one wheel with no network or source fallback."""

    wheel = wheel_path.resolve()
    wheelhouse = wheelhouse_path.resolve()
    validator = validator_path.resolve()
    source_revision = _normalise_source_revision(source_revision)
    _require_regular_file(wheel, label="SciRel wheel")
    _require_regular_file(validator, label="installed-wheel validator")
    inventory = _wheelhouse_inventory(wheelhouse)
    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "FAIL",
        "source_revision": source_revision,
        "artifact": {
            "filename": wheel.name,
            "sha256": _sha256(wheel),
            "bytes": wheel.stat().st_size,
        },
        "wheelhouse": {
            "path": str(wheelhouse),
            "wheel_count": len(inventory),
            "wheels": inventory,
        },
        "execution": {
            "network_resolution": False,
            "pip_install": "not_run",
            "commands": [],
        },
        "validation": {},
        "extras": {},
        "errors": [],
    }

    environment = _clean_environment()
    with tempfile.TemporaryDirectory(prefix="scirel-offline-wheelhouse-") as temporary:
        workspace = Path(temporary)
        venv = workspace / "venv"
        create_command = [sys.executable, "-m", "venv", str(venv)]
        receipt["execution"]["commands"].append(create_command)
        created = _run(create_command, env=environment)
        receipt["execution"]["venv"] = {
            "returncode": created.returncode,
            "stdout": _trim(created.stdout),
            "stderr": _trim(created.stderr),
        }
        if created.returncode:
            receipt["errors"].append(
                f"clean virtual environment creation failed with exit code {created.returncode}"
            )
            return receipt

        python = _venv_python(venv)
        install_command = _pip_install_command(python, wheel, wheelhouse)
        receipt["execution"]["commands"].append(install_command)
        installed = _run(install_command, env=environment)
        receipt["execution"]["pip_install"] = {
            "status": "PASS" if installed.returncode == 0 else "FAIL",
            "returncode": installed.returncode,
            "stdout": _trim(installed.stdout),
            "stderr": _trim(installed.stderr),
        }
        if installed.returncode:
            receipt["errors"].append(
                "offline pip installation failed; dependency resolution did not complete "
                f"with exit code {installed.returncode}"
            )
            return receipt

        normalised_extras: list[str] = []
        seen_extras: set[str] = set()
        for raw_extra in extras:
            extra = raw_extra.strip().lower()
            if not extra or extra in seen_extras:
                continue
            seen_extras.add(extra)
            normalised_extras.append(extra)
            extra_install = _pip_install_extra_command(python, extra, wheelhouse)
            receipt["execution"]["commands"].append(extra_install)
            extra_result = _run(extra_install, env=environment)
            receipt["extras"][extra] = {
                "install": {
                    "status": "PASS" if extra_result.returncode == 0 else "FAIL",
                    "returncode": extra_result.returncode,
                    "stdout": _trim(extra_result.stdout),
                    "stderr": _trim(extra_result.stderr),
                }
            }
            if extra_result.returncode:
                receipt["errors"].append(
                    f"offline installation of extra {extra!r} failed with exit code "
                    f"{extra_result.returncode}"
                )

        validation_path = workspace / "installed-wheel-validation.json"
        validate_command = [
            str(python),
            "-I",
            str(validator),
            "--expected-python",
            expected_python,
            "--wheel",
            str(wheel),
            "--output",
            str(validation_path),
        ]
        if expected_platform:
            validate_command[3:3] = ["--expected-platform", expected_platform]
        for extra in normalised_extras:
            validate_command.extend(["--extra", extra])
        receipt["execution"]["commands"].append(validate_command)
        validated = _run(validate_command, env=environment)
        if validation_path.is_file():
            try:
                receipt["validation"] = json.loads(validation_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                receipt["errors"].append(f"installed-wheel validation receipt is unreadable: {error}")
        else:
            receipt["errors"].append("installed-wheel validator produced no receipt")
        if validated.returncode:
            receipt["errors"].append(
                f"installed-wheel validation failed with exit code {validated.returncode}"
            )
        if receipt.get("validation", {}).get("status") != "PASS":
            receipt["errors"].append("installed-wheel validation receipt is not PASS")

    receipt["status"] = "PASS" if not receipt["errors"] else "FAIL"
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--wheelhouse", type=Path, required=True)
    parser.add_argument("--expected-platform", help="for example linux-x86_64-cp314")
    parser.add_argument(
        "--source-revision",
        help="optional exact lowercase Git commit; required when binding this receipt to CURRENT",
    )
    parser.add_argument(
        "--expected-python",
        default=DEFAULT_EXPECTED_PYTHON,
        help=f"expected CPython major.minor line (default: {DEFAULT_EXPECTED_PYTHON})",
    )
    parser.add_argument(
        "--extra",
        action="append",
        default=[],
        dest="extras",
        metavar="NAME",
        help="install and validate an optional extra; repeat for multiple extras",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = validate_offline_wheelhouse(
            wheel_path=args.wheel,
            wheelhouse_path=args.wheelhouse,
            expected_platform=args.expected_platform,
            expected_python=args.expected_python,
            source_revision=args.source_revision,
            extras=tuple(args.extras),
        )
    except Exception as error:  # keep command failures machine-readable
        receipt = {
            "schema": SCHEMA,
            "status": "FAIL",
            "errors": [f"validation setup failed: {type(error).__name__}: {error}"],
        }
    rendered = json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True)
    print(rendered)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if receipt.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
