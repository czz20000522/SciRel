"""Check the C4 usage-acceptance task list against the current contracts.

The list is the frozen baseline a blind consumer runs against a delivered
package, so it has to stay in step with `catalog/examples/`: every asset it
names must exist, every declared parameter, output field, tolerance unit and
rejection it relies on must be stated by that asset's own contract, and every
domain must carry the quota derived from the current asset distribution.

Changes to the tasks change `tasks_digest`, which is stored in the list itself.
Editing a criterion or widening a tolerance therefore forces a new digest into
the tracked file instead of passing silently.

This script checks structure and agreement only. It never imports scirel, never
runs a task and never writes outside stdout, so it can run before a task is
executed and cannot be satisfied by a candidate result.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
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
    "EQDSKFormatError",
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


def output_unit(document: dict, name: str) -> str:
    for item in document.get("outputs") or []:
        if item.get("name") == name:
            return str(item.get("units") or "")
    return ""


def input_names(document: dict) -> list[str]:
    return [item["name"] for item in document.get("inputs") or [] if "name" in item]


def has_placeholder(value) -> bool:
    if isinstance(value, str):
        lowered = value.lower()
        return any(token in lowered for token in PLACEHOLDER)
    if isinstance(value, dict):
        return any(has_placeholder(item) for item in value.values())
    if isinstance(value, list):
        return any(has_placeholder(item) for item in value)
    return False


def rejection_text(document: dict, key: str) -> str:
    return str((document.get("failure_semantics") or {}).get(key) or "")


def excluded_text(document: dict) -> str:
    return " ".join(document.get("applicability", {}).get("excluded") or [])


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
        quantity = str(criterion.get("quantity") or "")
        unit = str(criterion.get("unit") or "")
        if quantity == "@declared_outputs":
            if not any(output_names(assets[asset]) for asset in names):
                _fail(errors, where, "contract declares no outputs to compare")
        else:
            owners = [asset for asset in names if quantity in output_names(assets[asset])]
            if not owners:
                _fail(
                    errors,
                    where,
                    f"quantity {quantity!r} is not a declared output name of {names}, "
                    "so its unit cannot be bound to the contract",
                )
            elif unit != "dimensionless":
                declared_units = [output_unit(assets[asset], quantity) for asset in owners]
                if not any(unit in item for item in declared_units if item):
                    _fail(
                        errors,
                        where,
                        f"unit {unit!r} is not the declared unit of {quantity!r} "
                        f"(declared: {[item for item in declared_units if item]})",
                    )
    elif kind == "exception":
        expected = criterion.get("expected")
        key = criterion.get("failure_key")
        asset = criterion.get("asset")
        if expected not in EXCEPTIONS:
            _fail(errors, where, f"expected {expected!r} is not a known exception channel")
        if key not in FAILURE_KEYS:
            _fail(errors, where, f"failure_key {key!r} is not a declared failure channel")
        if asset not in names:
            _fail(errors, where, f"exception criterion must name one task asset, got {asset!r}")
            return
        if expected in EXCEPTIONS and key in FAILURE_KEYS:
            if expected not in rejection_text(assets[asset], key):
                _fail(errors, where, f"{expected} is not stated by {key} of {asset}")
    elif kind == "invariant":
        if len(str(criterion.get("statement") or "")) < 20:
            _fail(errors, where, "invariant needs a statement of the relation being checked")
        if len(str(criterion.get("independent_source") or "")) < 10:
            _fail(
                errors,
                where,
                "invariant needs an independent_source explaining why it is not circular",
            )
        quote = criterion.get("contract_quote")
        if quote is not None:
            haystacks = [
                rejection_text(assets[asset], key) for asset in names for key in FAILURE_KEYS
            ]
            haystacks.extend(excluded_text(assets[asset]) for asset in names)
            haystacks.extend(str(assets[asset].get("boundary") or "") for asset in names)
            if not any(quote in text for text in haystacks):
                _fail(errors, where, f"contract_quote {quote!r} is not verbatim in those contracts")
    elif kind == "readback":
        if len(str(criterion.get("statement") or "")) < 10:
            _fail(errors, where, "readback needs a statement of what to re-open")


def check_stimulus(
    errors: list[str],
    where: str,
    task: dict,
    assets: dict[str, dict],
) -> None:
    """A failure task may vary exactly the declared stimuli, each quoted from the contract."""
    stimulus = task.get("stimulus")
    if not isinstance(stimulus, list) or not stimulus:
        _fail(errors, where, "failure tasks need a nonempty stimulus list")
        return
    exceptions: list[tuple[str, str]] = []
    for position, entry in enumerate(stimulus):
        local = f"{where} stimulus[{position}]"
        if not isinstance(entry, dict):
            _fail(errors, local, "stimulus entry must be an object")
            continue
        asset = entry.get("asset")
        field = entry.get("field")
        key = entry.get("failure_key")
        if asset not in task["assets"]:
            _fail(errors, local, f"asset {asset!r} is not one of the task assets")
            continue
        if field not in input_names(assets[asset]):
            _fail(
                errors,
                local,
                f"field {field!r} is not a declared input of {asset} "
                f"(declared: {input_names(assets[asset])})",
            )
        if "value" not in entry:
            _fail(errors, local, "stimulus entry needs the frozen value it substitutes")
        elif has_placeholder(entry["value"]):
            _fail(errors, local, "stimulus value must be frozen, not a placeholder")
        if key not in FAILURE_KEYS:
            _fail(errors, local, f"failure_key {key!r} is not a declared failure channel")
            continue
        quote = str(entry.get("declared_rejection") or "")
        if len(quote) < 8:
            _fail(errors, local, "needs the contract wording of the rejection it relies on")
        elif quote not in rejection_text(assets[asset], key):
            _fail(
                errors,
                local,
                f"declared_rejection {quote!r} is not verbatim in {key} of {asset}",
            )
        expected = entry.get("expected_exception")
        if expected not in EXCEPTIONS:
            _fail(errors, local, f"expected_exception {expected!r} is not a known channel")
        elif expected not in rejection_text(assets[asset], key):
            _fail(errors, local, f"{expected} is not stated by {key} of {asset}")
        else:
            exceptions.append((asset, key))
    invariant_text = " ".join(
        str(criterion.get("statement") or "")
        for criterion in task.get("criteria") or []
        if isinstance(criterion, dict) and criterion.get("kind") == "invariant"
    )
    readback_text = " ".join(
        str(criterion.get("statement") or "")
        for criterion in task.get("criteria") or []
        if isinstance(criterion, dict) and criterion.get("kind") == "readback"
    )
    for entry in stimulus:
        if not isinstance(entry, dict):
            continue
        field = str(entry.get("field") or "")
        if field and field not in invariant_text:
            _fail(
                errors,
                where,
                f"an invariant must describe the {field} stimulus it is judged on, "
                "not a different quantity",
            )
        if field and field not in readback_text:
            _fail(
                errors,
                where,
                f"the readback must confirm the {field} argument it was stimulated with",
            )
    seen = sorted(
        (criterion.get("asset"), criterion.get("failure_key"))
        for criterion in task.get("criteria") or []
        if isinstance(criterion, dict) and criterion.get("kind") == "exception"
    )
    if _valid_exception_pairs(task):
        if seen != sorted(exceptions):
            _fail(
                errors,
                where,
                f"exception criteria {seen} do not match the stimuli {sorted(exceptions)}",
            )


def _valid_exception_pairs(task: dict) -> bool:
    return all(
        isinstance(criterion, dict)
        and isinstance(criterion.get("asset"), str)
        and isinstance(criterion.get("failure_key"), str)
        for criterion in task.get("criteria") or []
        if isinstance(criterion, dict) and criterion.get("kind") == "exception"
    ) and any(
        isinstance(criterion, dict) and criterion.get("kind") == "exception"
        for criterion in task.get("criteria") or []
    )


def check_task(
    errors: list[str],
    task: dict,
    index: int,
    assets: dict[str, dict],
    excluded: set[str],
) -> None:
    task_id = task.get("id")
    where = f"task {task_id}" if isinstance(task_id, str) and task_id else f"task[{index}]"
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
                f"declared domains {sorted(set(declared))} do not match asset domains "
                f"{sorted(task_domains)}",
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
            else:
                declared: set[str] = set()
                for asset in names:
                    declared.update(input_names(assets[asset]))
                unknown_keys = sorted(set(values) - declared)
                if unknown_keys:
                    _fail(
                        errors,
                        where,
                        f"literal keys {unknown_keys} are not declared inputs of {names} "
                        f"(declared: {sorted(declared)})",
                    )
                if has_placeholder(values):
                    _fail(errors, where, "literal inputs must be frozen numbers, not placeholders")
        else:
            _fail(errors, where, f"input_binding mode {mode!r} is not contract_example or literal")

    if kind == "failure":
        check_stimulus(errors, where, task, assets)
    elif task.get("stimulus") is not None:
        _fail(errors, where, f"only failure tasks carry a stimulus, {kind} does not")

    calls = task.get("min_calls")
    if not isinstance(calls, int) or isinstance(calls, bool) or calls < 1:
        _fail(errors, where, "min_calls must be a positive integer")
    elif calls < len(names):
        _fail(errors, where, f"min_calls {calls} cannot exercise {len(names)} named entries")
    elif kind == "failure":
        stimulus = task.get("stimulus")
        if isinstance(stimulus, list) and calls < len(stimulus):
            _fail(errors, where, f"min_calls {calls} cannot exercise {len(stimulus)} stimuli")

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
        quote = str(task.get("excluded_quote") or "")
        if len(quote) < 8:
            _fail(errors, where, "inapplicable tasks must quote the excluded clause they rely on")
        elif not any(quote in excluded_text(assets[name]) for name in names):
            _fail(
                errors, where, f"excluded_quote {quote!r} is not verbatim in applicability.excluded"
            )
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
                errors, "quota", f"{domain} has {row['nominal']} nominal tasks but needs {required}"
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


def digest(document: dict) -> str:
    """Canonical digest of the tasks, stored in the list so an edit is visible."""
    payload = json.dumps(
        document.get("tasks"), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def check(
    document: dict, assets: dict[str, dict], excluded: set[str]
) -> tuple[list[str], dict[str, dict], int]:
    errors: list[str] = []
    if document.get("schema") != SCHEMA:
        _fail(errors, "root", f"schema must be {SCHEMA!r}")
    version = document.get("schema_version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        _fail(errors, "root", "schema_version must be a positive integer")
    for key in (
        "purpose",
        "freeze",
        "blind_consumer",
        "deliverables",
        "quota",
        "tasks",
        "tasks_digest",
    ):
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

    declared_digest = str(document.get("tasks_digest") or "")
    actual = digest(document)
    if declared_digest != actual:
        _fail(
            errors,
            "root",
            f"tasks_digest {declared_digest[:12]}… does not match the tasks ({actual[:12]}…); "
            "a changed task must land with its new digest and a recorded reason",
        )

    table, cross = check_quota(errors, document, assets)
    return errors, table, cross


def format_table(table: dict[str, dict]) -> str:
    header = (
        f"{'domain':16s}{'assets':>7s}{'need':>6s}{'nominal':>9s}"
        f"{'reject':>7s}{'named':>7s}{'named_req':>10s}"
    )
    lines = [header, "-" * len(header)]
    for domain, row in table.items():
        lines.append(
            f"{domain:16s}{row['assets']:7d}{row['required']:6d}{row['nominal']:9d}"
            f"{row['rejected']:7d}{row['named']:7d}{row['named_required']:10d}"
        )
    if table:
        keys = next(iter(table.values()))
        total = {key: sum(row[key] for row in table.values()) for key in keys}
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
        "declared_digest": document.get("tasks_digest"),
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
                f"\nOK: {len(document['tasks'])} tasks satisfy every quota and bind to the current "
                "contracts"
            )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
