"""Check first-import behavior in fresh interpreters, independent of test order."""
from pathlib import Path
import subprocess
import sys
import tomllib


ROOT = Path(__file__).resolve().parents[1]
PROJECT_VERSION = tomllib.loads(
    (ROOT / "pyproject.toml").read_text(encoding="utf-8")
)["project"]["version"]


def test_root_import_and_discovery_need_no_scientific_dependencies():
    result = subprocess.run(
        [sys.executable, '-I', '-S', '-c', '''
import sys
sys.path.insert(0, sys.argv[1])
import scirel
assert set(scirel.__all__) <= set(dir(scirel))
assert not hasattr(scirel, "not_a_scientific_api")
assert scirel.__version__ == sys.argv[2]
assert not any(n.startswith("scirel.") for n in sys.modules)
assert not any(n in sys.modules for n in ("numpy", "scipy", "matplotlib"))
# Domain discovery itself is dependency-light; the scientific child
# modules still raise their normal missing-dependency error when used.
scirel.field
assert "scirel.field" in sys.modules
assert not any(n in sys.modules for n in ("numpy", "scipy", "matplotlib"))
''', str(ROOT / 'src'), PROJECT_VERSION], capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_scientific_functions_are_exposed_only_within_their_domain():
    result = subprocess.run(
        [sys.executable, '-I', '-c', '''
import sys
sys.path.insert(0, sys.argv[1])
import scirel
from scirel import field
from scirel.field.poloidal_field_from_flux import poloidal_field_from_flux as direct
assert field.poloidal_field_from_flux is direct
assert not hasattr(scirel, "poloidal_field_from_flux")
assert "poloidal_field_from_flux" not in dir(scirel)
try:
    from scirel import poloidal_field_from_flux
except ImportError:
    pass
else:
    raise AssertionError("scientific functions belong in their domain subpackage")
assert "scirel.kinetic" not in sys.modules
assert "scirel.inference" not in sys.modules
assert "matplotlib" not in sys.modules
''', str(ROOT / 'src')], capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_geometry_core_imports_without_matplotlib_and_plotting_fails_at_boundary():
    result = subprocess.run(
        [sys.executable, '-c', '''
import importlib.abc
import sys

class BlockMatplotlib(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "matplotlib" or fullname.startswith("matplotlib."):
            raise ModuleNotFoundError("blocked optional dependency", name=fullname)
        return None

sys.meta_path.insert(0, BlockMatplotlib())
sys.path.insert(0, sys.argv[1])
import scirel.geometry as geometry
assert not any(
    name.startswith("scirel.geometry.")
    for name in sys.modules
)
assert "numpy" not in sys.modules
assert "scipy" not in sys.modules
assert "matplotlib" not in sys.modules
assert callable(geometry.sample_rectilinear_field)
try:
    geometry.scale_patches([], 2)
except ModuleNotFoundError as error:
    assert "require Matplotlib" in str(error)
else:
    raise AssertionError("plotting helper unexpectedly ran without Matplotlib")
''', str(ROOT / 'src')], capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_root_namespace_discovers_every_public_domain_package():
    result = subprocess.run(
        [sys.executable, '-c', '''
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
import scirel

expected = sorted(
    p.name for p in (Path(sys.argv[1]) / "scirel").iterdir()
    if p.is_dir() and not p.name.startswith("_") and (p / "__init__.py").is_file()
)
assert sorted(scirel.__all__) == expected
namespace = {}
exec("from scirel import *", namespace)
assert all(name in namespace for name in expected)
assert all(getattr(scirel, name).__name__ == f"scirel.{name}" for name in expected)
''', str(ROOT / 'src')], capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_kinetic_exports_are_lazy_and_preserve_compatibility_identity():
    result = subprocess.run(
        [sys.executable, '-I', '-c', '''
import sys

sys.path.insert(0, sys.argv[1])
import scirel.kinetic as kinetic

assert len(kinetic.__all__) == 91
assert not any(
    name.startswith("scirel.kinetic.")
    for name in sys.modules
    if name != "scirel.kinetic"
)
assert "evaluate_gpdf_small_k" in dir(kinetic)

from scirel.kinetic import evaluate_gpdf_small_k
from scirel.kinetic.generalized_dispersion import evaluate_gpdf_small_k as direct

assert evaluate_gpdf_small_k is direct
assert kinetic.evaluate_gpdf_small_k is direct

namespace = {}
exec("from scirel.kinetic import *", namespace)
assert all(namespace[name] is getattr(kinetic, name) for name in kinetic.__all__)
''', str(ROOT / 'src')], capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_field_exports_are_lazy_and_preserve_compatibility_identity():
    result = subprocess.run(
        [sys.executable, '-I', '-c', '''
import sys

sys.path.insert(0, sys.argv[1])
import scirel.field as field

assert len(field.__all__) == 14
assert not any(
    name.startswith("scirel.field.")
    for name in sys.modules
    if name != "scirel.field"
)
assert "poloidal_field_from_flux" in dir(field)

from scirel.field import poloidal_field_from_flux
from scirel.field.poloidal_field_from_flux import poloidal_field_from_flux as direct

assert poloidal_field_from_flux is direct
assert field.poloidal_field_from_flux is direct

namespace = {}
exec("from scirel.field import *", namespace)
assert all(namespace[name] is getattr(field, name) for name in field.__all__)
''', str(ROOT / 'src')], capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_closures_namespace_is_dependency_light_before_operator_access():
    result = subprocess.run(
        [sys.executable, '-I', '-S', '-c', '''
import sys

sys.path.insert(0, sys.argv[1])
import scirel.closures as closures

assert len(closures.__all__) == 8
assert not any(
    name.startswith("scirel.closures.")
    for name in sys.modules
    if name != "scirel.closures"
)
assert "numpy" not in sys.modules
assert "scipy" not in sys.modules
assert "evaluate_tabulated_pressure" in dir(closures)

try:
    closures.evaluate_tabulated_pressure
except ModuleNotFoundError:
    pass
else:
    raise AssertionError("operator unexpectedly imported without scientific dependencies")
''', str(ROOT / 'src')], capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_closures_exports_are_lazy_and_preserve_compatibility_identity():
    result = subprocess.run(
        [sys.executable, '-I', '-c', '''
import sys

sys.path.insert(0, sys.argv[1])
import scirel.closures as closures

assert len(closures.__all__) == 8
assert not any(
    name.startswith("scirel.closures.")
    for name in sys.modules
    if name != "scirel.closures"
)

from scirel.closures import close_hall_two_fluid_pressure
from scirel.closures.hall_two_fluid_pressure import close_hall_two_fluid_pressure as direct

assert close_hall_two_fluid_pressure is direct
assert closures.close_hall_two_fluid_pressure is direct
assert closures.hall_two_fluid_pressure is sys.modules["scirel.closures.hall_two_fluid_pressure"]

namespace = {}
exec("from scirel.closures import *", namespace)
assert all(namespace[name] is getattr(closures, name) for name in closures.__all__)
''', str(ROOT / 'src')], capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
