"""Capture public contract inputs and derive discovery data without site builds.

The same exact contract and bound Chinese reader validation serves source
queries, runtime export and human documentation. No renderer or scientific
callable is imported by this module.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import stat
import subprocess

from capability_query import CAPABILITY_INDEX_SCHEMA, DEVICE_SCOPES, validate_capability_index
from exposure import held_asset_ids
from validate_asset_documents import validate_document

LANGUAGES = ("zh", "en")


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_translations(
    root, documents, docs, translation_paths=None, excluded_ids=(), *, read_bytes=None
):
    """Load one exact reader set; an explicit selection keeps all binding gates.

    The default repository handbook still consumes all repository reader bundles.
    A selected scientific distribution can supply its own complete reader set
    without inheriting unrelated documents from another development selection.
    A supplied reader consumes the caller's captured bytes for both bundles and
    contract bindings, so validation cannot mix them with later filesystem bytes.
    """
    records = {}
    paths = (
        sorted((root / "tools/docs/zh").glob("*.json"))
        if translation_paths is None
        else translation_paths
    )
    for path in paths:
        bundle = json.loads(path.read_bytes() if read_bytes is None else read_bytes(path))
        if (
            not isinstance(bundle, dict)
            or bundle.get("schema") != "scirel.reader-translation"
            or bundle.get("language") != "zh-CN"
            or not isinstance(bundle.get("records"), list)
        ):
            raise ValueError("invalid reader translation: " + str(path))
        for item in bundle["records"]:
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("asset_id"), str)
                or not item["asset_id"].strip()
            ):
                raise ValueError("invalid reader record: " + str(path))
            if item["asset_id"] in records:
                raise ValueError("duplicate reader translation: " + item["asset_id"])
            records[item["asset_id"]] = item
    excluded_ids = set(excluded_ids)
    ids = {doc["asset_id"] for doc in docs}
    active_records = {
        asset: record for asset, record in records.items() if asset not in excluded_ids
    }
    if set(active_records) != ids:
        raise ValueError("Chinese reader coverage differs from exact document set")
    records = active_records
    for doc in docs:
        asset = doc["asset_id"]
        item = records[asset]
        contract_path = documents / (asset + ".json")
        contract_bytes = (
            contract_path.read_bytes() if read_bytes is None else read_bytes(contract_path)
        )
        digest = hashlib.sha256(contract_bytes).hexdigest()
        if item.get("source_sha256") != digest:
            raise ValueError("stale Chinese reader translation: " + asset)
        for side in ("inputs", "outputs"):
            ports = item.get(side)
            if not isinstance(ports, list) or any(not isinstance(port, dict) for port in ports):
                raise ValueError("invalid translated ports: " + asset + ":" + side)
            if [x.get("name") for x in ports] != [x["name"] for x in doc[side]]:
                raise ValueError("translated port names/order differ: " + asset)
            for port in ports:
                for key in ("description", "constraints", "dtype"):
                    if not isinstance(port.get(key), str) or not port[key].strip():
                        raise ValueError("empty translated port field: " + asset)
        for key in ("summary", "definition", "model", "boundary"):
            if not isinstance(item.get(key), str) or not item[key].strip():
                raise ValueError("empty translated description: " + asset)
        for side, fields in [
            ("applicability", ("preconditions", "supported", "excluded")),
            ("verification", ("scope", "known_limitations")),
        ]:
            if not isinstance(item.get(side), dict):
                raise ValueError("invalid translated section: " + asset + ":" + side)
            for key in fields:
                clauses = item[side].get(key)
                if not isinstance(clauses, list) or len(clauses) != len(doc[side][key]):
                    raise ValueError("translation dropped a contract clause: " + asset + ":" + key)
                if any(not isinstance(x, str) or not x.strip() for x in item[side][key]):
                    raise ValueError("empty translated contract clause: " + asset + ":" + key)
        if not isinstance(item.get("assumptions"), list) or len(item["assumptions"]) != len(
            doc["identity"]["assumptions"]
        ):
            raise ValueError("translation dropped a model assumption: " + asset)
        if any(not isinstance(x, str) or not x.strip() for x in item["assumptions"]):
            raise ValueError("empty translated assumption: " + asset)
        failures = item.get("failure_semantics")
        if not isinstance(failures, dict):
            raise ValueError("invalid translated failure semantics: " + asset)
        for key in ("invalid_input", "runtime_failure", "nonconvergence", "partial_results"):
            if not isinstance(failures.get(key), str) or not failures[key].strip():
                raise ValueError("missing failure semantics: " + asset)
        if (
            not isinstance(item["verification"].get("evidence_ceiling"), str)
            or not item["verification"]["evidence_ceiling"].strip()
        ):
            raise ValueError("missing translated evidence ceiling: " + asset)
        if not isinstance(item.get("example"), dict):
            raise ValueError("invalid translated example: " + asset)
        for key in ("description", "expected"):
            if not isinstance(item["example"].get(key), str) or not item["example"][key].strip():
                raise ValueError("missing translated example: " + asset)
        conflicts = item.get("source_conflicts", [])
        if not isinstance(conflicts, list) or any(
            not isinstance(x, str) or not x.strip() for x in conflicts
        ):
            raise ValueError("invalid source conflict annotation: " + asset)
    return records


def _discovery(document):
    """Return the optional reviewed discovery block.

    Unknown keys inside the block are ignored: they are not projected and they
    never change the derived view.  A non-object block is a contract error.
    """
    discovery = document.get("discovery")
    if discovery is None:
        return {}
    if not isinstance(discovery, dict):
        raise ValueError("discovery must be an object: " + document["asset_id"])
    return discovery


def _discovery_text(discovery, field):
    """Return one reviewed nonempty discovery text list, or ``None``."""
    values = discovery.get(field)
    if values is None:
        return None
    if (
        not isinstance(values, list)
        or not values
        or any(not isinstance(value, str) or not value.strip() for value in values)
    ):
        raise ValueError("invalid discovery." + field + " list")
    return [value.strip() for value in values]


def _discovery_value(discovery, field, fallback):
    """Return one reviewed discovery string, or the contract-derived fallback."""
    value = discovery.get(field)
    if value is None:
        return fallback.strip()
    if not isinstance(value, str) or not value.strip():
        raise ValueError("invalid discovery." + field)
    return value.strip()


def _device_scope(document, discovery):
    """Return ``(scope, source)``; absence always means ``unclassified``."""
    if "device_scope" not in discovery:
        return "unclassified", "default-unclassified"
    scope = discovery["device_scope"]
    if scope not in DEVICE_SCOPES:
        raise ValueError("invalid discovery.device_scope: " + document["asset_id"])
    return scope, "discovery"


def _capability_port(port):
    record = {
        "name": port["name"],
        "description": port["description"],
        "units": port["units"],
        "shape": port["shape"],
        "dtype": port["dtype"],
        "required": port.get("required", True),
        "constraints": port["constraints"],
    }
    if "default" in port:
        record["default"] = port["default"]
    return record


def capability_record(document):
    """Project one contract into the read-only capability view.

    Reviewed ``discovery`` text for capability/operation/model/geometry/
    boundary/device_scope wins when present; otherwise the view derives from
    ``title``/``identity``/``taxonomy``/ports/``verification``.  ``aliases``
    always come from the top-level contract field (single recall truth), and
    unknown discovery keys are ignored.  ``device_scope`` defaults to
    ``unclassified`` and is never inferred from a name.
    """
    asset = document["asset_id"]
    identity = document["identity"]
    verification = document["verification"]
    tests = list(verification["tests"])
    discovery = _discovery(document)
    capability_terms = _discovery_text(discovery, "capability")
    operation_terms = _discovery_text(discovery, "operation")
    scope, scope_source = _device_scope(document, discovery)
    return {
        "asset_id": asset,
        "symbol": document["public_api"]["python"]["symbol"],
        "public_api": document["public_api"],
        "capability": (
            capability_terms[0] if capability_terms else document["title"]["en"].strip()
        ),
        "capability_summary": (
            " — ".join(capability_terms[1:])
            if capability_terms and len(capability_terms) > 1
            else document["summary"]
        ),
        "summary": document["summary"],
        "title_zh": document["title"]["zh"],
        "operation": (operation_terms[0] if operation_terms else identity["relation"].strip()),
        "operation_direction": (
            " — ".join(operation_terms[1:])
            if operation_terms and len(operation_terms) > 1
            else identity["direction"].strip()
        ),
        "model": _discovery_value(discovery, "model", identity["model"]),
        "geometry": _discovery_value(discovery, "geometry", identity["geometry"]),
        "coordinates": identity["coordinates"].strip(),
        "boundary": _discovery_value(discovery, "boundary", identity["boundary"]),
        "device_scope": scope,
        "device_scope_source": scope_source,
        "aliases": list(document.get("aliases", [])),
        "taxonomy": list(document.get("taxonomy", [])),
        "ports": {
            "inputs": [_capability_port(port) for port in document["inputs"]],
            "outputs": [_capability_port(port) for port in document["outputs"]],
        },
        "contract_path": "catalog/examples/" + asset + ".json",
        "record_path": "records/" + asset + ".json",
        "docs_path": "/reference/generated/" + asset + ".html",
        "evidence": {
            "status": "bounded" if tests else "unvalidated",
            "scope": list(verification["scope"]),
            "tests": tests,
            "evidence_ceiling": verification["evidence_ceiling"],
            "known_limitations": list(verification["known_limitations"]),
        },
    }


def capability_search_text(document, translation=None, *, language="zh"):
    """Lexical recall text from the contract plus its bound reader layer.

    The Chinese site also recalls the Chinese reader prose and the Chinese
    title. The English site uses the English contract fields only (it has no
    English reader layer), so Chinese queries do not match English pages.
    The reviewed discovery fields are included except ``aliases``: the
    top-level contract ``aliases`` list remains the only recall alias source,
    so a stray ``discovery.aliases`` key cannot become a second truth.
    """
    if language not in LANGUAGES:
        raise ValueError("language must be one of: " + ", ".join(LANGUAGES))
    if language == "en" and translation is not None:
        raise ValueError("English recall text does not consume a reader layer")
    identity = document["identity"]
    discovery = document.get("discovery")
    reviewed = {}
    if isinstance(discovery, dict):
        reviewed = {
            field: discovery[field]
            for field in (
                "capability",
                "operation",
                "model",
                "geometry",
                "boundary",
                "device_scope",
            )
            if field in discovery
        }
    payload = [
        document["asset_id"],
        document["title"]["en"],
        document["summary"],
        identity["relation"],
        identity["direction"],
        identity["definition"],
        identity["model"],
        identity["geometry"],
        identity["coordinates"],
        identity["boundary"],
        identity["assumptions"],
        reviewed,
        document.get("aliases", []),
        document.get("taxonomy", []),
        [port["name"] for port in document["inputs"]],
        [port["name"] for port in document["outputs"]],
        [port["units"] for port in document["inputs"]],
        [port["units"] for port in document["outputs"]],
        document["applicability"],
        document["verification"],
    ]
    if language == "zh":
        payload.insert(2, document["title"]["zh"])
    if translation is not None:
        payload.append(
            [
                translation["summary"],
                translation["definition"],
                translation["model"],
                translation["boundary"],
            ]
        )
    return json.dumps(payload, ensure_ascii=False).lower()


def build_capability_index(documents, *, source_revision, translations=None, language="zh"):
    """Build the read-only capability index published inside a snapshot."""
    if language not in LANGUAGES:
        raise ValueError("language must be one of: " + ", ".join(LANGUAGES))
    records = sorted(
        (capability_record(document) for document in documents), key=lambda item: item["asset_id"]
    )
    ids = [record["asset_id"] for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate capability index asset_id")
    if translations is not None and set(translations) != set(ids):
        raise ValueError("capability index translations differ from documents")
    search_text = {}
    for document in documents:
        asset = document["asset_id"]
        search_text[asset] = capability_search_text(
            document, None if translations is None else translations[asset], language=language
        )
    return {
        "schema": CAPABILITY_INDEX_SCHEMA,
        "source_revision": source_revision,
        "asset_count": len(records),
        "derivation": {
            "capability": (
                "discovery.capability when present (first entry is the "
                "name, remaining text is the summary); otherwise "
                "title.en + summary"
            ),
            "operation": (
                "discovery.operation when present; otherwise identity.relation + identity.direction"
            ),
            "model": "discovery.model; otherwise identity.model",
            "geometry": (
                "discovery.geometry; otherwise identity.geometry; "
                "identity.coordinates is always included"
            ),
            "boundary": "discovery.boundary; otherwise identity.boundary",
            "device_scope": (
                "discovery.device_scope when present; otherwise "
                "unclassified, never inferred as generic"
            ),
            "aliases": (
                "contract top-level aliases only; a discovery.aliases key "
                "is ignored so aliases never become a second truth"
            ),
            "ports": "inputs + outputs",
            "evidence": (
                "verification.scope/tests/evidence_ceiling/"
                "known_limitations; status is bounded when "
                "verification.tests is non-empty, else unvalidated"
            ),
            "paths": (
                "contract_path is repository-relative; record_path is the "
                "served exact contract; docs_path is the snapshot web route"
            ),
        },
        "assets": records,
        "search_text": search_text,
    }


class PublicCatalog:
    """Read the public working tree without building or importing scientific code.

    This identity binds current public inputs, not a wheel or a past acceptance
    run. HOLD is read only to filter exposure; review evidence is never loaded.
    """

    def __init__(self, root, expected_digest=None):
        self.root = Path(root).resolve()
        self.input_digests = {}
        self.input_bytes = {}
        revision, dirty = self._git_identity()
        self._git_state = (revision, dirty)
        hold = self.root / "catalog/review/HOLD.json"
        self._read("catalog/review/HOLD.json")
        held = held_asset_ids(hold, read_bytes=self._captured)
        self._held_ids = held
        self.documents = {}
        for path in sorted((self.root / "catalog/examples").glob("*.json")):
            if path.stem in held:
                continue
            document = json.loads(self._read("catalog/examples/" + path.name))
            validate_document(document, location=path.name)
            if document["asset_id"] != path.stem:
                raise ValueError("contract filename differs from asset identity")
            self.documents[path.stem] = document
        if not self.documents:
            raise ValueError("source has no public asset documents")
        for document in self.documents.values():
            if any(
                item["asset_id"] not in self.documents
                for item in document["version"]["dependencies"]
            ):
                raise ValueError("public contract dependency is outside the public set")
        reader_paths = sorted((self.root / "tools/docs/zh").glob("*.json"))
        self._reader_paths = reader_paths
        for path in reader_paths:
            self._read("tools/docs/zh/" + path.name)
        documents = list(self.documents.values())
        self.translations = load_translations(
            self.root,
            self.root / "catalog/examples",
            documents,
            translation_paths=reader_paths,
            excluded_ids=held,
            read_bytes=self._captured,
        )
        self.index = build_capability_index(
            documents, source_revision=revision, translations=self.translations
        )
        # Snapshot web/record routes do not exist in a working-tree query.
        for record in self.index["assets"]:
            record.pop("record_path")
            record.pop("docs_path")
        validate_capability_index(self.index, expected_ids=self.documents)
        self.verify_unchanged()
        self.identity = {
            "source_revision": revision,
            "source_dirty": dirty,
            "source_inputs_sha256": sha(encode(self.input_digests)),
        }
        self.identity["source_identity_sha256"] = sha(encode(self.identity))
        if (
            expected_digest is not None
            and expected_digest != self.identity["source_identity_sha256"]
        ):
            raise ValueError("source differs from expected digest")

    def _git_identity(self):
        try:

            def git(*arguments):
                return subprocess.check_output(
                    ["git", *arguments],
                    cwd=self.root,
                    text=True,
                    stderr=subprocess.PIPE,
                    timeout=10,
                ).strip()

            if Path(git("rev-parse", "--show-toplevel")).resolve() != self.root:
                raise ValueError("source root must be the Git checkout root")
            revision = git("rev-parse", "HEAD")
            if re.fullmatch(r"[0-9a-f]{40}", revision) is None:
                raise ValueError("source HEAD must be a full Git commit id")
            return revision, bool(git("status", "--porcelain"))
        except (subprocess.SubprocessError, OSError) as error:
            raise ValueError("cannot read source Git identity") from error

    def _read(self, relative):
        path = self.root / relative
        for parent in (path, *path.parents):
            if parent == self.root.parent:
                break
            info = parent.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise ValueError("public source input uses a link/reparse point")
        if not path.resolve().is_relative_to(self.root):
            raise ValueError("public source input escapes root")
        data = path.read_bytes()
        self.input_digests[relative] = sha(data)
        self.input_bytes[relative] = data
        return data

    def _captured(self, path):
        """Only bytes already included in this query's input binding may be parsed."""
        return self.input_bytes[Path(path).relative_to(self.root).as_posix()]

    def verify_unchanged(self):
        """Reject drift in the captured public inputs, membership and Git state."""
        if (
            self._git_state != self._git_identity()
            or {
                path.stem
                for path in (self.root / "catalog/examples").glob("*.json")
                if path.stem not in self._held_ids
            }
            != set(self.documents)
            or sorted((self.root / "tools/docs/zh").glob("*.json")) != self._reader_paths
            or any(
                sha(self._read(path)) != digest
                for path, digest in tuple(self.input_digests.items())
            )
        ):
            raise ValueError("public source inputs changed during query")
