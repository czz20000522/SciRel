# JSON snapshot forward test: bounded explanation, invalid invocation

A fresh Claude Code `2.1.281` session received two independent, invented
pressure/B snapshots in JSON. The source note explicitly said no equilibrium
model, pressure profile or physical-stability criterion had been selected.
This was a new structure after the preceding table/cohort experiments. The
solver visibly read the pinned `scirel-solving` body (`4509fe...`) and used
the unapproved SciRel `0.1.0.dev39` wheel with the complete 126/126
development catalog. The CLI model label was `claude-fable-5`, with no
independent confirmation of the underlying model. No call or token cap was
set; examiner and solver still shared a host filesystem. The
[manifest](manifests/2026-09-27-state-json.json) binds inputs, method, raw
trace, output and the [uncoached archive](../../../build/verification/state-json-20260927/autonomous.tgz).

The user-facing answer correctly refused to call either state stable and
described the pointwise firehose values (`+618.3` and `+1023.5 kPa`) as
arithmetic observations. The runnable project used the actual thin-adapter
`catalog.discover -> asset.read -> callable.invoke` path, and an extracted
copy outside SciRel reproduced the delivered CSV byte-for-byte from the
installed wheel. This is evidence that the final method revision improved
the *wording* of the physical conclusion on an unseen input format.

It did not pass the execution preflight. The code invokes the combined
`firehose-mirror-margins` asset separately on each one-sample state although
the exact document's physical applicability premises are absent. Its
documented one-sample branch sets the mirror derivative to zero. The CSV
still records positive numeric mirror margins and `mirror_sample_flag=True`
for both states, merely adding `mirror_criterion_evaluated=False`; the report
also displays those values "for transparency." A caveat cannot turn an
inapplicable set-dependent branch into an applicable SciRel check. This is a
real counterexample to counting restrained final prose as reliable asset
selection. There are no generated project tests for this case.

The skill was subsequently narrowed to state that hiding **or disclaiming**
numeric flags and a documented degenerate-input convention do not establish
a missing physical premise. That final wording has not yet had an independent
forward test. No SciRel science implementation or exact document changed,
and this case is not CodeFusion integration, expert approval or trusted v1.
