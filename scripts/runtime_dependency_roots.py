"""Locate declared wheel dependencies and pytest for the development install check."""

from __future__ import annotations

import argparse
from email.parser import Parser
from importlib import metadata
import json
from pathlib import Path
from zipfile import ZipFile

from packaging.requirements import Requirement


def runtime_dependency_roots(wheel: Path) -> list[str]:
    with ZipFile(wheel) as archive:
        members = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        if len(members) != 1:
            raise ValueError("wheel must have exactly one distribution metadata file")
        document = Parser().parsestr(archive.read(members[0]).decode("utf-8"))
    requirements = [Requirement("pytest"), *(
        Requirement(value) for value in document.get_all("Requires-Dist", [])
    )]
    roots = []
    for requirement in requirements:
        if requirement.marker is not None and not requirement.marker.evaluate({"extra": ""}):
            continue
        distribution = metadata.distribution(requirement.name)
        if distribution.version not in requirement.specifier:
            raise ValueError(f"installed dependency does not satisfy {requirement}")
        root = str(Path(distribution.locate_file("")).resolve())
        if root not in roots:
            roots.append(root)
    return roots


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    arguments = parser.parse_args()
    print(json.dumps(runtime_dependency_roots(arguments.wheel)))


if __name__ == "__main__":
    main()
