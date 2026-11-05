import sys
from pathlib import Path
from shutil import copyfile


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_public_export_documents import census  # noqa: E402


def test_public_export_document_census_has_no_current_reverse_gap():
    report = census(ROOT)

    assert report["schema"] == "scirel.public-export-document-census"
    assert report["counts"]["domains"] == len(report["domains"])
    assert report["counts"]["documented_bindings"] <= report["counts"]["public_callables"]
    assert report["counts"]["missing"] == 0
    assert report["duplicate_document_bindings"] == []
    assert report["missing"] == []


def test_public_export_document_census_cli_fails_closed_on_invalid_documents(
    tmp_path: Path, capsys
):
    from audit_public_export_documents import main

    assert main(["--source-root", str(ROOT), "--documents", str(tmp_path)]) == 1
    capsys.readouterr()


def test_public_export_document_census_cli_fails_on_reverse_gaps(tmp_path: Path, capsys):
    from audit_public_export_documents import main

    documents = tmp_path / "documents"
    documents.mkdir()
    source = ROOT / "catalog/examples/scirel.field.poloidal-field-from-flux.json"
    copyfile(source, documents / source.name)

    assert main(["--source-root", str(ROOT), "--documents", str(documents)]) == 1
    capsys.readouterr()


def test_public_export_document_census_cli_passes_for_current_tree(capsys):
    from audit_public_export_documents import main

    assert main(["--source-root", str(ROOT)]) == 0
    capsys.readouterr()
