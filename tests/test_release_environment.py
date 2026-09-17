from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
HELPERS = ROOT / "scripts" / "check_helpers.ps1"
CHECK = ROOT / "scripts" / "check.ps1"


def _resolve(environment: Path, platform: str):
    command = (
        f". '{HELPERS}'; "
        f"Resolve-SciRelVenvPython -EnvironmentPath '{environment}' -Platform {platform}"
    )
    return subprocess.run(
        ["pwsh", "-NoProfile", "-Command", command],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def test_release_python_path_is_resolved_for_windows_and_posix(tmp_path):
    windows = tmp_path / "windows"
    windows_python = windows / "Scripts" / "python.exe"
    windows_python.parent.mkdir(parents=True)
    windows_python.touch()

    posix = tmp_path / "posix"
    posix_python = posix / "bin" / "python"
    posix_python.parent.mkdir(parents=True)
    posix_python.touch()

    windows_result = _resolve(windows, "Windows")
    posix_result = _resolve(posix, "Posix")

    assert windows_result.returncode == 0, windows_result.stderr
    assert Path(windows_result.stdout.strip()) == windows_python
    assert posix_result.returncode == 0, posix_result.stderr
    assert Path(posix_result.stdout.strip()) == posix_python


def test_missing_release_python_fails_with_candidate_path(tmp_path):
    result = _resolve(tmp_path / "missing", "Posix")

    assert result.returncode != 0
    assert "Virtual environment Python was not created at" in result.stderr
    assert "bin" in result.stderr and "python" in result.stderr


def test_release_environment_does_not_inherit_system_packages():
    script = CHECK.read_text(encoding="utf-8")

    assert "--system-site-packages" not in script
    assert "--no-index --no-deps --force-reinstall" in script
    assert 'import numpy, scipy, scirel' in script
