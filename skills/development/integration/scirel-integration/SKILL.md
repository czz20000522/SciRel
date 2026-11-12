---
name: scirel-integration
description: Merge-line method for bringing an extraction package into SciRel — validate the package, judge each manifest verdict, file decided tickets, answer every open review comment, and never rewrite the extractor's work.
---

# SciRel merge line

The merge line consumes an **extraction package** and decides whether it enters
the library. It judges and reviews; it does not re-extract, does not repair a
defective package, and does not fill in an expert decision. The rules behind
this method are in [`docs/maintainer/supply-pipeline.md`](../../../../docs/maintainer/supply-pipeline.md)
sections 5–7; read them once before using this skill.

Read the shared operating contract once if this task mode has not loaded it:
[the shared operating contract](../../references/scirel-development-core.md).

## Inputs

The only input is an extraction package. Its format is defined in
`supply-pipeline.md` section 5: `manifest.md` (one row per capability: contract
id, domain, layer, family, and one of the four comparison verdicts),
`disposition.md` (one line per un-extracted part and why), `tickets/`, and the
candidate assets with their contracts and tests.

Run `scripts/validate_extraction_package.py` first. A format failure is a
package defect: return the defect list to the extraction line and let a new
extraction agent continue from the archived package. Do not repair frozen
controls in place, do not rerun valid science for a packaging defect, and do not
edit the package to make the validator pass.

## Judge each verdict

Walk `manifest.md` row by row. Each verdict is one of four values and each has
one required action:

| Verdict | Action |
| --- | --- |
| Already present | Bind to the existing asset; add a new method only if the row carries independent evidence for it |
| New method of an existing family | Add the method to that family; the family keeps one entry and one selector convention |
| Genuinely new | New asset with its own contract, direct tests and boundary matrix |
| Not accepted | Record the reason; the capability does not enter the library |

A **physics correction** is a B-level change: two independent reviewers must
agree on the evidence. Graded review is the maintainer's authority
(see #165), so a complete evidence chain is enough to proceed — do not wait for a
separate human sign-off, and do not widen a tolerance to make a row pass. When
the evidence cannot settle the question, file a ticket (below) and apply the safe
default: keep the implementation, record the doubt in the contract's limitations.

## Tickets

Move the package's `tickets/` into this repository as `tickets/<kind>/<id>.md`
(M3), preserving frontmatter. The repository is public: a ticket must not name
the source project, a private path or unpublished material; point at the
package's `private/` instead. Status lives only in frontmatter, and only the
owner of a field writes it — the review platform writes `decisions`,
`resolution` and the `decided` transition; agents write everything else.

Before starting any work, list tickets whose status is `decided` and handle them
first. A ticket must be readable on its own page: an expert decides from that
file without opening anything else.

## Answer every open review comment before merging

A review comment is part of the evidence chain, so an unanswered comment means
the review did not happen. Before merging, list every comment on the pull
request — `gh pr view <n> --comments` and
`gh api repos/{owner}/{repo}/pulls/<n>/comments` — and require a written response
for each of these:

- every Codex finding while `has_unresolved_findings` is true;
- every human or agent review marked as a required change.

A response is either "changed in `<sha>`" or "not changing, because …". A
reasoned refusal may merge, but it needs a tracking issue. The merge record (the
final "reviewed and merged" comment) lists the disposition of every such comment.
Skipping this step is not a shortcut; it is the failure mode where a merged
branch keeps contradicting its own contract.

## Assemble and verify

- Rebase the patch onto the latest `main`. Mechanical conflicts (a path or a name
  that already moved) are the merge line's job.
- Run the validator and the complete check with `scripts/dev.py check`; add the
  hidden tests when the case maps to one. Release evidence is that run, and it
  must carry the `EXCLUSIVE` line.
- Preserve ports, units, axes, state ownership, order, convergence, exceptions,
  native/build/ABI and dependency closure. Keep task-specific glue explicit and
  testable; do not hide a reusable scientific relation in glue and do not replace
  a declared failure with a warning.
- When several candidates merge together, open a separate integration worktree
  and re-verify the combination there; do not merge on the strength of
  per-branch runs alone.
- Reuse evidence by exact identity and rerun the affected reverse dependencies
  after a change.

Close with a merge record that names the accepted assets, the retained glue, the
affected tests, the failed and `NOT_RUN` rows, and the disposition of every review
comment. A diff without that record is still a candidate.

## What this skill cannot do

It cannot grant human approval, rights or release; it cannot decide a C-level
question; and it cannot accept a capability the maintainer froze. A freeze is a
scope decision, not a merge-line judgement.
