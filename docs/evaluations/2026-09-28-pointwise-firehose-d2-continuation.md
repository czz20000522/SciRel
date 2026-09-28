# Pointwise firehose D2 continuation

This is a development comparison record, not a second scientific contract or
an approval. The retained relation's scientific fields are in its single
`scirel.asset-document.v1` record.

Input: pending intake `647d5db`, with no qualified D1 bundle consumed.
Comparison baseline: SciRel `59bb916`. The designated qualified D1 root was
read-only checked and contained zero entries, including hidden entries.

First resumed action: inspect the new D2 process and the current Git states,
then create `codex/d2-pointwise-margin` from `59bb916`. The intake's direct
test was run before implementation and failed at import because this relation
was absent from the maintained source. No source computation was rerun.

Disposition: retain `scirel.diagnostics.pointwise-firehose-margin` as one
independent, pending development relation. The maintained combined
`firehose-mirror-margins` relation already exposes the same pointwise algebraic
field, but it also computes a B-sorted mirror derivative and sampled aggregate
flags. The new callable accepts single or duplicate-B samples without
requesting that branch and returns only the margin. The overlapping algebra is
tested for exact agreement on a common valid domain; a larger result is not
treated as an exact duplicate of the narrower callable. No upstream record
was changed, and no absorbed duplicate or extra review item was created.

The source of this proposal is SciRel's own outbound development evaluation,
not a migrated source oracle. Numeric and input-boundary tests establish only
the declared local formula and failure behavior. They do not establish a
general plasma stability criterion, expert approval, or public release.

Verification on the isolated checkout: the original direct test passed 10/10
after the implementation was added. The worktree-mode affected selector chose
that test, asset documentation and public surface checks; 36/36 passed without
falling back to the full suite. Runtime signatures and examples passed for all
118 exact documents. An initial `-BaseRef 59bb916` selection was empty because
the changes were uncommitted; the worktree-mode result is the applicable one.
