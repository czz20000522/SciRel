"""Small, stateless HTTP wrapper for the SciRel body-wire contract.

Authentication, endpoint admission, request budgeting, retries and platform
audit remain CodeFusion responsibilities.  This listener only converts one
UTF-8 JSON request into one SciRel domain response.
"""

from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import ssl
from typing import Any, Mapping

from .adapter import execute_body_import_wire


DEFAULT_PATH = "/scirel/body"
DEFAULT_MAX_BODY_BYTES = 1024 * 1024


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def make_handler(
    *, path: str = DEFAULT_PATH, max_body_bytes: int = DEFAULT_MAX_BODY_BYTES
) -> type[BaseHTTPRequestHandler]:
    """Create a handler bound to one route and a bounded request body."""

    if not isinstance(path, str) or not path.startswith("/"):
        raise ValueError("path must start with '/'")
    if not isinstance(max_body_bytes, int) or max_body_bytes <= 0:
        raise ValueError("max_body_bytes must be positive")

    class SciRelBodyHandler(BaseHTTPRequestHandler):
        server_version = "SciRelBody/0.1"

        def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
            if self.path != path:
                self._send_error(HTTPStatus.NOT_FOUND, "unknown endpoint")
                return
            if not self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() == "application/json":
                self._send_error(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "content type must be application/json")
                return
            length_header = self.headers.get("Content-Length")
            try:
                length = int(length_header) if length_header is not None else -1
            except ValueError:
                length = -1
            if length < 0:
                self._send_error(HTTPStatus.LENGTH_REQUIRED, "content length is required")
                return
            if length > max_body_bytes:
                self._send_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "request body is too large")
                return
            raw = self.rfile.read(length)
            if len(raw) != length:
                self._send_error(HTTPStatus.BAD_REQUEST, "request body is incomplete")
                return
            try:
                payload = json.loads(raw.decode("utf-8"))
                if not isinstance(payload, Mapping):
                    raise ValueError("request body must be a JSON object")
                response = execute_body_import_wire(payload)
                self._send_json(HTTPStatus.OK, response)
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
                self._send_error(HTTPStatus.BAD_REQUEST, str(error))

        def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
            self._send_error(HTTPStatus.NOT_FOUND, "unknown endpoint")

        def log_message(self, format: str, *args: object) -> None:
            # Do not log request bodies or platform credentials.
            return

        def _send_json(self, status: HTTPStatus, value: Mapping[str, Any]) -> None:
            body = _json_bytes(value)
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_error(self, status: HTTPStatus, message: str) -> None:
            self._send_json(status, {"error": "invalid_request", "message": message})

    return SciRelBodyHandler


def create_server(
    host: str = "127.0.0.1",
    port: int = 0,
    *,
    path: str = DEFAULT_PATH,
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
    ssl_context: ssl.SSLContext | None = None,
) -> ThreadingHTTPServer:
    """Create a server; the caller owns its lifecycle and shutdown."""

    server = ThreadingHTTPServer(
        (host, port), make_handler(path=path, max_body_bytes=max_body_bytes)
    )
    if ssl_context is not None:
        server.socket = ssl_context.wrap_socket(server.socket, server_side=True)
    return server


def create_server_ssl_context(
    *, certfile: str, keyfile: str, password: str | None = None
) -> ssl.SSLContext:
    """Create the server-side TLS context used by the optional HTTPS listener."""

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile=certfile, keyfile=keyfile, password=password)
    return context


__all__ = [
    "DEFAULT_MAX_BODY_BYTES",
    "DEFAULT_PATH",
    "create_server",
    "create_server_ssl_context",
    "make_handler",
]
