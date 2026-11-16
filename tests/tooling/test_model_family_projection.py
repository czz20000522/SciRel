"""Project the real F02 family and reject damaged reader/index projections.

The canonical schema/contract validator is the #257 implementation. These tests
use it unchanged; no validator mock or alternative scientific implementation is
substituted for it. Synthetic controls cover format paths absent from F02;
they never add public assets or establish scientific validation.
"""

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import capability_catalog as catalog  # noqa: E402
from build_catalog import build_catalog  # noqa: E402
from build_pure_delivery import consumer_index, seal_runtime  # noqa: E402
from build_scirel_sphinx import render_api  # noqa: E402
from capability_query import query_capabilities, validate_capability_index  # noqa: E402
from consumer_tools import call_tool  # noqa: E402
from validate_asset_documents import validate_document  # noqa: E402


def real_family_fixture():
    """Read the actual canonical F02 contract and its authored Chinese reader."""
    document = json.loads(
        (ROOT / "catalog/examples/scirel.neoclassical.bootstrap-coefficients.json").read_text()
    )
    readers = json.loads((ROOT / "tools/docs/zh/zh_missing_runtime_domains.json").read_text())
    reader = next(
        record for record in readers["records"] if record["asset_id"] == document["asset_id"]
    )
    validate_document(document)
    return document, reader


def family_fixture():
    """Use an existing port layout, with explicitly synthetic method claims."""
    document, reader = real_family_fixture()
    document["inputs"] = [port for port in document["inputs"] if port["name"] != "method"]
    reader["inputs"] = [port for port in reader["inputs"] if port["name"] != "method"]
    document["asset_id"] = "scirel.neoclassical.synthetic-family"
    document["summary"] = "Synthetic projection fixture only; no scientific validation."
    document["identity"]["model"] = "Synthetic model selection fixture"
    document["discovery"] = {"device_scope": "unclassified"}
    physical = ", ".join(port["name"] for port in document["inputs"])
    document["public_api"]["python"] = {
        "module": "scirel.neoclassical.bootstrap",
        "symbol": "synthetic_family",
        "canonical_module": "scirel.neoclassical",
        "canonical_symbol": "synthetic_family",
        "signature": f"synthetic_family({physical}, *, method='model_a', order=16)",
    }
    for name, default, dtype in (("method", "model_a", "string"), ("order", 16, "integer")):
        document["inputs"].append(
            {
                "name": name,
                "description": "Synthetic selector or control",
                "units": "dimensionless",
                "shape": "scalar",
                "dtype": dtype,
                "required": False,
                "default": default,
                "constraints": "Synthetic fixture input only",
            }
        )
    test_file = "tests/tooling/test_model_family_projection.py"
    document["verification"]["tests"] = [test_file]
    document["example"]["code"] = (
        "from scirel.neoclassical import synthetic_family\n"
        "synthetic_family([.3], [1.], [1.], [1.], method='model_a')\n"
        "synthetic_family([.3], [1.], [1.], [1.], method='model_b')\n"
    )
    members = []
    for name, order in (("model_a", 16), ("model_b", 32)):
        members.append(
            {
                "name": name,
                "model": f"Synthetic {name} model; not calibrated",
                "numerical_controls": {
                    "order": {"default": order, "constraints": "positive synthetic order"}
                },
                "applicability": {
                    "preconditions": ["Synthetic positive input"],
                    "supported": ["Format projection only"],
                    "excluded": ["No physical validation"],
                },
                "failure_semantics": {
                    "invalid_input": "Raises ValueError for invalid synthetic input",
                    "runtime_failure": "No synthetic fallback",
                    "nonconvergence": "No iteration",
                    "partial_results": "No partial results",
                },
                "verification": {
                    "scope": [f"Synthetic {name} projection"],
                    "tests": [
                        test_file + "::test_catalog_routes_and_summaries_preserve_one_contract"
                    ],
                    "evidence_ceiling": "Format projection only, not scientific PASS",
                    "known_limitations": [f"Unique {name} limitation"],
                },
            }
        )
    document["family"] = {
        "name": "synthetic-model-family",
        "default": "model_a",
        "default_reason": "Synthetic selected default, not a physical recommendation",
        "methods": members,
    }
    reader["asset_id"] = document["asset_id"]
    for port in document["inputs"][-2:]:
        reader["inputs"].append(
            {
                "name": port["name"],
                "description": "合成选择项或控制量",
                "constraints": "只作格式测试",
                "dtype": "字符串或整数",
                "shape": "标量",
                "units": "无量纲",
            }
        )
    reader["family"] = {
        "name": "synthetic-model-family",
        "default": "model_a",
        "default_reason": "这是合成示例的默认选择，不作物理推荐。",
        "methods": [],
    }
    for member in members:
        reader["family"]["methods"].append(
            {
                "name": member["name"],
                "model": "合成模型，仅验证投影。",
                "numerical_controls": {
                    "order": {
                        "default": member["numerical_controls"]["order"]["default"],
                        "constraints": "合成阶数须为正整数。",
                    }
                },
                "applicability": {
                    "preconditions": ["合成输入为正。"],
                    "supported": ["仅验证格式投影。"],
                    "excluded": ["不作物理验证。"],
                },
                "failure_semantics": {
                    "invalid_input": "非法合成输入抛出异常。",
                    "runtime_failure": "不返回替代值。",
                    "nonconvergence": "没有迭代。",
                    "partial_results": "不返回部分结果。",
                },
                "verification": {
                    "scope": ["覆盖合成方法投影。"],
                    "evidence_ceiling": "仅验证格式，不作科学放行。",
                    "known_limitations": ["此方法的专属局限。"],
                },
            }
        )
    validate_document(document)
    return document, reader


