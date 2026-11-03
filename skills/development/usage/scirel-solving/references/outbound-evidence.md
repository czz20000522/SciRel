# Keep a concise handover record

When handing a result to another team, platform or acceptance reviewer, keep one `OUTBOUND.md` beside the task outputs. A one-off answer does not need this extra file. Reuse the application's existing run evidence rather than duplicating it.

Record enough to replay and assess the claim:

| part | content |
| --- | --- |
| E1 requirement | supplied request, material interpretation/assumptions, user criteria and unresolved facts |
| E2 selection | actual queries and inspected scope, selected public IDs, runtime/input identity and contract-fit reasons |
| E3 execution | supplementary methods and their limits, real commands, saved outputs, checks/failures, replay and `NOT_RUN` |

Use a [physical plan](graph-model.md) only if it explains coupled dependencies. Supplementary work follows [these checks](glue-gap.md); the record need not repeat their instructions.

Lead the human answer with the result and limitation. Keep implementation detail in evidence. Numerical statements come from saved outputs; when the [delivery helper](delivery-tool.md) generates an answer, preserve those checked statements and support any added physical interpretation separately. A check of one draft does not verify a different final message.

For an existing application, preserve supplied inputs and baseline, reuse public SciRel APIs for covered steps, and deliver the authorized patch, runnable entrypoint and relevant application/runtime test results. The handover belongs in the task workspace; it does not modify SciRel's scientific contracts or qualify the library generally.
