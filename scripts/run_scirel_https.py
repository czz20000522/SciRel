"""Run the stateless SciRel body-wire listener over HTTPS."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scirel_plugin import (  # noqa: E402
    DEFAULT_MAX_BODY_BYTES,
    DEFAULT_PATH,
    create_server,
    create_server_ssl_context,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--certfile", type=Path, required=True)
    parser.add_argument("--keyfile", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8443)
    parser.add_argument("--path", default=DEFAULT_PATH)
    parser.add_argument("--max-body-bytes", type=int, default=DEFAULT_MAX_BODY_BYTES)
    args = parser.parse_args()

    context = create_server_ssl_context(
        certfile=str(args.certfile.resolve()), keyfile=str(args.keyfile.resolve())
    )
    server = create_server(
        args.host,
        args.port,
        path=args.path,
        max_body_bytes=args.max_body_bytes,
        ssl_context=context,
    )
    print(
        json.dumps(
            {
                "endpoint": f"https://{args.host}:{server.server_port}{args.path}",
                "transport": "https",
                "wire_contract": "artifact_ref+artifact_digest",
            },
            separators=(",", ":"),
        ),
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
