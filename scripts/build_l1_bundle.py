"""Build a canonical UTF-8 SciRel L1 bundle from a directory or ZIP."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scirel_workflow.l1_bundle import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
