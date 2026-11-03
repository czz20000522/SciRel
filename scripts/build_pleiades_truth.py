#!/usr/bin/env python3
"""Regenerate the external Pleiades simple-two-coil reference truth.

The generator imports a caller-supplied Pleiades checkout and writes a
candidate source truth.  It never vendors or copies Pleiades source;
``--source-root`` is a runtime input only.  ``--output`` is required so a
caller chooses an explicit candidate directory; the tracked domain fixture is
never a default or an implicit overwrite target.

Example::

    python scripts/build_pleiades_truth.py \
        --source-root /path/to/pleiades \
        --source-archive /path/to/pleiades-0161abb3.zip

The fixed source revision is the independent oracle recorded by the tracked
domain fixture under ``tests/fixtures/multi_coil_vacuum_field``.
"""
from __future__ import annotations

import argparse
import collections
import collections.abc
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np


SOURCE_COMMIT = "0161abb3e9a1d85143c650f068ec524d672fc9ab"
SOURCE_ARCHIVE_SHA256 = (
    "f86cfec618690e41a669d692ff195a775f756d2a654fc3e41d8175bf328381b3"
)
COMPATIBILITY_PATCH = (
    "pleiades/fields.py and current_sets.py: collections.Iterable -> "
    "collections.abc.Iterable (Python 3.14 import only)"
)
GRID = {"rmin": 0.0, "rmax": 0.8, "zmin": -0.4, "zmax": 0.4, "nr": 9, "nz": 9}
COILS = (
    {"r0": 0.45, "z0": -0.15, "nr": 2, "nz": 2, "dr": 0.04, "dz": 0.05, "current": 1000.0},
    {"r0": 0.45, "z0": 0.15, "nr": 2, "nz": 2, "dr": 0.04, "dz": 0.05, "current": -800.0},
)
ROOT = Path(__file__).resolve().parents[1]
FORMAL_FIXTURE = (
    ROOT / "tests" / "fixtures" / "multi_coil_vacuum_field"
    / "pleiades_simple_two_coil"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_head(source_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(source_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def _patch_collections() -> None:
    """Apply the documented Python 3.14 import-only compatibility patch."""
    for name in ("Iterable", "Mapping", "Sequence", "Callable", "MutableMapping"):
        if not hasattr(collections, name):
            setattr(collections, name, getattr(collections.abc, name))


def _load_pleiades(source_root: Path):
    if not (source_root / "pleiades").is_dir():
        raise SystemExit(f"source root does not contain pleiades/: {source_root}")
    sys.path.insert(0, str(source_root))
    _patch_collections()
    try:
        from pleiades.current_sets import RectangularCoil
        from pleiades.mesh import RectMesh
    except Exception as error:  # noqa: BLE001 - report the external-source failure
        raise SystemExit(f"cannot import Pleiades from {source_root}: {error!r}") from error
    return RectMesh, RectangularCoil


def build_arrays(source_root: Path) -> dict[str, np.ndarray]:
    RectMesh, RectangularCoil = _load_pleiades(source_root)
    mesh = RectMesh(**GRID)
    shape = mesh.shape
    fields = {
        "r_grid": np.asarray(mesh.R, dtype=float),
        "z_grid": np.asarray(mesh.Z, dtype=float),
        "psi_vac": np.zeros(shape, dtype=float),
        "b_r_vac": np.zeros(shape, dtype=float),
        "b_z_vac": np.zeros(shape, dtype=float),
    }
    for coil in COILS:
        source = RectangularCoil(
            r0=coil["r0"],
            z0=coil["z0"],
            nr=coil["nr"],
            nz=coil["nz"],
            dr=coil["dr"],
            dz=coil["dz"],
            current=coil["current"],
            mesh=mesh,
        )
        fields["psi_vac"] += np.asarray(source.psi()).reshape(shape)
        fields["b_r_vac"] += np.asarray(source.BR()).reshape(shape)
        fields["b_z_vac"] += np.asarray(source.BZ()).reshape(shape)
    if not all(np.isfinite(values).all() for values in fields.values()):
        raise SystemExit("Pleiades returned a nonfinite truth array")
    return fields


def write_truth(output: Path, fields: dict[str, np.ndarray], *, source_commit: str,
                source_archive_sha256: str) -> None:
    output.mkdir(parents=True, exist_ok=True)
    np.savez(output / "truth.npz", **fields)
    truth = {
        "source": "Pleiades",
        "source_commit": source_commit,
        "source_archive_sha256": source_archive_sha256,
        "compatibility_patch": COMPATIBILITY_PATCH,
        "grid": dict(GRID),
        "coils": [dict(coil) for coil in COILS],
        "arrays": {
            "psi_vac": "Wb/rad",
            "b_r_vac": "T",
            "b_z_vac": "T",
            "order": "[N_Z,N_R]",
        },
        "note": "Independent Pleiades source truth; SciRel is not used to generate this file.",
    }
    (output / "TRUTH.json").write_text(
        json.dumps(truth, indent=2) + "\n", encoding="utf-8"
    )


def check_existing(output: Path, fields: dict[str, np.ndarray]) -> None:
    arrays = np.load(output / "truth.npz")
    for key, value in fields.items():
        if key not in arrays:
            raise SystemExit(f"existing truth is missing {key}")
        if arrays[key].shape != value.shape or not np.array_equal(arrays[key], value):
            raise SystemExit(f"existing truth differs for {key}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path,
                        help="external Pleiades checkout or source tree (not vendored)")
    parser.add_argument("--source-archive", type=Path, default=None,
                        help="optional Pleiades source archive used to verify the recorded SHA-256")
    parser.add_argument("--source-archive-sha256", default=None,
                        help="explicit archive SHA-256 when the archive is unavailable")
    parser.add_argument("--source-commit", default=None,
                        help="explicit source commit when the source tree has no .git metadata")
    parser.add_argument("--output", required=True, type=Path,
                        help="explicit candidate output directory (never the formal fixture)")
    parser.add_argument("--allow-other-commit", action="store_true",
                        help="allow a source revision other than the recorded oracle revision")
    parser.add_argument("--allow-other-archive", action="store_true",
                        help="allow an archive SHA-256 other than the recorded oracle archive")
    parser.add_argument("--check", action="store_true",
                        help="regenerate in memory and compare with an existing artifact; do not write")
    args = parser.parse_args(argv)

    source_root = args.source_root.resolve()
    actual_commit = _git_head(source_root)
    if actual_commit is not None and args.source_commit is not None and actual_commit != args.source_commit:
        raise SystemExit(f"git HEAD {actual_commit} differs from --source-commit {args.source_commit}")
    source_commit = actual_commit or args.source_commit
    if source_commit is None:
        raise SystemExit("cannot determine source commit; provide --source-commit")
    if source_commit != SOURCE_COMMIT and not args.allow_other_commit:
        raise SystemExit(
            f"source commit {source_commit} is not the recorded oracle revision {SOURCE_COMMIT}; "
            "pass --allow-other-commit only for a deliberate new oracle"
        )

    if args.source_archive is not None:
        archive_sha = _sha256(args.source_archive)
    elif args.source_archive_sha256 is not None:
        archive_sha = args.source_archive_sha256
    elif source_commit == SOURCE_COMMIT:
        archive_sha = SOURCE_ARCHIVE_SHA256
    else:
        raise SystemExit("provide --source-archive or --source-archive-sha256 for a new revision")
    if archive_sha != SOURCE_ARCHIVE_SHA256 and not args.allow_other_archive:
        raise SystemExit(
            f"archive SHA-256 {archive_sha} is not the recorded oracle archive {SOURCE_ARCHIVE_SHA256}; "
            "pass --allow-other-archive only for a deliberate new oracle"
        )

    fields = build_arrays(source_root)
    output = args.output.resolve()
    if output == FORMAL_FIXTURE.resolve() and not args.check:
        raise SystemExit(
            "refusing to write the formal tracked fixture; choose an explicit candidate directory"
        )
    if args.check:
        check_existing(output, fields)
        print(f"Pleiades truth matches existing artifact: {output}")
        return 0
    write_truth(output, fields, source_commit=source_commit, source_archive_sha256=archive_sha)
    print(f"wrote Pleiades truth to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
