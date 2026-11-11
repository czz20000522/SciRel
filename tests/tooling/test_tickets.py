"""Ticket front matter follows the format and the state machine of supply-pipeline.md section 7."""

import importlib.util
import json
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("tickets", ROOT / "scripts/tickets.py")
tickets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tickets)

BODY = """
## 要决定的问题
用哪种拟合？
## 选项
A 或 B。
## 各方意见
双方都没有决定性证据。
## 不决定的后果
写进局限性。
"""


def _ticket(**overrides):
    fields = {
        "id": "T-2026-0001",
        "kind": "physics-dispute",
        "status": "open",
        "assets": "[scirel.collisions.example]",
        "default_applied": "写进局限性，不改实现",
        "options": "[A, B]",
        "reviewers_required": "2",
        "decisions": "[]",
        "resolution": "null",
        "applied": "null",
    }
    fields.update(overrides)
    front = "\n".join(f"{k}: {v}" for k, v in fields.items() if v is not None)
    return f"---\n{front}\n---\n{BODY}"


def test_open_ticket_passes():
    assert tickets.check(_ticket()) == []


def test_comments_and_quotes_are_parsed():
    data, _ = tickets.parse(_ticket(kind="physics-dispute   # 物理分歧", default_applied='"a # b"'))
    assert data["kind"] == "physics-dispute"
    assert data["default_applied"] == "a # b"


def test_missing_and_unknown_keys_are_reported():
    errors = tickets.check(_ticket(applied=None, extra="x"))
    assert "missing key: applied" in errors
    assert "unknown key: extra" in errors


def test_open_ticket_cannot_carry_a_resolution():
    assert any("no resolution" in e for e in tickets.check(_ticket(resolution="A")))


def test_decided_needs_enough_agreeing_reviewers():
    one = '[{"reviewer": "r1", "option": "A", "rationale": "x", "date": "2026-11-11"}]'
    errors = tickets.check(_ticket(status="decided", resolution="A", decisions=one))
    assert any("needs 2 distinct agreeing" in e for e in errors)


def test_split_human_decisions_cannot_be_decided():
    split = (
        '[{"reviewer": "r1", "option": "A", "rationale": "x", "date": "d"},'
        ' {"reviewer": "r2", "option": "A", "rationale": "x", "date": "d"},'
        ' {"reviewer": "r3", "option": "B", "rationale": "y", "date": "d"}]'
    )
    errors = tickets.check(_ticket(status="decided", resolution="A", decisions=split))
    assert any("reviewers disagree" in e for e in errors)


def test_applied_needs_a_reference():
    two = (
        '[{"reviewer": "r1", "option": "A", "rationale": "x", "date": "d"},'
        ' {"reviewer": "r2", "option": "A", "rationale": "x", "date": "d"}]'
    )
    assert tickets.check(_ticket(status="decided", resolution="A", decisions=two)) == []
    errors = tickets.check(_ticket(status="applied", resolution="A", decisions=two))
    assert any("by, ref and date" in e for e in errors)
    done = '{"by": "agent", "ref": "abc123", "date": "2026-11-12"}'
    assert (
        tickets.check(_ticket(status="applied", resolution="A", decisions=two, applied=done)) == []
    )


def test_body_sections_are_required():
    text = _ticket().replace("## 各方意见", "## 其他")
    assert any("各方意见" in e for e in tickets.check(text))


def test_package_tickets_must_still_be_open():
    two = (
        '[{"reviewer": "r1", "option": "A", "rationale": "x", "date": "d"},'
        ' {"reviewer": "r2", "option": "A", "rationale": "x", "date": "d"}]'
    )
    text = _ticket(status="decided", resolution="A", decisions=two)
    assert any(
        "status must be one of open" in e for e in tickets.check(text, allowed_statuses=("open",))
    )


def test_one_reviewer_cannot_vote_twice_or_anonymously():
    twice = (
        '[{"reviewer": "r1", "option": "A", "rationale": "x", "date": "d"},'
        ' {"reviewer": "r1", "option": "A", "rationale": "x", "date": "d"}]'
    )
    errors = tickets.check(_ticket(status="decided", resolution="A", decisions=twice))
    assert any("only one decision" in e for e in errors)
    assert any("needs 2 distinct agreeing" in e for e in errors)
    anonymous = '[{"option": "A"}, {"option": "A"}]'
    errors = tickets.check(_ticket(status="decided", resolution="A", decisions=anonymous))
    assert any("must name its reviewer" in e for e in errors)


