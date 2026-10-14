# SciRel wheel version line

Each JSON file under `versions/` is an append-only record for one cumulative
SciRel wheel build. `CURRENT.json` is the current pointer and may be replaced
when a newer wheel is accepted. The artifact itself may live in `dist/` during
development or in external release storage; the record must contain its exact
SHA-256 and source revision.
