"""Create a new, byte-bound FINAL from payload and non-derived metadata.

No payload code is executed. Existing paths are never overwritten; an incomplete
new output is retained on failure and reported for inspection.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_admission as admission


def _new_output(output: Path, inputs: list[Path], errors: list[str]) -> None:
    admission.check_ancestors(output, errors)
    if output.exists() or output.is_symlink():
        errors.append(f"output already exists; refusing overwrite: {output}")
    if not output.parent.is_dir():
        errors.append(f"output parent directory must already exist: {output.parent}")
    for source in inputs:
        if output.resolve().is_relative_to(source.resolve()):
            errors.append(f"output must be outside input: {source}")


def prepare(payload: Path, metadata: Path, output: Path, path_map: Path | None = None) -> dict:
    payload, metadata, output = Path(payload), Path(metadata), Path(output)
    path_map = Path(path_map) if path_map is not None else None
    report = {
        "directory": str(output),
        "status": "FAIL",
        "errors": [],
        "checks": {},
        "output_created": False,
        "scientific_acceptance": "NOT_ASSESSED",
    }
    errors = report["errors"]
    try:
        inputs = [payload, metadata] + ([path_map] if path_map is not None else [])
        _new_output(output, inputs, errors)
        for source in inputs:
            admission.check_ancestors(source, errors)
        if errors:
            return report
        if (
            not payload.is_dir()
            or not metadata.is_file()
            or (path_map is not None and not path_map.is_file())
        ):
            report["status"] = "NOT_RUN"
            errors.append("required payload directory or metadata/path-map file is missing")
            return report
        files, stored = admission.inspect_tree(payload, errors)
        if any(name.casefold() in {c.casefold() for c in admission.CONTROLS} for name in stored):
            errors.append("payload root must not contain any of the four admission controls")
        supplied = admission.read_json(metadata)
        if not isinstance(supplied, dict):
            errors.append("metadata must be a JSON object")
            return report
        if admission.DERIVED_KEYS & supplied.keys():
            errors.append(
                f"metadata must not supply derived keys: {sorted(admission.DERIVED_KEYS & supplied.keys())}"
            )
        final = dict(supplied)
        final.update(
            schema="scirel.project-final",
            files="FILES.json",
            path_map="PATH_MAP.json",
            root_binding=admission.ROOT_BINDING,
            payload_files=len(files) + 2,
            payload_bytes=1,
        )
        admission._check_final(final, errors)
        mapping = admission.read_json(path_map) if path_map is not None else {}
        members = set(files) | {"FINAL.json", "PATH_MAP.json"}
        admission.check_path_map(mapping, members, stored, errors)
        if errors:
            return report
        admission.check_references(final, members, errors)
        if errors:
            return report
        # Catch non-encodable metadata before creating the new directory.
        admission.json_bytes(final)
        mapping_bytes = admission.json_bytes(mapping) if mapping else b"{}\n"
        # Snapshot before creating output. Recheck copied bytes to detect an input
        # modified while packaging; never silently freeze a different payload.
        snapshot = {
            name: {"bytes": p.stat().st_size, "sha256": admission._sha(p)}
            for name, p in files.items()
        }
        output.mkdir(exist_ok=False)
        report["output_created"] = True
        for name in sorted(stored):
            if name not in files:
                (output / name).mkdir(parents=True, exist_ok=True)
        for name, source in files.items():
            target = output / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            if (
                target.stat().st_size != snapshot[name]["bytes"]
                or admission._sha(target) != snapshot[name]["sha256"]
            ):
                raise ValueError(f"payload changed during copying: {name}")
        (output / "PATH_MAP.json").write_bytes(mapping_bytes)
        other_bytes = sum(item["bytes"] for item in snapshot.values()) + len(mapping_bytes)
        for _ in range(32):
            data = admission.json_bytes(final)
            total = other_bytes + len(data)
            if final["payload_bytes"] == total:
                break
            final["payload_bytes"] = total
        else:
            raise ValueError("FINAL payload_bytes fixed point did not converge")
        (output / "FINAL.json").write_bytes(data)
        entries = []
        for name in sorted(members):
            target = output / name
            entries.append(
                {"path": name, "bytes": target.stat().st_size, "sha256": admission._sha(target)}
            )
        (output / "FILES.json").write_bytes(
            admission.json_bytes({"schema": "scirel.final-files", "files": entries})
        )
        validated = admission.validate(output, emit_root=True)
        report.update(validated)
        report["output_created"] = True
        if report["status"] != "PASS":
            report["retained_output"] = str(output)
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        errors.append(f"cannot prepare admission: {type(exc).__name__}: {exc}")
    if report["output_created"] and report["status"] != "PASS":
        report["retained_output"] = str(output)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--path-map", type=Path)
    args = parser.parse_args(argv)
    report = prepare(args.payload, args.metadata, args.output, args.path_map)
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return admission.exit_code(report)


if __name__ == "__main__":
    raise SystemExit(main())
