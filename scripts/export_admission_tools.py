"""Export the public admission producer, validator, schemas and examples.

Only the three named scripts and contracts/admission are read. Export does not
inspect scientific source, catalog, private methods or external project data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_admission as admission
from prepare_admission import _new_output

SCRIPTS = ("prepare_admission.py", "validate_admission.py", "export_admission_tools.py")


def export(output: Path) -> dict:
    output = Path(output)
    report = {"directory": str(output), "status": "FAIL", "errors": [], "output_created": False}
    errors = report["errors"]
    try:
        root = Path(__file__).resolve().parents[1]
        contract_dir = root / "contracts/admission"
        _new_output(output, [contract_dir, *(root / "scripts" / name for name in SCRIPTS)], errors)
        contract_files, _ = admission.inspect_tree(contract_dir, errors)
        files = {f"contracts/admission/{name}": path for name, path in contract_files.items()}
        for name in SCRIPTS:
            source = root / "scripts" / name
            admission.check_ancestors(source, errors)
            if not source.is_file():
                errors.append(f"required tool is missing: {name}")
            files[f"scripts/{name}"] = source
        if errors:
            return report
        # Check all live schema definitions before exporting an unusable toolset.
        for name in ("project-final.schema.json", "files.schema.json", "path-map.schema.json"):
            admission._schema_definition(admission.read_json(contract_dir / name), name)
        entries = [{"path": name, "bytes": path.stat().st_size, "sha256": admission._sha(path)}
                   for name, path in sorted(files.items())]
        output.mkdir(exist_ok=False)
        report["output_created"] = True
        for entry in entries:
            target = output / entry["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(files[entry["path"]], target)
            if target.stat().st_size != entry["bytes"] or admission._sha(target) != entry["sha256"]:
                raise ValueError(f"tool bytes changed while copying: {entry['path']}")
        identity = hashlib.sha256(admission.json_bytes(entries)).hexdigest()
        manifest = {"schema": "scirel.admission-tools", "files": entries,
                    "identity_sha256": identity,
                    "identity_rule": "SHA256 of files encoded as UTF-8 JSON, ensure_ascii=False, indent=2, trailing LF",
                    "claim_ceiling": "Packaging and format validation only; no scientific acceptance."}
        (output / "TOOLS.json").write_bytes(admission.json_bytes(manifest))
        report.update(status="PASS", files=len(entries), identity_sha256=identity, manifest="TOOLS.json")
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        errors.append(f"cannot export admission tools: {type(exc).__name__}: {exc}")
    if report["output_created"] and report["status"] != "PASS":
        report["retained_output"] = str(output)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    report = export(args.output)
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return admission.exit_code(report)


if __name__ == "__main__":
    raise SystemExit(main())
