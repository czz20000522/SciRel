"""Check first-import behavior in fresh interpreters, independent of test order."""
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_root_import_and_discovery_need_no_scientific_dependencies():
    result = subprocess.run(
        [sys.executable, '-I', '-S', '-c', '''
import sys
sys.path.insert(0, sys.argv[1])
import scirel
assert set(scirel.__all__) <= set(dir(scirel))
assert not hasattr(scirel, "not_a_scientific_api")
assert not any(n.startswith("scirel.") for n in sys.modules)
assert not any(n in sys.modules for n in ("numpy", "scipy", "matplotlib"))
try:
    scirel.field
except ModuleNotFoundError as error:
    assert error.name == "numpy", str(error)
else:
    raise AssertionError("missing runtime dependencies must not be hidden")
''', str(ROOT / 'src')], capture_output=True, text=True,
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
