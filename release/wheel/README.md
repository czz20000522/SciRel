# SciRel wheel version line

The authoritative version is the `project.version` field in `pyproject.toml` at the Git commit being built. The canonical current receipt is [`../CURRENT.json`](../CURRENT.json); this directory is a compatibility surface only. Do not create a per-version wheel record. Git history, tags, and short release notes identify prior versions, while the generated wheel remains outside the source-of-truth path.


The canonical tuple contains the one wheel currently bound by this checkout.
Its artifact record contains the exact SHA-256, byte size, source revision and
selected capability closure. Older wheel files are not a required working-tree
asset: Git history is the version history, and a prior wheel must be restored
from its recorded digest or external evidence when it is needed for an audit.
Do not copy every historical wheel into the repository.

The package layout is described by [`layout.json`](layout.json). The current
wheel pointer also binds the compatible documentation record and exact
operator/task-graph/document counts. Scientific
implementations are organized by domain package, and the wheel exposes those
domain paths directly. Legacy top-level module paths are intentionally absent;
callers must import from the owning domain package. Tests, provenance,
decomposition assets, and development tooling are outside the wheel intake.
