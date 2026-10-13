"""Use the maintained SciRel dependency baseline for every selected new build.

The source selection remains exact. A historical dependency requirement must
admit the maintained pin; otherwise requalify that implementation explicitly.
This helper neither changes frozen artifacts nor transfers their qualification.
"""
import hashlib
from pathlib import Path
import tomllib

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


BASELINE_PATH = Path(__file__).resolve().parents[1] / "pyproject.toml"


def baseline():
    with BASELINE_PATH.open("rb") as stream:
        return tomllib.load(stream)


def pin_dependencies(dependencies):
    pins = {canonicalize_name(Requirement(text).name): Requirement(text)
            for text in baseline()["project"]["dependencies"]}
    selected = []
    for text in dependencies:
        requested = Requirement(text)
        pin = pins.get(canonicalize_name(requested.name))
        if pin is None:
            raise ValueError(f"dependency is outside the scientific baseline: {requested.name}")
        constraints = list(pin.specifier)
        if len(constraints) != 1 or constraints[0].operator != "==":
            raise ValueError(f"scientific baseline dependency must be exactly pinned: {pin}")
        version = constraints[0].version
        if (requested.url or requested.extras or requested.marker
                or version not in requested.specifier):
            raise ValueError(f"dependency needs requalification against the scientific baseline: {text} -> {pin}")
        selected.append(str(pin))
    return selected


def python_requirement():
    return baseline()["project"]["requires-python"]


def build_requirements():
    return baseline()["build-system"]["requires"]


def baseline_receipt():
    """Bind generated package requirements to the exact maintained policy bytes."""
    policy = baseline()
    return {"schema": "scirel.scientific-runtime-baseline.v1",
            "pyproject_sha256": hashlib.sha256(BASELINE_PATH.read_bytes()).hexdigest(),
            "python": python_requirement(),
            "dependencies": policy["project"]["dependencies"],
            "build_requires": build_requirements()}
