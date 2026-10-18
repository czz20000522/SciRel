# Project credentials

This directory is the canonical location for private credentials used by the
SciRel development project. Credential files are ignored by Git; keep the
README and the project structure, and place each active provider configuration
here rather than under a personal home directory, WSL distribution, or shared
Codex configuration. This Mac checkout is the authority. Home Windows, Docker,
and WSL may receive a read-only runtime projection, but they must never become
the source of truth.

The local Codex bridge reads the canonical provider configuration from:

```text
.scirel/credentials/scirel-company-codex-provider.json
```

The canonical JSON uses `base_url`, `model`, and `api_key` fields, together
with non-secret provider metadata. Do not print or commit its contents. When a
run is moved to another host, create a one-way, read-only projection from this
Mac file into that host's project/runtime root and retain the receipt; edits to
the projection must never flow back into this checkout.
