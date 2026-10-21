"""Human-review import guard for held capabilities.

Held assets stay in the repository as review evidence but are not part of the
public capability surface.  The default package must not expose them; tests and
the human-review process may opt in with ``SCIREL_REVIEW_HOLD=1``.
"""
from __future__ import annotations

import os


def review_mode() -> bool:
    return os.environ.get("SCIREL_REVIEW_HOLD") == "1"


def require_review_import(module: str) -> None:
    """Fail a direct/public import unless the caller is the review harness."""
    if not review_mode():
        raise ImportError(
            f"{module} is withheld from public exposure for human review; "
            "set SCIREL_REVIEW_HOLD=1 only in the review harness"
        )


def require_review_call(symbol: str) -> None:
    """Fail a callable held behind review unless the review harness opted in."""
    if not review_mode():
        raise ImportError(
            f"{symbol} is withheld from public exposure for human review; "
            "set SCIREL_REVIEW_HOLD=1 only in the review harness"
        )
