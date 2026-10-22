# SciRel current handoff

This is the entry file for a new agent taking over the current development state.
Read it after `AGENTS.md`/`RULES.md`, not instead of them.

## Where the project is

- branch/tag: `baseline-self-contained-20261020`; last recorded commit at the
  time of this handoff: `916272b7`.
- exposed capability count: **247**.
- human-review hold: **1**
  - `scirel.inference.direct-anisotropic-inversion`
  - reason: source-graph assembly parity, but the Pleiades FINAL payload lacks the
    exact admitted direct-inversion graph artifact; its axisymmetric dependency
    is already released.
  - required action: restore/bind the exact graph artifact, rerun direct
    composition + physical-closure, then rebind.
- `dist/` contains the last zh/en docs snapshots and `dist/acceptance/` including
  the outbound S1-S6 report and wheel-exposure proof. These are generated
  artifacts, not source truth; rebuild into a new output directory (the build
  refuses to overwrite an existing snapshot).
- retained verdict evidence: `catalog/review/evidence/` (audit CSVs and source
  audit reports; no `/tmp` references remain in `VERDICTS.json`).
- review harness: `python scripts/review_harness.py --check` (sets
  `SCIREL_REVIEW_HOLD=1`, mounts the candidate tree and runs the held contract's
  direct tests).

## Required entry points

1. `AGENTS.md` — structure, testing, docs, information boundaries.
2. `RULES.md` — meta-rules: record first, one truth, review, bilingual,
   capability thinking, storage.
3. `catalog/README.md` — contract truth and asset rules.
4. `catalog/AUDIT.md` — audit protocol, ingestion prevention, source-based
   decisions, outbound policy.
5. `catalog/review/MERGE_CHAIN.md` — candidate quarantine and dependency-closure
   merge rules.
6. `catalog/RECORDS.md` — record locations, lifetime, cleanup.
7. `catalog/review/HOLD.json` / `VERDICTS.json` / `HUMAN_REVIEW_TODO.md` —
   current exposure state and pending decision.
8. `skills/development/usage/scirel-solving/` — the only outbound skill.

## What changed in this session (the parts a new agent must not re-derive)

### Audit and exposure

- Every catalog asset has a verdict in `catalog/review/VERDICTS.json`; the gate is
  `scripts/review_gate.py --check`.
- Held code/contracts live in the tracked review tree:
  `catalog/review/candidates/src/...` and `catalog/review/examples/`.
  They are not installed and are not in the public catalog.
- `scripts/check_wheel_exposure.py` proves held modules/symbols and candidate
  paths are absent from the built wheel.
- A composition with a held member is itself held; do not expose a partially
  wired chain.

### Source-based decisions

- Source is the oracle for **source fidelity**, not for choosing between two
  physically defensible models.
- `source parity` / `source conflict` / `source defect` / `no source` / `API
  policy` are distinct outcomes. A source-defect repair must be labelled as a
  repair, never as parity.
- Source identity and commit hashes stay in review evidence, not in the public
  contract body.

### Outbound

- The outbound skill is `scirel-solving`; no version suffix.
- A missing/held/near-miss capability is an in-flow **gap**, not a user handoff.
  Mark it, try a public formula/exposed composition, verify and continue; if
  impossible, state the concrete missing input and deliver a bounded result.
- Do not import a held implementation as a shortcut.
- Classify failures: user data/domain invalid, interface/contract mismatch,
  numerical/applicability limit, implementation failure. Do not call an interface
  mismatch "invalid physics".
- Formal outbound scenarios S1/S2/S3/S4/S5/S6 are recorded in
  `dist/acceptance/outbound-s1-s6.md` and the skill references. S1/S5 match
  Pleiades truth; S6 is pass-with-limits.

## Current verification commands

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/validate_asset_documents.py catalog/examples --check-runtime --execute-examples
.venv/bin/python scripts/review_gate.py --check
.venv/bin/python scripts/check_wheel_exposure.py --output dist/acceptance/wheel-exposure.json
.venv/bin/python scripts/scirel_docs.py build --output dist/docs-20261021
.venv/bin/python scripts/scirel_docs.py build --language en --output dist/docs-en-20261021
```

At the last handoff: full `3209 passed / 3 skipped / 1 xfailed`; validator 247
PASS; review gate PASS; wheel proof PASS; git clean.

## Do not repeat these mistakes

- Do not accept "all tests pass" as scientific correctness.
- Do not use a shared test file as asset-specific evidence without attribution.
- Do not treat a held capability as a reason to ask the user for a human review or
  to decompose the library; fill the gap or give a concrete blocker.
- Do not keep a held implementation in the installed package and call an import
  guard containment.
- Do not claim source parity for a source-defect repair.
- Do not put source identity/commit hashes into the public contract body.
- Do not use a tolerance below the recorded roundoff/conditioning floor.

## Known open work

- direct-inversion artifact restoration (the only held item).
- optional evidence hygiene outside the exposed set (P0/hold records).
- optional complex-case replication track; recorded in `catalog/AUDIT.md`, not a
  release gate.
