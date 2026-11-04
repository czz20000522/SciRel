"""Focused tests for the optional stateless SciRel HTTP wrapper."""

from __future__ import annotations

import hashlib
import http.client
import json
from threading import Thread

from scirel_plugin import DEFAULT_MAX_BODY_BYTES, create_server
from scirel_workflow import CandidatePackage, SciRelWorkflow


def _digest(body: bytes) -> str:
    return "sha256:" + hashlib.sha256(body).hexdigest()


def _post(server, value: dict[str, object]) -> tuple[int, dict[str, object]]:
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port)
    connection.request(
        "POST",
        "/scirel/body",
        body=json.dumps(value).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    response = connection.getresponse()
    result = json.loads(response.read().decode("utf-8"))
    connection.close()
    return response.status, result


def test_default_listener_limit_matches_codefusion_body_wire():
    assert DEFAULT_MAX_BODY_BYTES == 16 * 1024 * 1024


def test_default_listener_accepts_utf8_wire_above_the_old_one_mib_limit():
    source = json.dumps(
        {
            "assets": [],
            "automated_checks": [],
            "fixture_padding": "x" * (1024 * 1024),
        },
        separators=(",", ":"),
    ).encode("utf-8")
    server = create_server()
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, payload = _post(
            server,
            {
                "operation": "scirel.import_l1",
                "artifact_ref": "cf://l1/large-wire",
                "artifact_digest": _digest(source),
                "media_type": "application/json",
                "body": source.decode("utf-8"),
            },
        )
        assert status == 200
        assert payload["artifact_kind"] == "scirel.candidate-package.dev"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_http_listener_executes_l1_wire_and_returns_domain_artifact():
    source = b'{"assets": [], "automated_checks": [{"name": "replay", "status": "passed"}]}'
    server = create_server()
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        request = {
            "operation": "scirel.import_l1",
            "artifact_ref": "cf://l1/http-fixture",
            "artifact_digest": _digest(source),
            "media_type": "application/json",
            "body": source.decode("utf-8"),
        }
        status, payload = _post(server, request)

        assert status == 200
        assert payload["artifact_kind"] == "scirel.candidate-package.dev"
        assert payload["body_digest"] == _digest(payload["body"].encode("utf-8"))
        candidate = json.loads(payload["body"])
        assert candidate["source_artifact_ref"] == "cf://l1/http-fixture"
        assert set(payload) == {
            "operation", "artifact_kind", "media_type", "body", "body_digest"
        }

        candidate_body = payload["body"].encode("utf-8")
        check_status, check = _post(
            server,
            {
                "operation": "scirel.automated_check",
                "artifact_ref": "cf://candidate/http-fixture",
                "artifact_digest": _digest(candidate_body),
                "media_type": "application/json",
                "body": payload["body"],
            }
        )
        assert check_status == 200
        assert check["artifact_kind"] == "scirel.automated-check-result.dev"
        assert check["body_digest"] == _digest(check["body"].encode("utf-8"))
        result = json.loads(check["body"])
        assert result["next_action"] == "ready"
        assert result["gaps"] == []
        assert set(check) == {
            "operation", "artifact_kind", "media_type", "body", "body_digest"
        }
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_http_listener_returns_retry_result_for_imperfect_l1_candidate():
    source = json.dumps(
        {
            "assets": [
                {
                    "l1_asset_id": "sample:operator:missing-test",
                    "asset_path": "operators/missing-test",
                    "direct_test_path": None,
                }
            ],
            "automated_checks": [
                {
                    "name": "direct_test_mapping",
                    "status": "failed",
                    "issues": [{"automation": "discover_or_generate_test"}],
                }
            ],
        },
        separators=(",", ":"),
    ).encode("utf-8")
    server = create_server()
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, imported = _post(
            server,
            {
                "operation": "scirel.import_l1",
                "artifact_ref": "cf://l1/imperfect",
                "artifact_digest": _digest(source),
                "media_type": "application/json",
                "body": source.decode("utf-8"),
            },
        )
        assert status == 200
        candidate_body = imported["body"].encode("utf-8")

        check_status, checked = _post(
            server,
            {
                "operation": "scirel.automated_check",
                "artifact_ref": "cf://candidate/imperfect",
                "artifact_digest": _digest(candidate_body),
                "media_type": "application/json",
                "body": imported["body"],
            },
        )

        assert check_status == 200
        assert checked["artifact_kind"] == "scirel.automated-check-result.dev"
        assert checked["body_digest"] == _digest(checked["body"].encode("utf-8"))
        result = json.loads(checked["body"])
        assert result["status"] == "failed"
        assert result["next_action"] == "retry"
        assert result["gaps"] == [
            "missing_direct_test_mapping:sample:operator:missing-test"
        ]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_http_listener_exposes_single_state_review_list_and_open_wire():
    candidate = CandidatePackage.from_l1(
        {
            "assets": [],
            "automated_checks": [{"name": "replay", "status": "passed"}],
        },
        source_artifact_ref="cf://l1/review-http",
        source_digest="sha256:source",
        run_id="run-review-http",
    )
    workflow = SciRelWorkflow(candidate)
    workflow.create_draft(
        draft_id="draft-review-http",
        assets=[{"asset_id": "scirel.incomplete.review-http"}],
    )
    workflow.submit_for_review()
    state = json.dumps(
        workflow.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    state_digest = _digest(state)
    base = {
        "artifact_ref": "cf://state/review-http",
        "artifact_digest": state_digest,
        "media_type": "application/json",
        "body": state.decode("utf-8"),
    }

    server = create_server()
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        list_status, listed = _post(
            server, {"operation": "scirel.review.list_items", **base}
        )
        assert list_status == 200
        index = json.loads(listed["body"])
        assert listed["artifact_kind"] == "codefusion.plugin-view-index.v1"
        item = index["items"][0]
        action = next(
            action
            for action in item["actions"]
            if action["payload"]["outcome"] == "needs_evidence"
        )

        open_status, opened = _post(
            server,
            {
                "operation": "scirel.review.open_item",
                **base,
                "operation_payload": {
                    "item_ref": item["item_ref"],
                    "revision": item["revision"],
                },
            },
        )
        assert open_status == 200
        assert opened["artifact_kind"] == "scirel.review-item-detail.dev"
        snapshot = json.loads(opened["body"])
        assert snapshot["current_artifact"]["digest"] == state_digest
        assert snapshot["item"]["status"] == "review_pending"

        action_status, action_result = _post(
            server,
            {
                "operation": "plugin.review.action",
                **base,
                "operation_payload": {
                    "item_ref": item["item_ref"],
                    "revision": item["revision"],
                    "extension_ref": "scirel.review",
                    "action_ref": action["action_ref"],
                    "reviewer": {"actor_ref": "actor://reviewer/http"},
                    "payload": action["payload"],
                },
            },
        )
        assert action_status == 200
        assert action_result["artifact_kind"] == (
            "codefusion.plugin-reviewer-successor-snapshot.v1"
        )
        successor = json.loads(action_result["body"])
        assert successor["predecessor"]["digest"] == state_digest
        assert successor["payload"]["status"] == "needs_evidence"
        assert successor["payload"]["decision"]["reviewer_actor_ref"] == (
            "actor://reviewer/http"
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_http_listener_rejects_wrong_route_and_oversized_body():
    server = create_server(max_body_bytes=8)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port)
        connection.request("POST", "/wrong", body=b"{}", headers={"Content-Type": "application/json"})
        response = connection.getresponse()
        assert response.status == 404
        response.read()
        connection.close()

        connection = http.client.HTTPConnection("127.0.0.1", server.server_port)
        connection.request("POST", "/scirel/body", body=b"123456789", headers={"Content-Type": "application/json"})
        response = connection.getresponse()
        assert response.status == 413
        response.read()
        connection.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_http_listener_wraps_server_socket_with_supplied_ssl_context():
    class RecordingContext:
        def __init__(self):
            self.calls = []

        def wrap_socket(self, socket, *, server_side):
            self.calls.append((socket, server_side))
            return socket

    context = RecordingContext()
    server = create_server(ssl_context=context)
    try:
        assert context.calls == [(server.socket, True)]
    finally:
        server.server_close()
