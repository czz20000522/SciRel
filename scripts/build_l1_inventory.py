"""Build a JSON index from saved CodeFusion L1 project artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scirel_workflow import build_inventory  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="directory containing saved L1 projects")
    parser.add_argument("--output", type=Path, required=True, help="new JSON inventory path")
    parser.add_argument("--project", action="append", dest="projects", default=[])
    args = parser.parse_args()
    inventory = build_inventory(args.root, project_ids=args.projects or None)
    if len(args.projects) == 1:
        payload = inventory.to_project_l1_payloads()[0]
        candidate_scope = args.projects[0]
    else:
        payload = inventory.to_l1_payload()
        candidate_scope = None
    output = args.output.resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing inventory: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": output.as_posix(),
                "inventory_id": inventory.inventory_id,
                "inventory_digest": inventory.inventory_digest,
                "projects": len(inventory.projects),
                "operators": inventory.operator_count,
                "task_graphs": inventory.task_graph_count,
                "assets": inventory.asset_count,
                "gaps": len(inventory.gaps()),
                "candidate_scope": candidate_scope,
                "candidate_scoped_input": candidate_scope is not None,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
