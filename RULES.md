# Project meta-rules

The cross-project version of these rules lives in the global `agentic-development`
skill: `references/durable-rules-and-handoff.md` (durable placement, single truth,
generated-is-not-reviewed, information boundaries, handoff). This file is the
SciRel-specific overlay; project paths and schemas stay here.

This file records how SciRel work is **governed**, not just what one feature does.
It exists so a later human or agent can understand our preferences and continue
without replaying chat history. If a rule matters, it must live in a canonical
file or Notion decision record; chat-only knowledge is not durable.

## 1. Record first, then execute

- Durable decisions, boundaries, preferences, and handoff state must be written in
  the same task that created them.
- A later agent must be able to start from these files, not from a previous
  conversation.
- A change is not "done" until its rule/decision is recorded where the next owner
  will look.

## 2. Canonical placement

| Kind of knowledge | Canonical location |
| --- | --- |
| Contract truth, asset rules, conflict policy | `catalog/README.md`, `catalog/examples/` |
| Docs/API/bilingual/review/publish rules | `tools/docs/manual/README.md`, `tools/docs/` |
| Agent working conventions and required reading | `AGENTS.md` |
| Decomposition methodology, candidate/info/delivery boundaries | `skills/extraction/scientific-computation-asset-extraction/references/` |
| Decisions, rationale, history, ownership | Notion project/knowledge records |
| Generated publish artifacts | `dist/` (gitignored); never a source of truth |
| Runtime work, probes, intermediate containers | execution environment; disposable |

Do not create a second copy of the same rule in several places. Use one canonical
entry and link to it.

## 3. One truth, explicit choice

Every capability has one public contract truth. Implementation, tests, API pages,
user-guide links and the capability matrix are projections of that truth.

When contract and implementation disagree, choose one truth explicitly and record
the reason:

- scientific convention, fail-closed behavior or public promise -> fix implementation
  and add a regression test;
- stale/template-copied/incorrect contract -> fix contract and all derived text;
- never keep both truths alive, add compatibility aliases, or only patch a
  translation.

## 4. Review every delivered line

- Generated output is not reviewed output. Every API page, tutorial, contract
  fragment and published page is manually reviewed before release.
- "The validator passed" means structure is valid, not that the science or the
  language is correct.
- Check the chain: implementation -> contract -> direct tests -> example ->
  API page/user guide -> capability matrix.
- Prefer an explicit `NOT_RUN` / missing-evidence declaration over a fabricated
  result.

## 5. Bilingual is human work

- English contract fields are English; Chinese lives in the Chinese reader layer.
- Do not publish a Chinese page containing large English contract passages, or an
  English page retaining Chinese prose. Symbols, formulas and identifiers are the
  only acceptable shared tokens.
- Machine translation is a draft, not a deliverable; a human/agent review pass is
  required for both languages.

## 6. Correctness and competitive value

- Correctness is the product. An unverified capability has no reason to exist;
  users can use the mature source project instead.
- Coverage never justifies invented behavior, silent fallbacks or hidden failures.
- Prefer the longest available evidence chain: source parity, independent oracle,
  analytic invariant, boundary probe, or an explicit evidence gap.

## 7. Capability thinking, not LOC thinking

- Decompose and organize by scientific capability, operator/function or
  composition/task graph, never by lines of code, file count or directory shape.
- Decomposition is a proactive supply line; it does not wait for a demand map.
  Produce a complete candidate inventory, preserve uncertain candidates, and let
  the receiver choose.
- 10-20% is a receiver-side expectation, not an extraction quota or a LOC target.

## 8. Information boundaries

- Decomposition workers know the source, methodology, capability definitions and
  delivery format; not the receiver catalog/roadmap/acceptance decisions.
- Receiver workers know the self-contained package, contracts/tests/evidence and
  local acceptance rules; not source identity or decomposition history.
- Humans own the full chain. An optional global coordinator may assist the human
  but must not leak receiver context to workers or source identity to the receiver.
- Deliveries are self-contained; source checkout, private paths or receiver
  expectations must not become runtime dependencies.

## 9. Outbound delivery

- The single outbound entrypoint is `scirel-solving`; it has no version suffix and is overwritten in place, never forked into a parallel outbound skill.
- An old examination/sample is a source of physical requirements, not a package-version or acceptance baseline. The reference answer uses the current SciRel capability set plus explicit glue.
- Outbound workers see only public capability contracts/docs and the user request; not decomposition history, source identity, receiver roadmap or hidden oracle.
- Capability discovery metadata lives in the contract `discovery` block and is maintained by the SciRel intake owner. No schema version labels; iterate directly.
- Gaps are ordinary glue: explicit, testable, disclosed; final scientific acceptance belongs to the requester or a designated expert, not to the worker.

## 10. Storage and publication

- Mac checkout is the only source of truth. External project sources, runtime
  workspaces and generated release artifacts do not belong in Git.
- Generated HTML/API/matrix sites go to `dist/` (gitignored). E drive is not a
  required deployment location; deployment is a separate action.
- No secrets in the repository; credentials stay outside the source tree.
- Delivery may be a cloud Git repo, archive or object store; SciRel evaluates the
  self-contained result and correctness evidence.

## 11. Change process for meta-rules

When a new durable preference appears:

1. classify it using section 2;
2. write or update the canonical file/page;
3. link it from `AGENTS.md` required reading and the Notion handoff index;
4. commit tracked changes and move the baseline tag when appropriate;
5. tell the owner what changed and why, without turning the chat into the only copy.

This file is itself the meta-rule: **if it is valuable, it is written down where
the next owner will find it.**
