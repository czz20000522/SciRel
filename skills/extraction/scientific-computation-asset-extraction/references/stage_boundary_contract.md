# Scientific skill group stage boundary contract

SciRel owns its scientific methods and assets. A host such as CodeFusion, Claude Code, or Codex may load and run
those methods, but host job state does not replace SciRel scientific state and the host does not own Operator,
TaskGraph, catalog, review, or release semantics.

This reference supplies the self-contained D1 boundary in the deployed extraction bundle. In a full SciRel
checkout, later candidate/release authority lives in `docs/requirements/scirel-workflow.md`,
`docs/design/scirel-workflow.md` and `skills/integration/`; user-facing execution lives in `skills/usage/`.
Those repository-only resources are not part of the five-skill D1 bundle. D1 hands off exact artifacts and claims
to the receiving owner without loading unavailable later-stage instructions or duplicating them here.

## D1 responsibility

D1 produces a saved, source-traceable L1 bundle: complete source coverage, source-shaped callable code,
TaskGraph structure, necessary scientific anchors, tests, evidence, provenance, and explicit gaps. The result remains a
re-runnable source candidate. It is not a normalized SciRel identity, an expert decision, a maintained-baseline
change, a catalog entry, or a release.

Keep the output source-shaped and preserve its lineage. Do not perform cross-project equivalence decisions,
deduplication, public namespace design, expert approval, or release work. Those exclusions do not make imperfect L1
material invalid by definition: record recoverable format, test, evidence, and scientific gaps with enough detail for
a later SciRel workflow to diagnose them without rewriting the saved source record.

## Information and immutable handoff

A scientific contract is not a mandatory Markdown file. D1 anchors it in delivered code, YAML, docstrings,
function/module comments and existing scientific records. Reference recoverable facts there; state necessary
nonrecoverable units, assumptions, conventions, provenance and validation basis once. Minimal information does
not mean creating another draft Markdown page. Code comments may retain source references, implementation
conventions and internal details that do not belong in the formal human-facing document.

D2 reads the delivered D1 snapshot without changing it. Deduplication decisions, corrections, annotations and
new tests belong to D2's derived candidate, with a link to the original. The same read-only input rule applies
between every stage. A successor never rewrites a prior stage's frozen claims or evidence.

Formal operator/TaskGraph documents are generated only after D2 comparison, deduplication, correction and
assembly stabilize the retained new/changed code, before final review freeze. Duplicate or covered assets need
attributable disposition and scientific comparison evidence, not duplicate formal pages. Partial overlap alone
is not equivalence. Human approval decides the final frozen review version; intermediate Agent review and
internal development assembly do not require a human decision and do not imply publication.

## Scientific and mechanical completion

D1 must establish complete declared-source coverage, source-shaped implementations, and numerical comparisons
with the source before a qualified complete L1 `full_freeze`. Later stages may not be able to access or run the
source, so unresolved scientific coverage or validation remains a named D1 gap. An incomplete candidate may be
saved under an explicit claim ceiling but must not be reported as qualified complete material.

When an executed result still has independently verifiable code, inputs, outputs, and runtime-relevant
conditions, fix a path, assertion, format, or digest binding with a traceable supplemental record instead of
repeating the calculation. Check an assertion against source semantics and independent results; do not relax
its scientific tolerance to fit the candidate. Preserve the old failure and its evidence, without fabricating
a historical seal. Rerun only the affected cheap comparison or gate; repeat scientific execution when its
correspondence is missing or the inputs, executable science, or environment materially changed.

For a `bounded_delivery` handoff, D1 requires an independent read-only Agent review of the exact source-derived
census, selected bundle assets, reassembly evidence, and deferred capability register. The review receipt is a finite
exit decision for that batch, not expert approval and not a `full_freeze` claim. The producing coordinator must not
also act as this reviewer, and the reviewer must not edit the bundle or progress snapshot.
An authorized separate visible thread is a valid independent context. Use `reviewer_role=independent_agent` for it;
the validator also accepts the historical `independent_subagent` role without rewriting old receipts. Record actual
reviewer identity, harness/model version and reviewed scope in the existing review evidence. The role string alone
does not prove independence. A workflow does not require a hidden child agent, and caller delegation rules apply.

## Preserved material and gaps

- Preserve the source snapshot, raw evidence, L1 bundle, and their content identities.
- Record a gap with the observed fact, evidence, affected claim, next evidence or decision needed, and the condition
  that would make it actionable.
- Keep tool failures distinct from scientific defects. Missing evidence caps the claim and need not block unrelated
  candidates.
- Do not infer approval, publication, or maintained-baseline membership from a candidate, test result, review note,
  staged digest, or `full_freeze` signal.

Use content digests where bytes cross an artifact or evidence boundary. Do not create per-edit digest ceremony for
ordinary working notes.

## TaskGraph and evidence constraints

Ordinary TaskGraphs are dependency-closed DAGs. Feedback or iteration must declare state, update order, stopping
condition, finite bound, and nonconvergence behavior. Source parity proves source behavior only; it does not prove
general physical correctness. Project examples may support a bounded claim but do not automatically become global
rules for every SciRel asset.

For a D1 full-freeze claim, the extraction gate derives `closure_signal.kind=full_freeze` from the declared scope,
resolved asset references, package tests, source-free execution, and required reassembly evidence. This signal means
only that the declared L1 extraction bundle is internally frozen; it does not approve or publish the candidates. A
model must not set it merely because its own run completed.
