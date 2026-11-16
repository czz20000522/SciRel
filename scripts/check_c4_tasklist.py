"""Check the C4 usage-acceptance task list against the current contracts.

The list is the frozen baseline a blind consumer runs against a delivered
package, so it has to stay in step with `catalog/examples/`: every asset it
names must exist, every declared parameter, output field and exception it
expects must be stated by that asset's own contract, and every domain must
carry the quota derived from the current asset distribution.

This script checks structure and agreement only. It never imports scirel, never
runs a task and never writes outside stdout, so it can run before a task is
executed and cannot be satisfied by a candidate result.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path

SCHEMA = "scirel.c4-usage-tasklist"
KINDS = ("nominal", "failure", "inapplicable", "cross")
CRITERION_KINDS = (
    "contract_fields",
    "parameters",
    "tolerance",
    "exception",
    "invariant",
    "readback",
)
FAILURE_KEYS = ("invalid_input", "runtime_failure", "nonconvergence", "partial_results")
EXCEPTIONS = (
    "TypeError",
    "ValueError",
    "FloatingPointError",
    "KeyError",
    "IndexError",
    "RuntimeWarning",
    "ApplicabilityWarning",
    "OSError",
)
PLACEHOLDER = ("tbd", "todo", "fixme", "待定", "xxx", "???", "placeholder")
NOMINAL_REQUIRED_KINDS = ("contract_fields", "parameters", "invariant")


def _fail(errors: list[str], where: str, message: str) -> None:
    errors.append(f"{where}: {message}")


def load_catalog(root: Path) -> tuple[dict[str, dict], set[str]]:
    assets: dict[str, dict] = {}
    for path in sorted((root / "catalog" / "examples").glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        assets[document["asset_id"]] = document
    excluded_path = root / "catalog" / "review" / "excluded_from_package.json"
    excluded: set[str] = set()
    if excluded_path.is_file():
        excluded = set(json.loads(excluded_path.read_text(encoding="utf-8")).get("ids", []))
    return assets, excluded


def domain_of(asset_id: str) -> str:
    parts = asset_id.split(".")
    return parts[1] if len(parts) > 2 else ""


def output_names(document: dict) -> list[str]:
    return [item["name"] for item in document.get("outputs") or [] if "name" in item]


def input_names(document: dict) -> set[str]:
    return {item["name"] for item in document.get("inputs") or [] if "name" in item}


def output_unit(document: dict, name: str) -> str:
    for item in document.get("outputs") or []:
        if item.get("name") == name:
            return str(item.get("units") or "")
    return ""


def has_placeholder(value) -> bool:
    if isinstance(value, str):
        lowered = value.lower()
        return any(token in lowered for token in PLACEHOLDER)
    if isinstance(value, dict):
        return any(has_placeholder(item) for item in value.values())
    if isinstance(value, list):
        return any(has_placeholder(item) for item in value)
    return False


def check_criterion(
    errors: list[str],
    where: str,
    criterion: dict,
    task: dict,
    assets: dict[str, dict],
) -> None:
    kind = criterion.get("kind")
    if kind not in CRITERION_KINDS:
        _fail(errors, where, f"unknown criterion kind {kind!r}")
        return
    names = task["assets"]
    if kind == "contract_fields":
        expect = criterion.get("expect")
        declared: set[str] = set()
        for asset in names:
            declared.update(output_names(assets[asset]))
        if expect == "all_declared_outputs":
            if not declared:
                _fail(errors, where, "contract declares no output names to bind")
        elif isinstance(expect, list) and expect:
            missing = [item for item in expect if item not in declared]
            if missing:
                _fail(errors, where, f"fields {missing} are not declared outputs of {names}")
        else:
            _fail(errors, where, "expect must be a nonempty list or 'all_declared_outputs'")
    elif kind == "parameters":
        expect = criterion.get("expect")
        if expect == "@declared_inputs":
            if not any(input_names(assets[asset]) for asset in names):
                _fail(errors, where, "contract declares no input names to bind")
        elif not isinstance(expect, list) or not expect:
            _fail(errors, where, "expect must be a nonempty list or '@declared_inputs'")
        else:
            allowed: set[str] = set()
            for asset in names:
                allowed.update(input_names(assets[asset]))
            missing = [item for item in expect if item not in allowed]
            if missing:
                _fail(errors, where, f"parameters {missing} are not declared inputs of {names}")
    elif kind == "tolerance":
        for field in ("quantity", "unit"):
            if not str(criterion.get(field) or "").strip():
                _fail(errors, where, f"tolerance criterion needs {field}")
        tolerance = criterion.get("tolerance")
        if not isinstance(tolerance, dict):
            _fail(errors, where, "tolerance criterion needs a tolerance object")
        else:
            if not any(key in tolerance for key in ("abs", "rel")):
                _fail(errors, where, "tolerance needs abs or rel")
            basis = str(tolerance.get("basis") or "")
            if len(basis) < 20:
                _fail(errors, where, "tolerance basis must state its error estimate in prose")
        if criterion.get("declared_before_run") is not True:
            _fail(errors, where, "tolerance must be marked declared_before_run: true")
        unit = str(criterion.get("unit") or "")
        if criterion.get("quantity") == "@declared_outputs" or unit == "as declared":
            if not any(output_names(assets[asset]) for asset in names):
                _fail(errors, where, "contract declares no outputs to compare")
        elif unit and unit != "dimensionless":
            declared_units = {
                output_unit(assets[asset], criterion.get("quantity") or "") for asset in names
            }
            if not any(unit in item for item in declared_units if item):
                if criterion.get("quantity") not in set().union(
                    *(output_names(assets[a]) for a in names)
                ):
                    _fail(
                        errors,
                        where,
                        f"quantity {criterion.get('quantity')!r} is not a declared output name, "
                        "so its unit cannot be bound to the contract",
                    )
    elif kind == "exception":
        expected = criterion.get("expected")
        key = criterion.get("failure_key")
        if expected not in EXCEPTIONS:
            _fail(errors, where, f"expected {expected!r} is not a known exception channel")
        if key not in FAILURE_KEYS:
            _fail(errors, where, f"failure_key {key!r} is not a declared failure channel")
        if expected in EXCEPTIONS and key in FAILURE_KEYS:
            texts = [
                str((assets[asset].get("failure_semantics") or {}).get(key) or "")
                for asset in names
            ]
            if not any(expected in text for text in texts):
                _fail(
                    errors,
                    where,
                    f"{expected} is not stated by {key} of {names}",
                )
    elif kind == "invariant":
        if len(str(criterion.get("statement") or "")) < 20:
            _fail(errors, where, "invariant needs a statement of the relation being checked")
        if len(str(criterion.get("independent_source") or "")) < 10:
            _fail(
                errors,
                where,
                "invariant needs an independent_source explaining why it is not circular",
            )
    elif kind == "readback":
        if len(str(criterion.get("statement") or "")) < 10:
            _fail(errors, where, "readback needs a statement of what to re-open")


def check_task(
    errors: list[str],
    task: dict,
    index: int,
    assets: dict[str, dict],
    excluded: set[str],
) -> None:
    where = f"task[{index}]"
    task_id = task.get("id")
    if not isinstance(task_id, str) or not task_id:
        _fail(errors, where, "missing id")
        where = f"task[{index}]"
    else:
        where = f"task {task_id}"
    kind = task.get("kind")
    if kind not in KINDS:
        _fail(errors, where, f"kind {kind!r} not in {list(KINDS)}")
        return
    names = task.get("assets")
    if not isinstance(names, list) or not names:
        _fail(errors, where, "assets must be a nonempty list")
        return
    unknown = [name for name in names if name not in assets]
    if unknown:
        _fail(errors, where, f"unknown asset ids {unknown}")
        return
    banned = sorted(set(names) & excluded)
    if banned:
        _fail(
            errors, where, f"assets excluded from the package cannot be acceptance tasks: {banned}"
        )
    if len(set(names)) != len(names):
        _fail(errors, where, "duplicate asset id inside one task")

    task_domains = {domain_of(name) for name in names}
    if kind == "cross":
        if task.get("domain") != "cross":
            _fail(errors, where, "cross tasks must set domain to 'cross'")
        declared = task.get("domains")
        if not isinstance(declared, list) or len(set(declared)) < 2:
            _fail(errors, where, "cross tasks must declare at least two domains")
        elif set(declared) != task_domains:
            _fail(
                errors,
                where,
                f"declared domains {sorted(set(declared))} do not match asset domains {sorted(task_domains)}",
            )
    else:
        domain = task.get("domain")
        if domain not in task_domains:
            _fail(
                errors, where, f"domain {domain!r} does not own its assets {sorted(task_domains)}"
            )
        if len(task_domains) != 1:
            _fail(
                errors,
                where,
                f"a {kind} task must stay inside one domain, got {sorted(task_domains)}",
            )

    if len(str(task.get("question") or "")) < 20:
        _fail(errors, where, "question must state the task in at least one sentence")
    if not str(task.get("subdomain") or "").strip():
        _fail(errors, where, "missing subdomain")

    binding = task.get("input_binding")
    if not isinstance(binding, dict):
        _fail(errors, where, "input_binding must be an object")
    else:
        mode = binding.get("mode")
        if mode == "contract_example":
            bound = binding.get("assets")
            if not isinstance(bound, list) or not bound:
                _fail(
                    errors,
                    where,
                    "contract_example binding needs the assets whose example fixes the input",
                )
            else:
                for asset in bound:
                    if asset not in names:
                        _fail(errors, where, f"binding asset {asset} is not one of the task assets")
                    elif not (assets[asset].get("example") or {}).get("code"):
                        _fail(errors, where, f"{asset} declares no example to bind")
        elif mode == "literal":
            values = binding.get("values")
            if not isinstance(values, dict) or not values:
                _fail(errors, where, "literal binding needs a nonempty values object")
            elif has_placeholder(values):
                _fail(errors, where, "literal inputs must be frozen numbers, not placeholders")
        else:
            _fail(errors, where, f"input_binding mode {mode!r} is not contract_example or literal")

    calls = task.get("min_calls")
    if not isinstance(calls, int) or isinstance(calls, bool) or calls < 1:
        _fail(errors, where, "min_calls must be a positive integer")

    criteria = task.get("criteria")
    if not isinstance(criteria, list) or not criteria:
        _fail(errors, where, "criteria must be a nonempty list")
        return
    seen: set[str] = set()
    kinds: list[str] = []
    for position, criterion in enumerate(criteria):
        if not isinstance(criterion, dict):
            _fail(errors, where, f"criterion[{position}] must be an object")
            continue
        local = f"{where} criterion[{criterion.get('id') or position}]"
        cid = criterion.get("id")
        if isinstance(cid, str) and cid:
            if cid in seen:
                _fail(errors, local, "duplicate criterion id")
            seen.add(cid)
        check_criterion(errors, local, criterion, task, assets)
        kinds.append(criterion.get("kind"))

    if kind == "nominal":
        if not any(item in NOMINAL_REQUIRED_KINDS for item in kinds):
            _fail(errors, where, "nominal tasks need a contract, parameter or invariant criterion")
        if "readback" not in kinds:
            _fail(errors, where, "nominal tasks need a readback criterion")
    if kind == "failure":
        if "exception" not in kinds:
            _fail(errors, where, "failure tasks need an exception criterion")
        if "tolerance" in kinds:
            _fail(
                errors,
                where,
                "a rejection has no numeric tolerance; remove the tolerance criterion",
            )
    if kind == "inapplicable":
        if "tolerance" in kinds:
            _fail(errors, where, "an inapplicable case returns no value, so it has no tolerance")
        if len(str(task.get("inapplicable_reason") or "")) < 20:
            _fail(errors, where, "inapplicable tasks must state why the model does not apply")
        excluded_text = [
            " ".join(assets[name].get("applicability", {}).get("excluded") or []) for name in names
        ]
        if not any(text.strip() for text in excluded_text):
            _fail(errors, where, "no asset in the task declares an excluded domain")
    if kind == "cross" and "invariant" not in kinds:
        _fail(errors, where, "cross-domain tasks need an invariant stating the handoff relation")


def check_quota(
    errors: list[str], document: dict, assets: dict[str, dict]
) -> tuple[dict[str, dict], int]:
    quota = document.get("quota")
    if not isinstance(quota, dict):
        _fail(errors, "quota", "missing quota object")
        return {}, 0
    divisor = quota.get("tasks_per_domain_divisor")
    floor = quota.get("min_per_domain")
    failure_floor = quota.get("min_failure_or_inapplicable_per_domain")
    cross_floor = quota.get("min_cross_domain")
    for name, value in (
        ("tasks_per_domain_divisor", divisor),
        ("min_per_domain", floor),
        ("min_failure_or_inapplicable_per_domain", failure_floor),
        ("min_cross_domain", cross_floor),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            _fail(errors, "quota", f"{name} must be a positive integer")
            return {}, 0

    tasks = document.get("tasks") or []
    nominal: dict[str, int] = defaultdict(int)
    rejected: dict[str, int] = defaultdict(int)
    named: dict[str, set[str]] = defaultdict(set)
    cross = 0
    for task in tasks:
        if not isinstance(task, dict):
            continue
        kind = task.get("kind")
        names = [name for name in task.get("assets") or [] if name in assets]
        if kind == "cross":
            cross += 1
            for name in names:
                named[domain_of(name)].add(name)
            continue
        for name in names:
            named[domain_of(name)].add(name)
        domain = task.get("domain")
        if kind == "nominal":
            nominal[domain] += 1
        elif kind in ("failure", "inapplicable"):
            rejected[domain] += 1

    by_domain: dict[str, int] = defaultdict(int)
    for asset in assets:
        by_domain[domain_of(asset)] += 1

    table: dict[str, dict] = {}
    for domain in sorted(by_domain):
        required = max(floor, math.ceil(by_domain[domain] / divisor))
        row = {
            "assets": by_domain[domain],
            "required": required,
            "nominal": nominal[domain],
            "rejected": rejected[domain],
            "named": len(named[domain]),
            "named_required": required,
        }
        table[domain] = row
        if row["nominal"] < required:
            _fail(
                errors,
                "quota",
                f"{domain} has {row['nominal']} nominal tasks but needs {required}",
            )
        if row["rejected"] < failure_floor:
            _fail(
                errors,
                "quota",
                f"{domain} has {row['rejected']} failure/inapplicable tasks but needs {failure_floor}",
            )
        if row["named"] < row["named_required"]:
            _fail(
                errors,
                "quota",
                f"{domain} names {row['named']} distinct assets but must reach {row['named_required']}",
            )
    if cross < cross_floor:
        _fail(errors, "quota", f"{cross} cross-domain tasks but needs {cross_floor}")
    return table, cross


def check(
    document: dict, assets: dict[str, dict], excluded: set[str]
) -> tuple[list[str], dict[str, dict], int]:
    errors: list[str] = []
    if document.get("schema") != SCHEMA:
        _fail(errors, "root", f"schema must be {SCHEMA!r}")
    version = document.get("schema_version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        _fail(errors, "root", "schema_version must be a positive integer")
    for key in ("purpose", "freeze", "blind_consumer", "deliverables", "quota", "tasks"):
        if key not in document:
            _fail(errors, "root", f"missing {key}")

    blind = document.get("blind_consumer")
    if isinstance(blind, dict):
        allowed = blind.get("allowed_inputs")
        forbidden = blind.get("forbidden_inputs")
        if not isinstance(allowed, list) or not allowed:
            _fail(errors, "blind_consumer", "allowed_inputs must be a nonempty list")
        if not isinstance(forbidden, list) or not forbidden:
            _fail(errors, "blind_consumer", "forbidden_inputs must be a nonempty list")
    else:
        _fail(errors, "blind_consumer", "must be an object")

    freeze = document.get("freeze")
    if isinstance(freeze, dict):
        if freeze.get("tolerances_declared_before_any_candidate_run") is not True:
            _fail(
                errors, "freeze", "must assert tolerances_declared_before_any_candidate_run: true"
            )
        for key in ("baseline", "input_binding_rule", "edit_rule"):
            if len(str(freeze.get(key) or "")) < 20:
                _fail(errors, "freeze", f"{key} must be stated in prose")
    else:
        _fail(errors, "freeze", "must be an object")

    tasks = document.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        _fail(errors, "root", "tasks must be a nonempty list")
        return errors, {}, 0
    ids: set[str] = set()
    for index, task in enumerate(tasks):
        if isinstance(task, dict):
            task_id = task.get("id")
            if isinstance(task_id, str):
                if task_id in ids:
                    _fail(errors, f"task[{index}]", f"duplicate id {task_id}")
                ids.add(task_id)
        check_task(errors, task if isinstance(task, dict) else {}, index, assets, excluded)

    table, cross = check_quota(errors, document, assets)
    return errors, table, cross


def digest(document: dict) -> str:
    """Canonical digest a freeze record quotes, so an edit is visible."""
    import hashlib

    payload = json.dumps(
        document.get("tasks"), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def format_table(table: dict[str, dict]) -> str:
    header = f"{'domain':16s}{'assets':>7s}{'need':>6s}{'nominal':>9s}{'reject':>7s}{'named':>7s}{'named_req':>10s}"
    lines = [header, "-" * len(header)]
    for domain, row in table.items():
        lines.append(
            f"{domain:16s}{row['assets']:7d}{row['required']:6d}{row['nominal']:9d}"
            f"{row['rejected']:7d}{row['named']:7d}{row['named_required']:10d}"
        )
    total = (
        {key: sum(row[key] for row in table.values()) for key in table[next(iter(table))]}
        if table
        else {}
    )
    if total:
        lines.append("-" * len(header))
        lines.append(
            f"{'TOTAL':16s}{total['assets']:7d}{total['required']:6d}{total['nominal']:9d}"
            f"{total['rejected']:7d}{total['named']:7d}{total['named_required']:10d}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--repo",
        default=".",
        help="repository root that owns catalog/examples (default: current directory)",
    )
    parser.add_argument(
        "--tasklist",
        default="examples/c4-usage-acceptance/tasklist.json",
        help="task list path, relative to --repo unless absolute",
    )
    parser.add_argument(
        "--print-digest", action="store_true", help="print the canonical tasks digest and exit"
    )
    parser.add_argument("--json", action="store_true", help="print the machine-readable report")
    args = parser.parse_args(argv)

    root = Path(args.repo).resolve()
    path = Path(args.tasklist)
    if not path.is_absolute():
        path = root / path
    if not path.is_file():
        print(f"FAIL: task list not found at {path}")
        return 2
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        print(f"FAIL: {path} is not valid JSON: {error}")
        return 2

    if args.print_digest:
        print(digest(document))
        return 0

    assets, excluded = load_catalog(root)
    errors, table, cross = check(document, assets, excluded)
    report = {
        "tasklist": str(path),
        "assets_in_catalog": len(assets),
        "domains_in_catalog": len(table),
        "tasks": len(document.get("tasks") or []),
        "cross_domain_tasks": cross,
        "digest": digest(document),
        "quota": table,
        "errors": errors,
        "ok": not errors,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_table(table))
        print()
        print(f"cross-domain tasks: {cross}")
        print(f"tasks digest: {report['digest']}")
        if errors:
            print(f"\nFAIL: {len(errors)} problem(s)")
            for error in errors:
                print(f"  - {error}")
        else:
            print(
                f"\nOK: {len(document['tasks'])} tasks satisfy every quota and bind to the current contracts"
            )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
