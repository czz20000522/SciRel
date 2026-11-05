"""Small helpers for optional runtime dependencies.

Optional dependencies belong at the capability boundary that uses them.  The
helper in this module keeps a missing package distinguishable from a failure
inside an installed package and gives callers the extra needed to enable the
capability.
"""

from __future__ import annotations

from importlib import import_module
from types import ModuleType


def import_optional_module(
    module_name: str,
    *,
    extra: str,
    feature: str,
) -> ModuleType:
    """Import an optional module with an actionable extra hint.

    A dependency failure raised *by* an installed optional package is
    propagated unchanged.  Only a missing module in the optional package's
    own import tree is converted into the SciRel capability error so a broken
    transitive install is not misreported as a missing extra.
    """

    try:
        return import_module(module_name)
    except ModuleNotFoundError as error:
        root = module_name.split(".", 1)[0]
        missing = error.name or ""
        if missing == root or missing.startswith(root + "."):
            raise ModuleNotFoundError(
                f"{feature} requires the optional dependency {root!r}; "
                f"install it with `pip install scirel[{extra}]`.",
                name=root,
            ) from error
        raise


__all__ = ["import_optional_module"]
