#!/usr/bin/env python3
"""Differential test: the local mirror must agree with SciRel's admission validator.

The mirror in `scripts/validate_final.py` exists only because a decomposition
worker may have no SciRel checkout. A mirror is useful exactly as far as it is
indistinguishable from the authority, so this test does not assert what the
rules "should" be. It builds adversarial FINAL directories and requires that the
authority and the mirror return the same status and the same error list.

If SciRel's contract changes, the authority moves and this test fails. That is
the point: the failure is the signal to re-mirror, not to edit the expectation.

Run:
  python skills/extraction/scientific-computation-asset-extraction/tests/test_validate_final.py

Skips (does not pass) when no SciRel checkout is reachable.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

MIRROR = (
    Path(__file__).resolve().parents[1] / "scripts" / "validate_final.py"
)

_CANDIDATES = [
    Path("/Users/tomczz/Projects/SciReL/scripts/validate_admission.py"),
]


def _find_authority() -> Path | None:
    for candidate in _CANDIDATES:
        if candidate.is_file():
            return candidate
    return None


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build(root: Path, *, schema="scirel.project-final", files_schema="scirel.final-files",
          control_members=None, payload=None, omit=(), extra_final=None,
          sort_members=True, root_file=True, project_id="proj") -> Path:
    """Build one adversarial FINAL directory and return it."""
    final_dir = root / "proj" / "decomposition" / "FINAL"
    final_dir.mkdir(parents=True, exist_ok=True)
    if payload is None:
        payload = {"d1/impl.py": b"x = 1\n", "licenses/NOTICE.txt": b"MIT\n"}
    license_references = [p for p in payload if p.startswith("licenses/")][:1]
    for rel, data in payload.items():
        target = final_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    final: dict = {
        "schema": schema,
        "project_id": project_id,
        "decomposition_scope": "bounded D1",
        "limitations": ["one relation only"],
        "claim_ceiling": "D1 evidence for one relation",
        "files": "FILES.json",
        "path_map": "PATH_MAP.json",
        "root_binding": "ROOT.sha256",
        "payload_files": len(payload) + 2,
        "payload_bytes": sum(len(v) for v in payload.values()) + 2,
        "evidence_policy": "planes recorded separately",
        "custody_note": "producer-held",
        "license": {"spdx": "MIT", "references": license_references},
    }
    if extra_final:
        final.update(extra_final)

    # FINAL.json and PATH_MAP.json are members; their own bytes feed the counts.
    path_map_bytes = b'{"aliases": {}}\n'
    placeholder_final = (json.dumps(final, indent=1) + "\n").encode()
    # Two-pass: fix points so payload_bytes matches the real emitted sizes.
    for _ in range(3):
        members = dict(payload)
        members["FINAL.json"] = placeholder_final
        members["PATH_MAP.json"] = path_map_bytes
        if control_members:
            for name in control_members:
                members.setdefault(name, b"{}\n")
        for name in omit:
            members.pop(name, None)
        final["payload_files"] = len(members)
        final["payload_bytes"] = sum(len(v) for v in members.values())
        placeholder_final = (json.dumps(final, indent=1) + "\n").encode()

    (final_dir / "FINAL.json").write_bytes(placeholder_final)
    (final_dir / "PATH_MAP.json").write_bytes(path_map_bytes)

    members = dict(payload)
    members["FINAL.json"] = placeholder_final
    members["PATH_MAP.json"] = path_map_bytes
    if control_members:
        for name in control_members:
            members.setdefault(name, b"{}\n")
    for name in omit:
        members.pop(name, None)

    entries = [{"path": p, "bytes": len(d), "sha256": _sha(d)}
               for p, d in members.items()]
    entries.sort(key=lambda e: e["path"])
    if not sort_members:
        entries.reverse()
    manifest = {"schema": files_schema, "files": entries}
    (final_dir / "FILES.json").write_bytes(
        (json.dumps(manifest, indent=1) + "\n").encode())

    if root_file:
        bound = [(n, (final_dir / n).read_bytes()) for n in
                 ("FINAL.json", "FILES.json", "PATH_MAP.json")]
        lines = [f"{_sha(data)}  {name}" for name, data in bound]
        digest = hashlib.sha256(("".join(l + "\n" for l in lines)).encode()).hexdigest()
        (final_dir / "ROOT.sha256").write_text(
            f"{digest}  ROOT.sha256\n" + "".join(l + "\n" for l in lines),
            encoding="utf-8")
    return final_dir


class MirrorAgreesWithAuthority(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        authority_path = _find_authority()
        if authority_path is None:
            raise unittest.SkipTest(
                "no SciRel checkout: cannot prove the mirror still matches")
        cls.authority = _load(authority_path, "authority_validate_admission")
        cls.mirror = _load(MIRROR, "mirror_validate_final")

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _both(self, final_dir: Path):
        expected = self.authority.validate(final_dir)
        actual = self.mirror.validate(final_dir)
        return expected, actual

    def _agree(self, final_dir: Path) -> dict:
        expected, actual = self._both(final_dir)
        self.assertEqual(
            expected["status"], actual["status"],
            f"status differs\n authority={expected['status']}\n mirror={actual['status']}\n"
            f" authority errors={expected['errors']}\n mirror errors={actual['errors']}")
        self.assertEqual(
            expected["errors"], actual["errors"],
            "error lists differ\n"
            f" authority only={sorted(set(expected['errors']) - set(actual['errors']))}\n"
            f" mirror only={sorted(set(actual['errors']) - set(expected['errors']))}")
        return expected

    # --- one case per rule, each the minimal witness -----------------------

    def test_valid_submission_passes_both(self):
        report = self._agree(build(self.tmp))
        self.assertEqual(report["status"], "PASS")

    def test_missing_root_binding_fails(self):
        # NOT_RUN is reserved for a missing FINAL.json/FILES.json/PATH_MAP.json.
        # A missing ROOT.sha256 is a failed check, not an unrun one.
        report = self._agree(build(self.tmp, root_file=False))
        self.assertEqual(report["status"], "FAIL")

    def test_missing_control_file_is_not_run(self):
        final_dir = build(self.tmp)
        (final_dir / "FILES.json").unlink()
        report = self._agree(final_dir)
        self.assertEqual(report["status"], "NOT_RUN")

    def test_edited_final_json_breaks_root_binding(self):
        final_dir = build(self.tmp)
        final = json.loads((final_dir / "FINAL.json").read_text())
        final["decomposition_scope"] = "full core"
        (final_dir / "FINAL.json").write_text(json.dumps(final, indent=1) + "\n")
        report = self._agree(final_dir)
        self.assertEqual(report["status"], "FAIL")

    def test_versioned_schema_is_rejected(self):
        report = self._agree(build(self.tmp, schema="scirel.project-final.v1"))
        self.assertEqual(report["status"], "FAIL")

    def test_versioned_files_schema_is_rejected(self):
        report = self._agree(build(self.tmp, files_schema="scirel.final-files.v1"))
        self.assertEqual(report["status"], "FAIL")

    def test_final_json_must_be_a_member(self):
        report = self._agree(build(self.tmp, omit=("FINAL.json",)))
        self.assertEqual(report["status"], "FAIL")

    def test_path_map_must_be_a_member(self):
        report = self._agree(build(self.tmp, omit=("PATH_MAP.json",)))
        self.assertEqual(report["status"], "FAIL")

    def test_control_files_cannot_be_members(self):
        for name in ("FILES.json", "ROOT.sha256"):
            with self.subTest(member=name):
                case = Path(tempfile.mkdtemp())
                self.addCleanup(shutil.rmtree, case, True)
                self._agree(build(case, control_members=(name,)))

    def test_unsorted_members_fail(self):
        # SciRel's standard makes ordering an error, unlike the earlier
        # decomposition-side draft which downgraded it to a warning.
        report = self._agree(build(self.tmp, sort_members=False))
        self.assertEqual(report["status"], "FAIL")

    def test_unknown_top_level_property_rejected(self):
        report = self._agree(build(self.tmp, extra_final={"capability_gain": {"x": 1}}))
        self.assertEqual(report["status"], "FAIL")

    def test_schema_version_property_rejected(self):
        report = self._agree(build(self.tmp, extra_final={"schema_version": "v1"}))
        self.assertEqual(report["status"], "FAIL")

    def test_payload_count_disagreement_detected(self):
        final_dir = build(self.tmp)
        final = json.loads((final_dir / "FINAL.json").read_text())
        final["payload_files"] = final["payload_files"] + 1
        (final_dir / "FINAL.json").write_text(json.dumps(final, indent=1) + "\n")
        self._agree(final_dir)

    def test_missing_payload_detected(self):
        final_dir = build(self.tmp)
        (final_dir / "d1" / "impl.py").unlink()
        self._agree(final_dir)

    def test_license_reference_must_be_member(self):
        report = self._agree(
            build(self.tmp, extra_final={"license": {"spdx": "MIT",
                                                     "references": ["licenses/X.txt"]}}))
        self.assertEqual(report["status"], "FAIL")

    def test_stage_evidence_must_be_member(self):
        report = self._agree(
            build(self.tmp, extra_final={"stage_evidence": {"d1": "d1/nope.json"}}))
        self.assertEqual(report["status"], "FAIL")

    def test_bad_project_id_rejected(self):
        report = self._agree(build(self.tmp, project_id="Proj_Name"))
        self.assertEqual(report["status"], "FAIL")

    def test_empty_limitations_rejected(self):
        report = self._agree(build(self.tmp, extra_final={"limitations": []}))
        self.assertEqual(report["status"], "FAIL")

    def test_emit_root_is_idempotent_and_agrees(self):
        final_dir = build(self.tmp, root_file=False)
        for _ in range(2):
            self.mirror.validate(final_dir, emit_root=True)
        first = (final_dir / "ROOT.sha256").read_bytes()
        self.mirror.validate(final_dir, emit_root=True)
        self.assertEqual(first, (final_dir / "ROOT.sha256").read_bytes())
        self.assertEqual(self._agree(final_dir)["status"], "PASS")


class MirrorDeclaresItsUpstream(unittest.TestCase):
    def test_mirror_names_the_commit_it_copies(self):
        mirror = _load(MIRROR, "mirror_meta")
        self.assertRegex(mirror.MIRRORED_UPSTREAM_COMMIT, r"^[0-9a-f]{7,40}$")

    def test_mirror_reports_the_commit_in_every_verdict(self):
        mirror = _load(MIRROR, "mirror_report")
        with tempfile.TemporaryDirectory() as tmp:
            report = mirror.validate(Path(tmp) / "absent")
        self.assertEqual(report["mirrored_upstream_commit"],
                         mirror.MIRRORED_UPSTREAM_COMMIT)


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    unittest.main(verbosity=2)
