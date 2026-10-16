"""Scientific Relations Library, organized into scientific domain subpackages.

Use domain APIs such as ``scirel.field.solve_multi_coil_vacuum_field``.
Importing ``scirel`` alone does not load scientific backends.
"""

from importlib import import_module as _import_module
from importlib.metadata import PackageNotFoundError as _PackageNotFoundError
from importlib.metadata import version as _installed_version
from pathlib import Path as _Path
import tomllib as _tomllib


def _project_version():
    # Source checkouts read the single version source directly; installed
    # wheels read their own dist-info metadata. No version is duplicated here.
    project = _Path(__file__).resolve().parents[2] / "pyproject.toml"
    if project.is_file():
        try:
            return str(_tomllib.loads(project.read_text(encoding="utf-8"))["project"]["version"])
        except (OSError, KeyError, TypeError, _tomllib.TOMLDecodeError):
            pass
    try:
        return _installed_version("scirel")
    except _PackageNotFoundError:
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
    return sorted(set(globals()) | set(__all__))
