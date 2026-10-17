"""Regression checks for dependency-light scientific domain namespaces."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def _run(source: str) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-c", source],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def test_heavy_domain_namespaces_do_not_import_numeric_backends() -> None:
    result = _run(
        """
import sys
import scirel.collisions
import scirel.configurations
import scirel.electromagnetism
assert "numpy" not in sys.modules
assert "scipy" not in sys.modules
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_all_domain_namespaces_are_dependency_light_until_an_export_is_used() -> None:
    result = _run(
        """
import sys
import scirel.diagnostics
import scirel.dielectric
import scirel.fvm
import scirel.fusion
import scirel.inference
import scirel.io
import scirel.neoclassical
import scirel.physics
import scirel.plasma
import scirel.source
assert "numpy" not in sys.modules
assert "scipy" not in sys.modules
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_lazy_exports_preserve_identity_for_the_remaining_domains() -> None:
    result = _run(
        """
from scirel.dielectric import cold_plasma_dielectric_tensor
from scirel.dielectric.cold_plasma_tensor import cold_plasma_dielectric_tensor as direct_dielectric
from scirel.physics import calculate_log_lambda_ee
from scirel.physics.coulomb_logs import calculate_log_lambda_ee as direct_logs
from scirel.source import gaussian_profile
from scirel.source.gaussian import gaussian_profile as direct_gaussian
assert cold_plasma_dielectric_tensor is direct_dielectric
assert calculate_log_lambda_ee is direct_logs
assert gaussian_profile is direct_gaussian
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_collision_lazy_exports_keep_public_identity() -> None:
    result = _run(
        """
import scirel.collisions as package
from scirel.collisions import normalized_momentum
from scirel.collisions.momentum_scales import normalized_momentum as direct
assert package.normalized_momentum is direct
assert normalized_momentum is direct
assert all(name in dir(package) for name in package.__all__)
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_configuration_and_electromagnetism_lazy_exports_keep_public_identity() -> None:
    result = _run(
        """
from scirel.configurations import BRB
from scirel.configurations.brb import BRB as direct_brb
from scirel.electromagnetism import compute_greens
from scirel.electromagnetism.greens import compute_greens as direct_greens
assert BRB is direct_brb
assert compute_greens is direct_greens
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_field_child_modules_are_discoverable_and_lazy() -> None:
    result = _run(
        """
import sys
import scirel.field as field

assert {"coil_green_geometry", "complete_elliptic_integrals_approx"} <= set(dir(field))
assert not any(name.startswith("scirel.field.") for name in sys.modules)

child = field.coil_green_geometry
assert child.__name__ == "scirel.field.coil_green_geometry"
assert field.coil_green_geometry is child
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_domain_dirs_expose_only_public_contract_and_legal_lazy_names() -> None:
    result = _run(
        """
import importlib

import scirel


def check_namespace(package):
    public = set(package.__all__)
    lazy_modules = getattr(package, "_LAZY_MODULES", ())
    if hasattr(lazy_modules, "keys"):
        lazy_modules = set(lazy_modules)
    else:
        lazy_modules = set(lazy_modules)
    compatibility = set(getattr(package, "_COMPAT_EXPORTS", ()))
    names = set(dir(package))
    allowed = public | lazy_modules | compatibility
    assert public <= names, (package.__name__, sorted(public - names))
    assert compatibility <= names, (package.__name__, sorted(compatibility - names))
    assert names <= allowed, (package.__name__, sorted(names - allowed))
    assert not any(name.startswith("_") for name in names), package.__name__


for domain_name in scirel.__all__:
    check_namespace(importlib.import_module(f"scirel.{domain_name}"))

check_namespace(importlib.import_module("scirel.kinetic.pdrk"))
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr
