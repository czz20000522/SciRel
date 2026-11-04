# Flat-B holdout: final method did not enforce scientific preflight

This fresh, uncoached Claude Code `2.1.281` case used three independent
fictional operating points, each with the same B value. The source note
explicitly rejected a common plasma state, profile or chosen stability
criterion. The solver visibly read all four SciRel skill bodies, including
the final `scirel-solving` wording (`bac0e4...`), and used the unapproved
`0.1.0.dev39` wheel plus complete 126/126 catalog. The CLI model label was
`claude-fable-5`; the underlying model was not independently verified. No
call or token cap was imposed, and the shared host filesystem was not a
blind security boundary. The [manifest](manifests/2026-09-27-flat-b.json)
binds the inputs, raw trace and [first archive](../../../build/verification/flat-b-20260927/autonomous.tgz).

The final answer correctly declined an overall stability verdict and said
the mirror criterion was not evaluable. The CSV left mirror values blank.
Those are useful presentation choices, but the ordinary program still sent
each one-point state through the combined SciRel
`firehose-mirror-margins` callable via actual thin-adapter
`catalog.discover -> asset.read -> callable.invoke` operations. Its own
`run_evidence.json` says `mirror_branch_applicable=false` while recording
three invocations. The asset's documented one-sample zero-derivative
convention is numerical behavior, not permission to run an inapplicable
scientific branch. The answer also said all three independent invented
states "satisfy the firehose criterion," despite the source note saying no
physical criterion had been selected. The algebraic margins are correct;
the physical screening claim is not established.

After extraction outside the SciRel checkout, the installed development
wheel imported from `site-packages`, and the ordinary command reproduced
the first CSV byte-for-byte. Thus this is a real selection/preflight failure,
not a blank runtime or a unit-conversion defect. No project tests were
generated. The same failure survived multiple narrow method revisions and
two different input structures. Further generic admonitions in the skill
alone have not demonstrated a fix; a science-owner decision about separating
the pointwise relation from the set-dependent callable, or another
contract-level way to expose only applicable branches, is warranted before
claiming autonomous reliability. SciRel source, exact documents and
CodeFusion code were not changed by this evaluation.
