"""Build SciRel's own capability matrix from the asset catalog.

The matrix is a derived view: it answers "which scientific domains/relations
does SciRel already provide?" so a human can spot a missing domain and decide
which external project to decompose next. It is not a gap list and does not
read any external project.
"""

from __future__ import annotations

import argparse
import collections
import datetime as _dt
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "catalog" / "examples"


def _git_revision() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
            stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _port(text: str) -> str:
    return text.strip()


def summarize(document: dict) -> dict:
    api = document["public_api"]["python"]
    parts = api["module"].split(".")
    domain = parts[1] if len(parts) > 1 else "scirel"
    subdomain = ".".join(parts[:3]) if len(parts) > 2 else api["module"]
    inputs = [f"{p['name']}:{p.get('units', '')}" for p in document["inputs"]]
    outputs = [f"{p['name']}:{p.get('units', '')}" for p in document["outputs"]]
    return {
        "asset_id": document["asset_id"],
        "domain": domain,
        "subdomain": subdomain,
        "module": api["module"],
        "symbol": api["symbol"],
        "title_en": document["title"]["en"],
        "title_zh": document["title"]["zh"],
        "summary": document["summary"],
        "relation": document["identity"]["relation"],
        "boundary": document["identity"]["boundary"],
        "taxonomy": list(document.get("taxonomy", [])),
        "inputs": inputs,
        "outputs": outputs,
        "ports": " , ".join(inputs) + " -> " + " , ".join(outputs),
        "supported": list(document["applicability"]["supported"]),
        "excluded": list(document["applicability"]["excluded"]),
        "known_limitations": list(document["verification"]["known_limitations"]),
        "tests": list(document["verification"]["tests"]),
    }


def build_matrix(documents: list[dict], *, revision: str | None = None,
                 generated_at: str | None = None) -> dict:
    assets = sorted((summarize(document) for document in documents),
                    key=lambda item: item["asset_id"])
    domains: dict[str, list[dict]] = collections.defaultdict(list)
    taxonomy: collections.Counter[str] = collections.Counter()
    subdomains: collections.Counter[str] = collections.Counter()
    for asset in assets:
        domains[asset["domain"]].append(asset)
        subdomains[asset["subdomain"]] += 1
        taxonomy.update(asset["taxonomy"])
    return {
        "schema": "scirel.capability-matrix",
        "schema_version": "1.0",
        "source_revision": revision,
        "generated_at": generated_at or _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "total_assets": len(assets),
        "total_domains": len(domains),
        "domains": [
            {"domain": domain, "count": len(items),
             "assets": [item["asset_id"] for item in items],
             "subdomains": sorted({item["subdomain"] for item in items})}
            for domain, items in sorted(domains.items(), key=lambda pair: (-len(pair[1]), pair[0]))
        ],
        "taxonomy_counts": dict(sorted(taxonomy.items(), key=lambda pair: (-pair[1], pair[0]))),
        "subdomain_counts": dict(sorted(subdomains.items())),
        "assets": assets,
    }


def render_markdown(matrix: dict) -> str:
    lines = ["# SciRel capability matrix", ""]
    lines.append(f"- source revision: `{matrix.get('source_revision') or 'unknown'}`")
    lines.append(f"- generated at: `{matrix['generated_at']}`")
    lines.append(f"- assets: **{matrix['total_assets']}** across **{matrix['total_domains']}** domains")
    lines += ["", "## Domain coverage", "",
              "| domain | assets | representative functions |", "| --- | ---: | --- |"]
    assets = {asset["asset_id"]: asset for asset in matrix["assets"]}
    for group in matrix["domains"]:
        symbols = [assets[asset_id]["symbol"] for asset_id in group["assets"][:4]]
        more = " …" if group["count"] > 4 else ""
        lines.append(f"| `{group['domain']}` | {group['count']} | {', '.join(f'`{s}`' for s in symbols)}{more} |")
    lines += ["", "## Taxonomy coverage", "", "| tag | assets |", "| --- | ---: |"]
    for tag, count in matrix["taxonomy_counts"].items():
        lines.append(f"| `{tag}` | {count} |")
    for group in matrix["domains"]:
        lines += ["", f"## {group['domain']} ({group['count']})", "",
                  "| function | capability | ports | limits | tests |",
                  "| --- | --- | --- | --- | ---: |"]
        for asset_id in group["assets"]:
            asset = assets[asset_id]
            capability = asset["title_zh"] or asset["title_en"]
            boundary = asset["boundary"].replace("|", "\\|")
            if len(boundary) > 120:
                boundary = boundary[:117] + "…"
            ports = asset["ports"].replace("|", "\\|")
            if len(ports) > 100:
                ports = ports[:97] + "…"
            lines.append(f"| `{asset['symbol']}` | {capability} | {ports} | {boundary} | {len(asset['tests'])} |")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path, required=True,
                        help="directory for capability-matrix.json and CAPABILITY_MATRIX.md")
    args = parser.parse_args(argv)
    documents = [json.loads(path.read_text(encoding="utf-8"))
                 for path in sorted(args.catalog.glob("*.json"))]
    if not documents:
        print(f"no documents under {args.catalog}", file=sys.stderr)
        return 1
    matrix = build_matrix(documents, revision=_git_revision())
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "capability-matrix.json").write_text(
        json.dumps(matrix, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (args.output / "CAPABILITY_MATRIX.md").write_text(
        render_markdown(matrix), encoding="utf-8")
    print(f"wrote {args.output}/capability-matrix.json and CAPABILITY_MATRIX.md "
          f"({matrix['total_assets']} assets, {matrix['total_domains']} domains)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
