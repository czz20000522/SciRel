"""Official SDK subprocess probe for test_real_delivery; no repository imports."""

from __future__ import annotations

import asyncio
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

import httpx2
from mcp import Client, StdioServerParameters
from mcp.client.streamable_http import streamable_http_client


def main():
    config = json.load(sys.stdin)
    root = Path(config["root"])
    server = Path(config["server"])
    identity = config["identity"]
    assert server == root / "skills/scirel-capability-discovery/scripts/server.py"
    assert (
        hashlib.sha256(server.read_bytes()).hexdigest()
        == identity["files"][server.relative_to(root).as_posix()]["sha256"]
    )
    # Expected schemas come from the actual export, never repository scripts.
    sys.path.insert(0, str(server.parent))
    import consumer_tools

    assert Path(consumer_tools.__file__).parent == server.parent
    index = json.loads((root / "catalog/capability-index.json").read_bytes())
    expected_assets = {item["asset_id"] for item in index["assets"]}
    assert len(expected_assets) == identity["asset_count"] > 1
    pid_path = Path(config["work"]) / (config["transport"] + ".pid")
    # -I drops the script directory too. Restore only the exported sibling
    # directory, record the real child PID, and execute that exact server file.
    launcher = """
import os, runpy, sys
from pathlib import Path
entry = Path(sys.argv[1])
Path(sys.argv[2]).write_text(str(os.getpid()))
sys.path.insert(0, str(entry.parent))
sys.argv = [str(entry), *sys.argv[3:]]
runpy.run_path(str(entry), run_name='__main__')
"""
    args = ["-I", "-B", "-c", launcher, str(server), str(pid_path), "--root", str(root)]

    async def exercise(target):
        async with Client(target, read_timeout_seconds=10) as client:
            advertised = await client.list_tools()
            registry = [t.model_dump(by_alias=True, exclude_none=True) for t in advertised.tools]
            assert registry == consumer_tools.tools()
            assert {t["name"] for t in registry} == {
                "scirel_describe",
                "scirel_browse",
                "scirel_search",
                "scirel_get",
            }
            assert all(t["annotations"]["readOnlyHint"] is True for t in registry)
            discovery = client.session.discover_result
            assert discovery is not None

            async def call(name, arguments, outcome="ok", error=False):
                response = await client.call_tool("scirel_" + name, arguments)
                assert response.is_error is error, response
                data = response.structured_content
                assert data["outcome"] == outcome, data
                assert json.loads(response.content[0].text) == data
                if "snapshot_sha256" in data:
                    assert data["snapshot_sha256"] == identity["snapshot_sha256"]
                    assert data["wheel_sha256"] == identity["runtime"]["wheel_sha256"]
                    assert data["source_revision"] == identity["source_revision"]
                return data

            description = await call("describe", {})
            assert description["asset_count"] == len(expected_assets)
            pins = {
                "expected_snapshot_sha256": description["snapshot_sha256"],
                "expected_wheel_sha256": description["wheel_sha256"],
            }
            first = await call("browse", {**pins, "limit": 1}, "match")
            assert first["next_cursor"]
            second = await call(
                "browse", {**pins, "limit": 1, "cursor": first["next_cursor"]}, "match"
            )
            assert (
                first["result"]["items"][0]["asset_id"] != second["result"]["items"][0]["asset_id"]
            )
            # Traverse all real records and compare exact membership. Byte-bound
            # pages may contain fewer than limit; only the returned cursor advances.
            seen, cursors, cursor = [], set(), None
            for _ in range(len(expected_assets) + 1):
                query = {**pins, "limit": 100}
                if cursor:
                    query["cursor"] = cursor
                page = await call("browse", query, "match")
                items = [item["asset_id"] for item in page["result"]["items"]]
                assert items and page["returned"] == len(items)
                seen.extend(items)
                cursor = page["next_cursor"]
                if cursor is None:
                    break
                assert cursor not in cursors
                cursors.add(cursor)
            else:
                raise AssertionError("pagination did not terminate")
            assert len(seen) == len(set(seen)) == len(expected_assets)
            assert set(seen) == expected_assets
            asset = first["result"]["items"][0]["asset_id"]
            contract = root / "catalog/contracts" / (asset + ".json")
            document = await call("get", {**pins, "asset_id": asset})
            assert document["document"] == json.loads(contract.read_bytes())
            assert document["digests"] == {
                contract.relative_to(root).as_posix(): hashlib.sha256(
                    contract.read_bytes()
                ).hexdigest()
            }
            search = await call("search", {**pins, "q": asset, "limit": 100}, "match")
            assert asset in [item["asset_id"] for item in search["result"]["items"]]
            assert search["result"]["retrieval"]["scientific_applicability"] == "not_assessed"
            await call("search", {**pins, "q": "zzzzunfindable185zzzz"}, "no_candidates")
            await call("browse", {}, "invalid_request", True)
            for pin in pins:
                await call("browse", {**pins, pin: "0" * 64}, "identity_mismatch", True)
            await call("browse", {**pins, "limit": 0}, "invalid_request", True)
            await call("browse", {**pins, "cursor": "invalid"}, "invalid_request", True)
            await call(
                "browse",
                {**pins, "limit": 2, "cursor": first["next_cursor"]},
                "invalid_request",
                True,
            )
            await call("get", {**pins, "asset_id": "test.absent185"}, "unknown_asset", True)
            # Keep the same live session across drift and restoration: cached
            # metadata must not hide changed index/contract bytes.
            for path, name, arguments in (
                (
                    root / "catalog/capability-index.json",
                    "browse",
                    {**pins, "limit": 1, "cursor": first["next_cursor"]},
                ),
                (contract, "get", {**pins, "asset_id": asset}),
            ):
                original = path.read_bytes()
                try:
                    path.write_bytes(original + b"\n")
                    await call(name, arguments, "metadata_error", True)
                finally:
                    path.write_bytes(original)
                await call(name, arguments, "match" if name == "browse" else "ok")
            assert not any(
                n == "scirel" or n.startswith(("numpy", "scipy", "sphinx")) for n in sys.modules
            )
            return {
                "sdk_version": version("mcp"),
                "protocol_version": client.protocol_version,
                "supported_versions": discovery.supported_versions,
                "asset_count": len(seen),
                "snapshot_sha256": description["snapshot_sha256"],
                "wheel_sha256": description["wheel_sha256"],
            }

    async def exercise_http(url):
        async with httpx2.AsyncClient(
            trust_env=False, timeout=httpx2.Timeout(10.0, read=10.0)
        ) as http:
            return await exercise(streamable_http_client(url, http_client=http))

    if config["transport"] == "stdio":
        output = asyncio.run(
            exercise(StdioServerParameters(command=sys.executable, args=args, cwd=root))
        )
        pid = int(pid_path.read_text())
    else:
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        process = subprocess.Popen(
            [
                sys.executable,
                *args,
                "--transport",
                "streamable-http",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=root,
            stdout=subprocess.DEVNULL,
        )
        pid = process.pid
        forced = False
        try:
            deadline = time.monotonic() + 10
            while True:
                assert process.poll() is None, "packaged HTTP server exited before readiness"
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                        break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError("packaged HTTP server did not become ready") from None
                    time.sleep(0.05)
            output = asyncio.run(exercise_http(f"http://127.0.0.1:{port}/mcp"))
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                forced = True
                process.kill()
                process.wait(timeout=5)
        assert not forced, "HTTP server required a forced kill"
        # Uvicorn re-raises the received shutdown signal after graceful cleanup.
        # On Windows Popen.terminate uses TerminateProcess with exit status 1.
        expected_exit = -signal.SIGTERM if os.name == "posix" else 1
        assert process.returncode in (0, expected_exit), process.returncode
        output["server_exit_code"] = process.returncode
    # POSIX can probe the actual SDK-launched PID. On Windows HTTP is reaped by
    # Popen.wait, and stdio completion is owned by the SDK's awaited context.
    if os.name == "posix":
        deadline = time.monotonic() + 5
        while True:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                break
            assert time.monotonic() < deadline, "server process survived transport shutdown"
            time.sleep(0.05)
    assert not list(root.rglob("__pycache__"))
    output["server_exited"] = True
    print(json.dumps(output, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
