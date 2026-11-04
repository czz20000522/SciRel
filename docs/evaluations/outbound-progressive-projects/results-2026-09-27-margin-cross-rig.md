# Cross-rig margin applicability: uncoached Claude follow-up

This is a synthetic, source-free **development** evaluation, not physical
approval. A fresh Claude Code `2.1.281` session, with observed reads of four
owner skill bodies, used the unapproved SciRel `0.1.0.dev39` wheel and the
complete 126/126 development catalog. The CLI model label was
`claude-fable-5`; the underlying model was not independently confirmed.
There was no call or token cap. The examiner and solver shared a host
filesystem without OS-level read isolation. The [manifest](manifests/2026-09-27-margin-cross-rig.json)
binds the exact requests, data, method, raw traces and stage archives.

The first request supplied four mT/kPa rows and explicitly deferred how
they were collected. Claude found `firehose-mirror-margins`, converted units,
and produced a runnable TSV-to-CSV tool. Its numbers matched the installed
wheel, but the report called two rows mirror-criterion failures and described
all four as satisfying the firehose condition. The exact document requires
the caller to establish the B-value sampling and interpretation criterion;
the initial request did not. These are formula values, not established
physical screens. A caveat that general stability was not proved did not
repair this applicability gap.

The second user message supplied a separate origin table: each row came from
a different apparatus and operating point. Without reviewer coaching, Claude
withdrew the cross-rig mirror flags, produced a firehose-only CSV/report and
kept the first CSV/report byte-identical. In an extracted copy outside the
SciRel checkout, 13 project tests passed and the ordinary command reproduced
the stage-2 CSV from the installed wheel. This is useful correction after
new evidence, but its code still invokes the combined SciRel callable on the
full cross-rig set and merely hides the mirror output. A negative probe with
two independent rigs sharing the same B returned `ValueError` from the
supposedly inapplicable mirror derivative, so even the pointwise delivery
failed. The report's claim that mirror was "not evaluated" is false.

The implementation also treats one matching apparatus/operating-point label
as sufficient to enable pooled differentiation, although that metadata alone
cannot establish a common equilibrium p(B) profile or selected criterion.
The pointwise algebraic firehose value is reproducible, but the stage-2 claim
that it satisfies a physical necessary condition remains unsupported without
the criterion's model premise. The issue is a scientific preflight decision,
not a unit conversion error. This case uses direct SciRel Python calls, not
CodeFusion or the thin adapter. It is not evidence of first-pass autonomous
scientific reliability or a trusted/public v1.