def write_inputs(tmp_path, document, reader):
    documents = tmp_path / "contracts"
    documents.mkdir()
    data = catalog.encode(document)
    (documents / (document["asset_id"] + ".json")).write_bytes(data)
    reader = deepcopy(reader)
    bundle = tmp_path / "zh.json"
    bundle.write_bytes(
        catalog.encode(
            {"schema": "scirel.reader-translation", "language": "zh-CN", "records": [reader]}
        )
    )
    return documents, bundle


@pytest.mark.parametrize("fixture", [real_family_fixture, family_fixture], ids=["f02", "controls"])
def test_family_reader_loads_every_method_and_derives_test_identity(tmp_path, fixture):
    document, reader = fixture()
    before = deepcopy(reader)
    docs, bundle = write_inputs(tmp_path, document, reader)
    translated = catalog.load_translations(ROOT, docs, [document], translation_paths=[bundle])[
        document["asset_id"]
    ]
    for method, source in zip(
        translated["family"]["methods"], document["family"]["methods"], strict=True
    ):
        assert method["verification"]["tests"] == source["verification"]["tests"]
    assert reader == before
    assert (
        "tests"
        not in json.loads(bundle.read_bytes())["records"][0]["family"]["methods"][0]["verification"]
    )


@pytest.mark.parametrize(
    "damage",
    [
        "missing-family",
        "extra-method",
        "missing-method",
        "reorder-methods",
        "wrong-default",
        "wrong-name",
        "missing-model",
        "english-model",
        "missing-default-reason",
        "wrong-control",
        "wrong-control-default",
        "bool-control-default",
        "missing-control-constraints",
        "dropped-supported",
        "extra-excluded",
        "missing-failure",
        "missing-ceiling",
        "dropped-limit",
        "unknown-verification",
        "copied-tests",
    ],
)
def test_bad_family_translations_fail_before_projection(tmp_path, damage):
    document, reader = family_fixture()
    family = reader["family"]
    member = family["methods"][0]
    if damage == "missing-family":
        del reader["family"]
    elif damage == "extra-method":
        family["methods"].append(deepcopy(member))
    elif damage == "missing-method":
        family["methods"].pop()
    elif damage == "reorder-methods":
        family["methods"].reverse()
    elif damage == "wrong-default":
        family["default"] = "model_b"
    elif damage == "wrong-name":
        family["name"] = "other"
    elif damage == "missing-model":
        del member["model"]
    elif damage == "english-model":
        member["model"] = document["family"]["methods"][0]["model"]
    elif damage == "missing-default-reason":
        family["default_reason"] = ""
    elif damage == "wrong-control":
        member["numerical_controls"]["phantom"] = member["numerical_controls"].pop("order")
    elif damage == "wrong-control-default":
        member["numerical_controls"]["order"]["default"] = 17
    elif damage == "bool-control-default":
        member["numerical_controls"]["order"]["default"] = True
    elif damage == "missing-control-constraints":
        del member["numerical_controls"]["order"]["constraints"]
    elif damage == "dropped-supported":
        member["applicability"]["supported"] = []
    elif damage == "extra-excluded":
        member["applicability"]["excluded"].append("多余条款。")
    elif damage == "missing-failure":
        del member["failure_semantics"]["runtime_failure"]
    elif damage == "missing-ceiling":
        member["verification"]["evidence_ceiling"] = ""
    elif damage == "dropped-limit":
        member["verification"]["known_limitations"] = []
    elif damage == "unknown-verification":
        member["verification"]["approval"] = "已通过。"
    elif damage == "copied-tests":
        member["verification"]["tests"] = ["tests/stale.py"]
    docs, bundle = write_inputs(tmp_path, document, reader)
    with pytest.raises(ValueError, match="family"):
        catalog.load_translations(ROOT, docs, [document], translation_paths=[bundle])


