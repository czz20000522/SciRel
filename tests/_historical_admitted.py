"""Read the archived dev15 code bound to the legacy admission ledger."""

from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
HISTORICAL_COMMIT = "4f610fd49cf0e84b0dd60fcbffe4bc4a738b36fa"
HISTORICAL_VERSION = "0.1.0.dev15"


def historical_file(relative: Path | str) -> bytes:
    path = Path(relative).as_posix()
    return subprocess.run(
        ["git", "show", f"{HISTORICAL_COMMIT}:{path}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
