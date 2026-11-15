"""One callable contract retains distinct, independently evidenced model choices."""

from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_asset_documents import AssetDocumentError, validate_document  # noqa: E402


def family_document():
    """Use real member descriptions in a synthetic format-only contract fixture."""
    members = [
        json.loads(
            (
                ROOT
                / "catalog/examples"
                / f"scirel.neoclassical.{name}-bootstrap-coefficients.json"
            ).read_text(encoding="utf-8")
        )
        for name in ("redl", "sauter")
    ]
    document = deepcopy(members[0])
    physical_names = ", ".join(port["name"] for port in document["inputs"])
    document["asset_id"] = "scirel.neoclassical.bootstrap-coefficients"
    document["public_api"]["python"] = {
        "module": "scirel.neoclassical.bootstrap",
        "symbol": "compute_bootstrap_coefficients",
        "signature": f"compute_bootstrap_coefficients({physical_names}, *, method='redl')",
        "canonical_module": "scirel.neoclassical",
        "canonical_symbol": "compute_bootstrap_coefficients",
    }
    document["inputs"].append(
        {
            "name": "method",
            "description": "Coefficient fit selector",
            "units": "dimensionless",
            "shape": "scalar",
            "dtype": "string",
            "required": False,
            "default": "redl",
            "constraints": "Exactly redl or sauter; the physical inputs keep their meaning.",
        }
    )
    document["family"] = {
        "name": "bootstrap-coefficients",
        "default": "redl",
        "default_reason": "Redl is the selected fit; the older fit remains an explicit choice.",
        "methods": [
            {
                "name": name,
                "model": member["identity"]["model"],
                "numerical_controls": {},
                "applicability": member["applicability"],
                "failure_semantics": member["failure_semantics"],
                "verification": member["verification"],
            }
            for name, member in zip(("redl", "sauter"), members)
        ],
    }
    document["verification"]["tests"] = sorted(
        {path for member in members for path in member["verification"]["tests"]}
    )
    document["example"]["code"] = (
        "from scirel.neoclassical import compute_bootstrap_coefficients\n"
        "redl = compute_bootstrap_coefficients([0.3], [1.0], [1.0], [1.0], method='redl')\n"
        "sauter = compute_bootstrap_coefficients([0.3], [1.0], [1.0], [1.0], method='sauter')\n"
        "assert set(redl) == set(sauter) == {'L31', 'L32', 'L34', 'alpha'}"
    )
    return document


def test_one_contract_accepts_distinct_model_ranges_and_evidence():
    document = family_document()
    assert validate_document(document) is document
    assert [member["name"] for member in document["family"]["methods"]] == ["redl", "sauter"]


def test_schema_declares_the_same_single_family_shape():
    schema = json.loads((ROOT / "contracts/scientific-asset-document.schema.json").read_text())
    assert "family" in schema["properties"]
    assert "family" not in schema["required"]
    family = schema["$defs"]["family"]
    assert family["additionalProperties"] is False
    assert set(family["required"]) == {"name", "default", "default_reason", "methods"}


@pytest.mark.parametrize("key", ["name", "default", "default_reason", "methods"])
def test_missing_family_fields_are_rejected(key):
    document = family_document()
    del document["family"][key]
    with pytest.raises(AssetDocumentError, match="family.*missing.*" + key):
        validate_document(document)


@pytest.mark.parametrize(
    "key",
    ["name", "model", "numerical_controls", "applicability", "failure_semantics", "verification"],
)
def test_each_method_must_retain_its_own_contract_and_evidence(key):
    document = family_document()
    del document["family"]["methods"][1][key]
    with pytest.raises(AssetDocumentError, match="family.*missing.*" + key):
        validate_document(document)


def test_unknown_family_or_method_keys_cannot_hide_claims():
    for section in ("family", "method"):
        document = family_document()
        target = document["family"] if section == "family" else document["family"]["methods"][0]
        target["phantom_approval"] = True
        with pytest.raises(AssetDocumentError, match="family.*unknown.*phantom_approval"):
            validate_document(document)


@pytest.mark.parametrize("default", ["unknown", "", None])
def test_unknown_or_missing_default_is_rejected(default):
    document = family_document()
    document["family"]["default"] = default
    with pytest.raises(AssetDocumentError, match="family.*default"):
        validate_document(document)


def test_duplicate_method_names_do_not_count_as_two_models():
    document = family_document()
    document["family"]["methods"].append(deepcopy(document["family"]["methods"][0]))
    with pytest.raises(AssetDocumentError, match="family.*duplicate.*redl"):
        validate_document(document)


def test_a_default_only_in_the_family_cannot_override_the_public_input_default():
    document = family_document()
    document["inputs"][-1]["default"] = "sauter"
    with pytest.raises(AssetDocumentError, match="family.*default"):
        validate_document(document)


def test_a_member_without_executable_evidence_is_rejected():
    document = family_document()
    document["family"]["methods"][1]["verification"]["tests"] = []
    with pytest.raises(AssetDocumentError, match="family.*verification.*tests"):
        validate_document(document)


def test_member_evidence_must_enter_the_existing_test_consumer_scope():
    document = family_document()
    document["family"]["methods"][1]["verification"]["tests"] = [
        "tests/tooling/unselected_method_file.py::test_method"
    ]
    with pytest.raises(AssetDocumentError, match="family.*verification.*tests"):
        validate_document(document)


def test_file_scope_already_selects_its_method_node_without_adding_duplicate_tests():
    document = family_document()
    scope = document["verification"]["tests"][0]
    document["family"]["methods"][0]["verification"]["tests"] = [scope + "::test_method"]
    assert validate_document(document) is document


def test_a_method_control_is_explicit_and_optional_while_other_methods_can_omit_it():
    document = family_document()
    document["public_api"]["python"]["signature"] = document["public_api"]["python"][
        "signature"
    ].replace("method='redl')", "method='redl', order=None)")
    document["inputs"].append(
        {
            "name": "order",
            "description": "Numeric truncation order",
            "units": "1",
            "shape": "scalar",
            "dtype": "int or None",
            "required": False,
            "default": None,
            "constraints": "An explicit positive integer for methods using it.",
        }
    )
    document["family"]["methods"][0]["numerical_controls"] = {
        "order": {"default": 8, "constraints": "A positive integer."}
    }
    assert validate_document(document) is document


def test_a_family_method_selector_must_be_keyword_only_in_the_real_declared_signature():
    document = family_document()
    document["public_api"]["python"]["signature"] = document["public_api"]["python"][
        "signature"
    ].replace(", *, method", ", method")
    with pytest.raises(AssetDocumentError, match="family.*keyword-only"):
        validate_document(document)


def test_method_numeric_controls_must_name_real_explicit_parameters():
    document = family_document()
    document["family"]["methods"][0]["numerical_controls"] = {
        "invisible_tolerance": {"default": 1e-8, "constraints": "positive"}
    }
    with pytest.raises(AssetDocumentError, match="family.*invisible_tolerance"):
        validate_document(document)


def test_examples_cannot_exercise_only_the_default_method():
    document = family_document()
    document["example"]["code"] = (
        "from scirel.neoclassical import compute_bootstrap_coefficients\n"
        "compute_bootstrap_coefficients([0.3], [1.0], [1.0], [1.0], method='redl')"
    )
    with pytest.raises(AssetDocumentError, match="family.*example.*sauter"):
        validate_document(document)
