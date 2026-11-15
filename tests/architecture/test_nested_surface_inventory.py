"""Independent source expectations for nested modules and direct exports."""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _surface_inventory import SurfaceInventoryError, surface_counts  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts import validate_installed_wheel as validator  # noqa: E402


def _source(tmp_path, initializer):
    domain = tmp_path / "ordinary"
    nested = domain / "operators"
    nested.mkdir(parents=True)
    (domain / "__init__.py").write_text('__all__ = ["operators"]\n')
    (nested / "__init__.py").write_text(initializer)
    (nested / "kernel.py").write_text('__all__ = ["evaluate"]\ndef evaluate(): pass\n')
    return tmp_path


def test_static_inventory_counts_nested_modules_and_direct_values(tmp_path):
    root = _source(
        tmp_path,
        "from .kernel import evaluate\nconstant = 3\n"
        '__all__ = ["kernel", "evaluate", "constant"]\n',
    )
    assert surface_counts(root) == {
        "domain_count": 1,
        "export_count": 1,
        "nested_package_count": 1,
        "nested_module_count": 1,
        "nested_export_count": 3,
    }


def test_an_explicit_sibling_module_import_is_still_a_module(tmp_path):
    root = _source(tmp_path, 'from . import kernel\n__all__ = ["kernel"]\n')
    assert surface_counts(root)["nested_module_count"] == 1
    assert surface_counts(root)["nested_export_count"] == 1


def test_direct_classes_and_annotated_constants_need_no_sibling_module(tmp_path):
    root = _source(
        tmp_path,
        'class State: pass\nconstant: float = 3.0\n__all__ = ["State", "constant"]\n',
    )
    assert surface_counts(root)["nested_module_count"] == 0
    assert surface_counts(root)["nested_export_count"] == 2


def test_static_inventory_resolves_literal_lazy_function_binding(tmp_path):
    root = _source(
        tmp_path,
        '__all__ = ["evaluate"]\n_LAZY_EXPORTS = {"evaluate": ("kernel", "evaluate")}\n',
    )
    assert surface_counts(root)["nested_export_count"] == 1
    assert surface_counts(root)["nested_module_count"] == 0


@pytest.mark.parametrize(
    "initializer",
    [
        '__all__ = ["absent"]\n',
        '__all__ = ["evaluate"]\n_LAZY_EXPORTS = {"evaluate": ("absent", "evaluate")}\n',
        '__all__ = ["evaluate"]\n_LAZY_EXPORTS = {"evaluate": ("kernel", "absent")}\n',
        '__all__ = ["evaluate", "evaluate"]\n',
        '__all__ = list(("evaluate",))\n',
    ],
)
def test_static_inventory_refuses_missing_or_unreadable_bindings(tmp_path, initializer):
    with pytest.raises(SurfaceInventoryError):
        surface_counts(_source(tmp_path, initializer))


def test_runtime_surface_reaches_a_function_in_a_nonkinetic_subpackage(monkeypatch):
    from scirel.numerics import linalg

    monkeypatch.delattr(linalg, "compute_truncated_pseudoinverse", raising=False)
    monkeypatch.setitem(
        linalg._LAZY_EXPORTS,
        "compute_truncated_pseudoinverse",
        ("missing_scientific_module", "compute_truncated_pseudoinverse"),
    )
    details, errors = validator._run_public_surface()
    assert details["status"] == "FAIL"
    assert errors
    assert any(
        "scirel.numerics.linalg.compute_truncated_pseudoinverse" in failure
        for failure in details["failures"]
    ), "Every declared domain's nested exports must actually be resolved"
