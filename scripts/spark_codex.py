"""Sync a private model JSON over SSH and launch Codex with that configuration.

No credentials are placed in command arguments, printed, or written to Codex's
shared config/auth files. This is developer tooling, not part of the wheel.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import urlsplit

ENV_KEY = "SCIREL_MODEL_API_KEY"
DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / ".runtime/spark-model.local.json"


def load_config(path: Path) -> dict[str, str]:
    config = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("Expected a model configuration object")
    for name in ("key", "url", "model"):
        if not isinstance(config.get(name), str) or not config[name].strip():
            raise ValueError(f"Missing configuration field: {name}")
        if any(ord(c) < 32 for c in config[name]):
            raise ValueError(f"Control character in configuration field: {name}")
    url = urlsplit(config["url"])
    if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise ValueError("Provider URL must be HTTPS without credentials, query or fragment")
    return {"key": config["key"], "url": config["url"].rstrip("/"), "model": config["model"]}


def command(config: dict[str, str], executable: str, args: list[str]) -> tuple[list[str], dict[str, str]]:
    # Reject competing model/provider flags instead of silently choosing a value.
    for i, arg in enumerate(args):
        if arg in ("--model", "--profile") or arg.startswith(("-m", "-p", "--model=", "--profile=")):
            raise ValueError("Model/profile flags must come from the private JSON")
        override = args[i + 1] if arg in ("-c", "--config") and i + 1 < len(args) else ""
        if arg.startswith("--config="):
            override = arg.partition("=")[2]
        elif arg.startswith("-c") and arg != "-c":
            override = arg[2:]
        if override.split("=", 1)[0].strip() in ("model", "model_provider") or override.startswith("model_providers."):
            raise ValueError("Provider overrides must come from the private JSON")
    settings = {
        "model_provider": "scirel_runtime",
        "model_providers.scirel_runtime.name": "SciRel configured provider",
        "model_providers.scirel_runtime.base_url": config["url"],
        "model_providers.scirel_runtime.wire_api": "responses",
        "model_providers.scirel_runtime.env_key": ENV_KEY,
        "model_providers.scirel_runtime.requires_openai_auth": False,
    }
    argv = [executable, "--model", config["model"]]
    for key, value in settings.items():
        argv.extend(["--config", key + "=" + json.dumps(value)])
    env = os.environ.copy()
    env[ENV_KEY] = config["key"]
    return argv + args, env


INSTALL = r'''
import json, os, pathlib, sys, tempfile
payload = json.load(sys.stdin)
root = pathlib.Path.home()
config = root / '.config/scirel/spark-model.local.json'
script = root / '.local/share/scirel/spark_codex.py'
launcher = root / '.local/bin/scirel-codex'
items = [(config, json.dumps(payload['config'], indent=2) + '\n', 0o600),
         (script, payload['script'], 0o700),
         (launcher, '#!/bin/sh\nexec python3 "$HOME/.local/share/scirel/spark_codex.py" run --config "$HOME/.config/scirel/spark-model.local.json" -- "$@"\n', 0o700)]
for path, text, mode in items:
    if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != root):
        raise ValueError('Refusing a symlinked installation path')
    path.parent.mkdir(parents=True, exist_ok=True)
    if path == config: os.chmod(path.parent, 0o700)
    fd, name = tempfile.mkstemp(prefix='.scirel-', dir=path.parent)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(text)
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)
print(json.dumps({'installed': True, 'config': str(config), 'launcher': str(launcher),
                  'model': payload['config']['model'], 'key_printed': False}))
'''


def sync(config_path: Path, host: str) -> int:
    if not host or host.startswith("-") or any(c.isspace() for c in host):
        raise ValueError("Expected a single SSH host alias")
    config = load_config(config_path)
    payload = json.dumps({"config": config, "script": Path(__file__).read_text(encoding="utf-8")})
    encoded = base64.b64encode(INSTALL.encode()).decode("ascii")
    remote = "python3 -c 'import base64;exec(base64.b64decode(\"" + encoded + "\"))'"
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", host, remote],
        input=payload, text=True, capture_output=True, timeout=30,
    )
    # Remote failures may contain provider data; only return an exit status.
    if result.returncode:
        print(json.dumps({"installed": False, "ssh_exit": result.returncode}))
    else:
        print(result.stdout.replace(config["key"], "[REDACTED]"), end="")
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    transfer = sub.add_parser("sync", help="Install/update private config and launcher via SSH stdin")
    transfer.add_argument("--host", required=True)
    transfer.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    run = sub.add_parser("run", help="Run local Codex, reading credentials from JSON on every invocation")
    run.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    run.add_argument("args", nargs=argparse.REMAINDER)
    options = parser.parse_args()
    try:
        if options.action == "sync":
            return sync(options.config, options.host)
        args = options.args[1:] if options.args[:1] == ["--"] else options.args
        executable = shutil.which("codex")
        if not executable:
            fallback = Path.home() / ".local/bin/codex"
            if not fallback.is_file():
                raise FileNotFoundError("Codex executable unavailable")
            executable = str(fallback)
        argv, env = command(load_config(options.config), executable, args)
        os.execvpe(executable, argv, env)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(json.dumps({"ok": False, "error_type": type(error).__name__}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
