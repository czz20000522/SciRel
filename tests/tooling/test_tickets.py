"""Ticket front matter follows the format and the state machine of supply-pipeline.md section 7."""

import importlib.util
from pathlib import Path

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
    assert any("needs 2 agreeing" in e for e in errors)


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