TWO = (
    '[{"reviewer": "r1", "option": "A", "rationale": "x", "date": "d"},'
    ' {"reviewer": "r2", "option": "A", "rationale": "x", "date": "d"}]'
)
DONE = '{"by": "agent", "ref": "abc123", "date": "2026-11-12"}'
OPEN = _ticket()
DECIDED = _ticket(status="decided", resolution="A", decisions=TWO)
APPLIED = _ticket(status="applied", resolution="A", decisions=TWO, applied=DONE)
CLOSED = _ticket(status="closed", resolution="A", decisions=TWO, applied=DONE)


def test_the_four_legal_steps_pass():
    for old, new in ((OPEN, DECIDED), (DECIDED, APPLIED), (APPLIED, CLOSED), (OPEN, OPEN)):
        assert tickets.check_transition(old, new) == []


def test_skipping_or_reversing_a_step_is_rejected():
    for old, new, step in (
        (OPEN, APPLIED, "open to applied"),
        (DECIDED, OPEN, "decided to open"),
        (CLOSED, APPLIED, "closed to applied"),
    ):
        assert tickets.check_transition(old, new) == [f"status may not change from {step}"]


def test_agent_fields_are_frozen_once_decided():
    errors = tickets.check_transition(OPEN, _ticket(**{**_fields_of(DECIDED), "options": "[A, C]"}))
    assert "options may not change when the status goes from open to decided" in errors
    edited = APPLIED.replace("写进局限性。", "改成别的。")
    assert tickets.check_transition(DECIDED, edited) == [
        "the body may not change when the status goes from decided to applied"
    ]


def test_the_platform_does_not_write_applied_and_the_agent_does_not_write_the_verdict():
    applied_early = _ticket(status="decided", resolution="A", decisions=TWO, applied=DONE)
    assert any("applied may not change" in e for e in tickets.check_transition(OPEN, applied_early))
    revoted = _ticket(
        status="applied",
        resolution="A",
        decisions=TWO.replace('"rationale": "x"', '"rationale": "edited"', 1),
        applied=DONE,
    )
    assert "decisions may not change when the status goes from decided to applied" in (
        tickets.check_transition(DECIDED, revoted)
    )


def test_recorded_decisions_are_append_only_while_open():
    one = '[{"reviewer": "r1", "option": "A", "rationale": "x", "date": "d"}]'
    other = '[{"reviewer": "r9", "option": "B", "rationale": "y", "date": "d"}]'
    assert tickets.check_transition(_ticket(decisions=one), _ticket(decisions=TWO)) == []
    assert tickets.check_transition(_ticket(decisions=one), _ticket(decisions=other)) == [
        "recorded decisions may only be appended to, never edited or removed"
    ]


def test_new_tickets_start_open_and_tickets_are_never_deleted():
    assert tickets.check_transition(None, OPEN) == []
    assert tickets.check_transition(None, DECIDED)[0] == "a new ticket starts open, not decided"
    assert tickets.check_transition(OPEN, None) == ["tickets are never deleted; close them instead"]


def _fields_of(text):
    data, _ = tickets.parse(text)
    return {k: json.dumps(v, ensure_ascii=False) for k, v in data.items()}


def _write(root, kind, name, text):
    path = root / kind / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_directory_file_name_and_id_must_agree(tmp_path):
    good = _write(tmp_path, "physics-dispute", "T-2026-0001.md", OPEN)
    assert tickets.check_files([good]) == []
    wrong_dir = _write(tmp_path, "scope", "T-2026-0001.md", OPEN)
    wrong_name = _write(tmp_path, "physics-dispute", "T-2026-0002.md", OPEN)
    errors = tickets.check_files([good, wrong_dir, wrong_name])
    assert any("does not match its directory scope/" in e for e in errors)
    assert any("does not match its file name T-2026-0002.md" in e for e in errors)
    assert any("is already used by" in e for e in errors)


def _git(cwd, *args):
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


def test_base_revision_catches_a_skipped_step_and_a_deleted_ticket(tmp_path):
    root = tmp_path / "tickets"
    kept = _write(root, "physics-dispute", "T-2026-0001.md", OPEN)
    gone = _write(root, "physics-dispute", "T-2026-0002.md", OPEN.replace("0001", "0002"))
    _git(tmp_path, "init", "--quiet")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "--quiet", "-m", "base")
    kept.write_text(APPLIED, encoding="utf-8")
    gone.unlink()

    errors = tickets.check_files([kept], base=tickets.base_texts(root, "HEAD"))
    assert any("status may not change from open to applied" in e for e in errors)
    assert any("T-2026-0002.md: tickets are never deleted" in e for e in errors)
    with pytest.raises(tickets.TicketError, match="is not a revision"):
        tickets.base_texts(root, "no-such-rev")


def test_repository_tickets_follow_the_format():
    files = sorted(p for p in (ROOT / "tickets").rglob("*.md") if p.name != "README.md")
    assert files, "tickets/ holds at least the first real ticket"
    assert tickets.check_files(files) == []
