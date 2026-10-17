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
