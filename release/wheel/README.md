# SciRel wheel version line

Each JSON file under `versions/` is an append-only record for one cumulative
SciRel wheel build. `CURRENT.json` is the current pointer and may be replaced
when a newer wheel is accepted. The artifact record contains its exact
SHA-256, byte size, source revision and selected capability closure.

The package layout is described by [`layout.json`](layout.json). Scientific
implementations are organized by domain package, and the wheel exposes those
domain paths directly. Legacy top-level module paths are intentionally absent;
callers must import from the owning domain package. Tests, provenance,
decomposition assets, and development tooling are outside the wheel intake.