def test_nonfamily_contract_cannot_acquire_a_reader_family(tmp_path):
    document, reader = family_fixture()
    del document["family"]
    docs, bundle = write_inputs(tmp_path, document, reader)
    with pytest.raises(ValueError, match="family"):
        catalog.load_translations(ROOT, docs, [document], translation_paths=[bundle])


@pytest.mark.parametrize("fixture", [real_family_fixture, family_fixture], ids=["f02", "controls"])
def test_discovery_and_lightweight_index_retain_both_methods_without_extra_assets(fixture):
    document, reader = fixture()
    names = [member["name"] for member in document["family"]["methods"]]
    full = catalog.build_capability_index(
        [document], source_revision="a" * 40, translations={document["asset_id"]: reader}
    )
    light = consumer_index(full)
    assert full["asset_count"] == light["asset_count"] == 1
    assert light["assets"][0]["family"] == full["assets"][0]["family"]
    assert [m["name"] for m in light["assets"][0]["family"]["methods"]] == names
    assert light["assets"][0]["family"]["paths"] == [
        ["neoclassical", document["family"]["name"], name] for name in names
    ]
    for ranked in (False, True):
        for name in names:
            page = query_capabilities(
                light, {"schema": "scirel.capability-query", "q": name}, ranked=ranked
            )
            assert page["total"] == 1 and page["items"][0]["asset_id"] == document["asset_id"]
            assert page["items"][0]["family"] == light["assets"][0]["family"]
    chinese_limit = reader["family"]["methods"][1]["verification"]["known_limitations"][0]
    assert chinese_limit.lower() in full["search_text"][document["asset_id"]]
    english = catalog.build_capability_index([document], source_revision="a" * 40, language="en")
    assert names[1] in english["search_text"][document["asset_id"]]
    assert chinese_limit.lower() not in english["search_text"][document["asset_id"]]


def test_family_without_numerical_controls_keeps_every_method(tmp_path):
    document, reader = family_fixture()
    for source, translated in zip(
        document["family"]["methods"], reader["family"]["methods"], strict=True
    ):
        source["numerical_controls"] = {}
        translated["numerical_controls"] = {}
    validate_document(document)
    documents, bundle = write_inputs(tmp_path, document, reader)
    loaded = catalog.load_translations(ROOT, documents, [document], translation_paths=[bundle])
    page = render_api(document, loaded[document["asset_id"]], [])
    assert "method=model_a" in page and "method=model_b" in page
    assert page.count("此方法没有专属数值控制项") == 2


@pytest.mark.parametrize("fixture", [real_family_fixture, family_fixture], ids=["f02", "controls"])
def test_catalog_routes_and_summaries_preserve_one_contract(tmp_path, fixture):
    document, reader = fixture()
    docs, _ = write_inputs(tmp_path, document, reader)
    output = tmp_path / "catalog"
    build_catalog(
        docs,
        output,
        catalog_id="synthetic-family",
        release_version="0.0.0",
        coverage_status="complete",
        declared_total=1,
        source_revision="a" * 40,
    )
    route = json.loads((output / "routes/all.jsonl").read_text())
    summary_files = list((output / "summaries").rglob("*.jsonl"))
    summaries = [
        json.loads(line) for path in summary_files for line in path.read_text().splitlines()
    ]
    assert len(summaries) == 1
    assert route["family"] == summaries[0]["family"] == catalog.family_summary(document)
    exact = json.loads((output / route["exact_record"]["path"]).read_text())
    assert exact["family"] == document["family"]


@pytest.mark.parametrize("damage", ["drop-method", "drop-path", "duplicate", "bad-default"])
def test_light_index_rejects_broken_method_summaries(damage):
    document, _ = family_fixture()
    light = consumer_index(catalog.build_capability_index([document], source_revision="a" * 40))
    family = light["assets"][0]["family"]
    if damage == "drop-method":
        family["methods"].pop()
    elif damage == "drop-path":
        family["paths"].pop()
    elif damage == "duplicate":
        family["methods"][1] = deepcopy(family["methods"][0])
    else:
        family["default"] = "ghost"
    with pytest.raises(ValueError, match="family"):
        validate_capability_index(light)


