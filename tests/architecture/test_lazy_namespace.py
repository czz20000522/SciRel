"""Check first-import behavior in fresh interpreters, independent of test order."""
from pathlib import Path
import json
import subprocess
import sys
import tomllib

# The expected names are read from the source tree with ``ast`` (no SciRel
# import), so each fresh interpreter compares its runtime ``__all__`` against
# the declaration that produced it instead of a pinned integer.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _surface_inventory import domain_exports  # noqa: E402


ROOT = Path(__file__).resolve().parents[2]
PROJECT_VERSION = tomllib.loads(
    (ROOT / "pyproject.toml").read_text(encoding="utf-8")
)["project"]["version"]
KINETIC_EXPORTS = json.dumps(list(domain_exports("kinetic")))
FIELD_EXPORTS = json.dumps(list(domain_exports("field")))
CLOSURES_EXPORTS = json.dumps(list(domain_exports("closures")))
EQUILIBRIUM_EXPORTS = json.dumps(list(domain_exports("equilibrium")))


def test_root_import_and_discovery_need_no_scientific_dependencies():
    result = subprocess.run(
        [sys.executable, '-I', '-S', '-c', '''
import sys
sys.path.insert(0, sys.argv[1])
import scirel
assert set(scirel.__all__) <= set(dir(scirel))
assert "__version__" in dir(scirel)
assert "_project_version" not in dir(scirel)
assert "_import_module" not in dir(scirel)
assert not hasattr(scirel, "not_a_scientific_api")
assert scirel.__version__ == sys.argv[2]
assert not any(n.startswith("scirel.") for n in sys.modules)
assert not any(n in sys.modules for n in ("numpy", "scipy", "matplotlib"))
# A source checkout resolves its version from the single pyproject source;
# installed-wheel metadata is only needed after the package is built.
assert "importlib.metadata" not in sys.modules
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


def test_root_namespace_discovers_every_public_domain_package():
    result = subprocess.run(
        [sys.executable, '-I', '-c', '''
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
assert not any(
    name.split(".", 1)[0] in ("numpy", "scipy", "matplotlib", "mpmath")
    for name in sys.modules
)
''', str(ROOT / 'src')], capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_kinetic_exports_are_lazy_and_preserve_canonical_identity():
    result = subprocess.run(
        [sys.executable, '-I', '-c', '''
import json
import sys

sys.path.insert(0, sys.argv[1])
import scirel.kinetic as kinetic

assert tuple(kinetic.__all__) == tuple(json.loads(sys.argv[2]))
assert not any(
    name.startswith("scirel.kinetic.")
    for name in sys.modules
    if name != "scirel.kinetic"
)
assert "evaluate_gpdf_small_k" in kinetic.__all__
assert "evaluate_gpdf_small_k" in dir(kinetic)
assert {"fluid_spectrum", "generalized_dispersion", "dispersion"} <= set(dir(kinetic))
assert not any(
    name.startswith("numpy") or name.startswith("scipy")
    for name in sys.modules
)
assert kinetic.generalized_dispersion.__name__ == "scirel.kinetic.generalized_dispersion"
assert kinetic.dispersion.__name__ == "scirel.kinetic.dispersion"

from scirel.kinetic import evaluate_gpdf_small_k
from scirel.kinetic.generalized_dispersion import evaluate_gpdf_small_k as direct

assert evaluate_gpdf_small_k is direct
assert kinetic.evaluate_gpdf_small_k is direct

namespace = {}
exec("from scirel.kinetic import *", namespace)
assert all(namespace[name] is getattr(kinetic, name) for name in kinetic.__all__)
''', str(ROOT / 'src'), KINETIC_EXPORTS], capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_fluid_wavevector_scan_defers_graph_dependencies_until_call():
    result = subprocess.run(
        [sys.executable, '-I', '-c', '''
import sys

sys.path.insert(0, sys.argv[1])
from scirel.kinetic import scan_fluid_wavevectors

assert callable(scan_fluid_wavevectors)
assert "scirel.kinetic.fluid_wavevector_scan" in sys.modules
assert not any(
    name in sys.modules
    for name in (
        "scirel.kinetic.fluid_dispersion_matrix",
        "scirel.kinetic.fluid_wavevector_eigensolve",
        "scirel.kinetic.gamma_lpole_coefficients",
        "scirel.kinetic.species_equilibrium_scales",
        "scirel.kinetic.z_pole_coefficients",
    )
)
''', str(ROOT / 'src')], capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_kinetic_wavevector_scan_defers_graph_dependencies_until_call():
    result = subprocess.run(
        [sys.executable, '-I', '-c', '''
import sys

sys.path.insert(0, sys.argv[1])
from scirel.kinetic import scan_kinetic_wavevectors

assert callable(scan_kinetic_wavevectors)
assert "scirel.kinetic.kinetic_wavevector_scan" in sys.modules
assert not any(
    name in sys.modules
    for name in (
        "scirel.kinetic.kinetic_wavevector_roots",
        "scirel.kinetic.kinetic_dispersion_ronnmark",
        "scirel.kinetic.ronnmark_r_function",
        "scirel.kinetic.species_equilibrium_scales",
    )
)
''', str(ROOT / 'src')], capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_kinetic_dispersion_relation_defers_graph_dependencies_until_call():
    result = subprocess.run(
        [sys.executable, '-I', '-c', '''
import sys

sys.path.insert(0, sys.argv[1])
from scirel.kinetic import evaluate_kinetic_dispersion_relation

assert callable(evaluate_kinetic_dispersion_relation)
assert "scirel.kinetic.kinetic_dispersion_relation" in sys.modules
assert not any(
    name in sys.modules
    for name in (
        "scirel.kinetic.kinetic_dispersion_ronnmark",
        "scirel.kinetic.ronnmark_r_function",
        "scirel.kinetic.kinetic_dispersion_sum_fluid",
        "scirel.kinetic.species_equilibrium_scales",
    )
)
''', str(ROOT / 'src')], capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_field_exports_are_lazy_and_preserve_compatibility_identity():
    result = subprocess.run(
        [sys.executable, '-I', '-c', '''
import json
import sys

sys.path.insert(0, sys.argv[1])
import scirel.field as field

assert tuple(field.__all__) == tuple(json.loads(sys.argv[2]))
assert not any(
    name.startswith("scirel.field.")
    for name in sys.modules
    if name != "scirel.field"
)
assert "poloidal_field_from_flux" in dir(field)
assert {"coil_green_geometry", "complete_elliptic_integrals_approx"} <= set(dir(field))

from scirel.field import poloidal_field_from_flux
from scirel.field.poloidal_field_from_flux import poloidal_field_from_flux as direct

assert poloidal_field_from_flux is direct
assert field.poloidal_field_from_flux is direct

namespace = {}
exec("from scirel.field import *", namespace)
assert all(namespace[name] is getattr(field, name) for name in field.__all__)
''', str(ROOT / 'src'), FIELD_EXPORTS], capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_closures_namespace_is_dependency_light_before_operator_access():
    result = subprocess.run(
        [sys.executable, '-I', '-S', '-c', '''
import json
import sys

sys.path.insert(0, sys.argv[1])
import scirel.closures as closures

assert tuple(closures.__all__) == tuple(json.loads(sys.argv[2]))
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
''', str(ROOT / 'src'), CLOSURES_EXPORTS], capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_closures_exports_are_lazy_and_preserve_compatibility_identity():
    result = subprocess.run(
        [sys.executable, '-I', '-c', '''
import json
import sys

sys.path.insert(0, sys.argv[1])
import scirel.closures as closures

assert tuple(closures.__all__) == tuple(json.loads(sys.argv[2]))
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
''', str(ROOT / 'src'), CLOSURES_EXPORTS], capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_equilibrium_namespace_is_dependency_light_and_preserves_missing_dependency_errors():
    result = subprocess.run(
        [sys.executable, '-I', '-S', '-c', '''
import json
import sys

sys.path.insert(0, sys.argv[1])
import scirel.equilibrium as equilibrium

assert tuple(equilibrium.__all__) == tuple(json.loads(sys.argv[2]))
assert all(name in dir(equilibrium) for name in equilibrium.__all__)
assert not any(
    name.startswith("scirel.equilibrium.")
    for name in sys.modules
)
assert "numpy" not in sys.modules
assert "scipy" not in sys.modules

try:
    equilibrium.compute_equilibrium
except ModuleNotFoundError as public_error:
    assert public_error.name == "numpy"
else:
    raise AssertionError("equilibrium operator unexpectedly imported without NumPy")

try:
    from scirel.equilibrium.isotropic_picard_step import pressure_flux_picard_step
except ModuleNotFoundError as direct_error:
    assert direct_error.name == "numpy"
else:
    raise AssertionError("direct child module unexpectedly imported without NumPy")
''', str(ROOT / 'src'), EQUILIBRIUM_EXPORTS], capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_equilibrium_exports_preserve_child_module_identity_and_from_star():
    result = subprocess.run(
        [sys.executable, '-I', '-c', '''
import sys

sys.path.insert(0, sys.argv[1])
import scirel.equilibrium as equilibrium

expected = {
    "pressure_flux_picard_step",
    "build_pressure_flux_state",
    "update_anisotropic_picard_flux",
    "compute_anisotropic_toroidal_current",
    "update_axisymmetric_picard_flux",
    "compute_anisotropic_force_balance",
    "solve_free_boundary_anisotropic_picard",
    "solve_isotropic_pressure_flux",
    "solve_reduced_hall_anisotropic_picard",
    "solve_kinetic_mirror_hall_equilibrium",
    "EquilibriumResult",
    "compute_equilibrium",
}
assert set(equilibrium.__all__) == expected
assert not any(
    name.startswith("scirel.equilibrium.")
    for name in sys.modules
    if name != "scirel.equilibrium"
)

from scirel.equilibrium import compute_equilibrium
from scirel.equilibrium.equilibrium_state import compute_equilibrium as direct
from scirel.equilibrium import equilibrium_state as child
from scirel.equilibrium import isotropic_pressure_flux as graph
from scirel.equilibrium.isotropic_pressure_flux import (
    solve_isotropic_pressure_flux as direct_graph,
)

assert compute_equilibrium is direct
assert equilibrium.compute_equilibrium is direct
assert child is sys.modules["scirel.equilibrium.equilibrium_state"]
assert graph is sys.modules["scirel.equilibrium.isotropic_pressure_flux"]
assert equilibrium.solve_isotropic_pressure_flux is direct_graph

namespace = {}
exec("from scirel.equilibrium import *", namespace)
assert all(namespace[name] is getattr(equilibrium, name) for name in equilibrium.__all__)
assert "equilibrium_state" not in namespace
''', str(ROOT / 'src')], capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
