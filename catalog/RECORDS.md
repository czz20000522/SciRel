# Record locations, lifetime and cleanup

This policy applies to records produced by development, audits, outbound runs and
the human-review hold. A record's location follows its authority and lifetime,
not convenience.

## Durable, Git-tracked process records

| location | contents | lifetime | cleanup / change |
| --- | --- | --- | --- |
| `catalog/examples/` | admitted scientific contracts (single truth) | project lifetime | only by reviewed contract change; never delete to hide a failure |
| `catalog/review/HOLD.json` | human-review exposure hold | until owner decision | remove only after the review record and evidence are complete |
| `catalog/review/VERDICTS.json` | one admission verdict per asset | project lifetime | update with evidence; never silently drop an asset |
| `catalog/AUDIT.md`, `catalog/review/MERGE_CHAIN.md` | audit, merge and quarantine policy | project lifetime | controlled doc change |
| `scripts/review_gate.py`, tests | enforcement of the policy | project lifetime | change with the policy and its tests |

These are process truth, not scientific truth; the contract remains the single
scientific truth.

## Transient work products

| location | contents | lifetime | cleanup |
| --- | --- | --- | --- |
| `/tmp/audit-*`, `/tmp/probe_*`, `/tmp/d*-probes*` | raw audit reports, probes, CSVs | until the current audit wave is merged and its findings recorded | summarize into `catalog/AUDIT.md`/Notion; delete after merge or after the decision; do not cite `/tmp` from tracked files |
| `/tmp/outbound-*`, worker outputs | smoke/acceptance runs, candidate analysis | task lifetime | keep the acceptance result and failing evidence in `OUTBOUND.md`/Notion; delete the scratch tree when the task closes |
| `build/`, `*.egg-info/`, `__pycache__/` | build/cache | one command | delete after build/test; never commit |

Raw failure evidence is not deleted before the finding is recorded. If it may be
needed for human review, move the minimal evidence into `catalog/review/` or the
review archive first.

## Generated product artifacts

| location | contents | lifetime | cleanup |
| --- | --- | --- | --- |
| `dist/docs-*`, `dist/scirel-docs-*.tar.gz` | rendered documentation snapshots | latest verified snapshot(s) | rebuild at a named commit; delete superseded snapshots after the new one is verified |
| `dist/reference-truth/` | external oracle artifacts used by tests/reports | while referenced by a test, acceptance record or decision | keep the `TRUTH.json` provenance and generator script; delete only after the reference is retired and the test is updated |
| `dist/acceptance/` | acceptance verdicts | project lifetime or release cycle | archive with the release; never silently replace |

Generated artifacts are gitignored. They are reproducible products, not source
truth; a test must not depend on a hidden artifact without a documented
generation path and a skip/fixture rule.

## Notion and local skills

- Notion holds decisions, handoffs and review conclusions. It is durable until
  superseded; obsolete pages are archived rather than silently rewritten.
- `skills/` is local and excluded from Git. Changes to a skill must be backed up
  with the local skill source; do not put run outputs or truth artifacts inside a
  skill directory.

## Review candidates

Candidate code and contracts that are not admitted belong in the review tree
(`catalog/review/candidates/` or an external review tree), never in
`src/scirel/` or `catalog/examples/`. After merge, the staged copy is removed
only after the merged closure is green; the verdict record remains.

## Closing checklist

1. `git status --porcelain` is clean.
2. No tracked file cites `/tmp`, a private path or a hidden oracle.
3. The latest docs snapshot is built from the current commit; old snapshots are
   either removed or clearly marked superseded.
4. Every truth artifact has provenance and a reproducible generator.
5. Every held/candidate record has a verdict and, if unresolved, a named owner
   decision in `catalog/review/HUMAN_REVIEW_TODO.md`.
6. No held code or contract is installed/exposed; a guard is only transitional.