@pytest.mark.parametrize("language", ["zh", "en"])
@pytest.mark.parametrize("fixture", [real_family_fixture, family_fixture], ids=["f02", "controls"])
def test_actual_bilingual_api_html_keeps_method_specific_text(tmp_path, language, fixture):
    from sphinx.application import Sphinx

    document, reader = fixture()
    catalog.validate_family_translation(document, reader)
    rst = render_api(document, reader, [], language=language)
    source = tmp_path / "source"
    source.mkdir()
    (source / "conf.py").write_text(
        "project='Family projection'\nmaster_doc='index'\nextensions=[]\n"
    )
    (source / "index.rst").write_text(rst)
    from io import StringIO

    warnings = StringIO()
    app = Sphinx(
        str(source),
        str(source),
        str(tmp_path / "html"),
        str(tmp_path / "doctrees"),
        "html",
        status=StringIO(),
        warning=warnings,
        freshenv=True,
    )
    app.build(force_all=True)
    assert app.statuscode == 0, warnings.getvalue()
    from bs4 import BeautifulSoup

    text = BeautifulSoup((tmp_path / "html/index.html").read_text(), "html.parser").get_text(
        " ", strip=True
    )
    assert all(member["name"] in text for member in document["family"]["methods"])
    selected = document if language == "en" else reader
    opposite = reader if language == "en" else document
    assert selected["family"]["default_reason"] in text
    for member, other in zip(
        selected["family"]["methods"], opposite["family"]["methods"], strict=True
    ):
        assert member["model"] in text
        assert other["model"] not in text
        for key in ("scope", "known_limitations"):
            assert all(clause in text for clause in member["verification"][key])
        assert member["verification"]["evidence_ceiling"] in text
    if fixture is family_fixture:
        assert "16" in text and "32" in text
    assert document["family"]["methods"][1]["verification"]["tests"][0] in text


def test_sync_uses_the_same_family_reader_validation():
    spec = importlib.util.spec_from_file_location(
        "family_sync", ROOT / "skills/development/scirel-acceptance/scripts/check_contract_sync.py"
    )
    sync = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sync)
    document, reader = family_fixture()
    reader["family"]["methods"].pop()
    assert any("family" in error for error in sync.clause_errors(document, reader))


@pytest.mark.parametrize("fixture", [real_family_fixture, family_fixture], ids=["f02", "controls"])
def test_sealed_runtime_browse_search_get_keeps_single_contract_and_member_limits(
    tmp_path, fixture
):
    document, reader = fixture()
    names = [member["name"] for member in document["family"]["methods"]]
    full = catalog.build_capability_index([document], source_revision="a" * 40)
    files = {
        "catalog/capability-index.json": catalog.encode(consumer_index(full)),
        f"catalog/contracts/{document['asset_id']}.json": catalog.encode(document),
        "wheel/synthetic.whl": b"Synthetic bytes, not an installable or tested wheel",
    }
    root = tmp_path / "runtime"
    for relative, data in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    identity = seal_runtime(
        root,
        {
            "schema": "scirel.consumer-runtime",
            "source_revision": "a" * 40,
            "asset_count": 1,
            "runtime": {
                "wheel": "synthetic.whl",
                "wheel_sha256": catalog.sha(files["wheel/synthetic.whl"]),
                "requires_python": ">=3.12",
                "requires_dist": [],
                "dependencies_bundled": False,
            },
            "retrieval": {
                "backend": "lexical-and",
                "completeness": "unknown",
                "scientific_applicability": "not_assessed",
                "incomplete_status": "retrieval_incomplete",
            },
        },
    )
    pins = {
        "expected_snapshot_sha256": identity["snapshot_sha256"],
        "expected_wheel_sha256": identity["runtime"]["wheel_sha256"],
    }
    for tool in ("scirel_browse", "scirel_search"):
        result = call_tool(
            root, tool, {**pins, ("model" if tool == "scirel_browse" else "q"): names[1]}
        )
        assert result["outcome"] == "match"
        assert [m["name"] for m in result["result"]["items"][0]["family"]["methods"]] == names
    result = call_tool(root, "scirel_get", {**pins, "asset_id": document["asset_id"]})
    assert result["outcome"] == "ok" and result["document"] == document
    assert (
        result["document"]["family"]["methods"][1]["verification"]["known_limitations"]
        == document["family"]["methods"][1]["verification"]["known_limitations"]
    )


@pytest.mark.parametrize(
    "damage", ["drop-method", "reverse-methods", "drop-scope", "drop-limit", "english-model"]
)
def test_real_family_reader_rejects_lost_or_untranslated_method_claims(tmp_path, damage):
    document, reader = real_family_fixture()
    methods = reader["family"]["methods"]
    if damage == "drop-method":
        methods.pop()
    elif damage == "reverse-methods":
        methods.reverse()
    elif damage == "drop-scope":
        methods[1]["verification"]["scope"].pop()
    elif damage == "drop-limit":
        methods[1]["verification"]["known_limitations"].pop()
    else:
        methods[1]["model"] = document["family"]["methods"][1]["model"]
    docs, bundle = write_inputs(tmp_path, document, reader)
    with pytest.raises(ValueError, match="family"):
        catalog.load_translations(ROOT, docs, [document], translation_paths=[bundle])
