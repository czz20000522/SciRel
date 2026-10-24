"""Scientific Relations Library, organized into scientific domain subpackages.

Use domain APIs such as ``scirel.field.solve_multi_coil_vacuum_field``.
Importing ``scirel`` alone does not load scientific backends.
"""

from importlib import import_module as _import_module
import os as _os


def _project_version():
    # Source checkouts read the single version source directly; installed
    # wheels read their own dist-info metadata. No version is duplicated here.
    project = _os.path.abspath(
        _os.path.join(_os.path.dirname(__file__), "..", "..", "pyproject.toml")
    )
    if _os.path.isfile(project):
        try:
            import tomllib

            with open(project, "rb") as stream:
                return str(tomllib.load(stream)["project"]["version"])
        except (OSError, KeyError, TypeError, ValueError):
            pass
    try:
        from importlib.metadata import PackageNotFoundError, version

        return version("scirel")
    except PackageNotFoundError:
        return "0+unknown"


__version__ = _project_version()

__all__ = [
    "closures",
    "collisions",
    "configurations",
    "diagnostics",
    "dielectric",
    "electromagnetism",
    "equilibrium",
    "field",
    "fusion",
    "fvm",
    "geometry",
    "inference",
    "io",
    "kinetic",
    "neoclassical",
    "numerics",
    "physics",
    "plasma",
    "source",
]


def __getattr__(name):
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = _import_module("." + name, __name__)
    globals()[name] = value
    return value


def __dir__():
    # Keep discovery focused on the package contract.  Implementation helpers
    # such as ``_project_version`` remain available to the module itself but
    # are not part of ``dir(scirel)`` for callers using introspection.
    return sorted(set(__all__) | {"__version__"})
