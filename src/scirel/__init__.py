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
                metadata = tomllib.load(stream)["project"]
            # A vendored copy can sit under another project's pyproject.toml.
            if metadata["name"] == "scirel":
                return str(metadata["version"])
        except (OSError, KeyError, TypeError, ValueError):
            pass
    try:
        from importlib.metadata import PackageNotFoundError, version

        return version("scirel")
    except PackageNotFoundError:
        return "0+unknown"


__version__ = _project_version()


class ApplicabilityWarning(UserWarning):
    """A result was returned outside the relation's declared applicability range.

    A relation that raises this warning still returns a value: the input left the range in
    which the relation is validated (for example above or below the temperatures its fit was
    compared against), so the result is low- or high-biased rather than undefined. Raise it
    only for that case; ``ValueError`` and ``TypeError`` keep the cases where no meaningful
    value exists at all, and ``FloatingPointError`` the ones where the value is unrepresentable.

    Callers who require validated inputs can turn it into an error::

        warnings.simplefilter("error", scirel.ApplicabilityWarning)

    The message of every warning of this class names the quantity, its declared range, the
    effect of the offending value on the result, and the contract ID that states the limit.

    Defined here, in the root module, rather than in a private submodule: importing ``scirel``
    must load no submodule and keep working when only this file is vendored, which two
    architecture tests pin.
    """


# The root namespace lists domain subpackages only: ``from scirel import *`` must keep
# yielding modules, which the architecture tests pin. ``ApplicabilityWarning`` is exported as a
# plain attribute (``scirel.ApplicabilityWarning`` and ``from scirel import ApplicabilityWarning``)
# and appears in ``dir()``, without joining this domain list.
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
    "mirror",
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
    return sorted(set(__all__) | {"__version__", "ApplicabilityWarning"})
