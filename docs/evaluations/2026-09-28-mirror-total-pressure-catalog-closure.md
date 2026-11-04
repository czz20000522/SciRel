# Mirror total-pressure catalog closure

Status: development catalog documentation, not new scientific admission,
expert approval or public release. SciRel comparison base: `9146b42`.
The historical Pleiades descriptor and migration mapping, the pending intake
development candidate, the current implementation and direct SciRel tests were
compared independently. Intake r81-v1 remains `pending_unapproved`; no
qualified D1 delivery was consumed for this change.

The existing `assemble_mirror_total_pressure` callable now has an independent
`scirel.asset-document.v1` record. It adds the supplied isotropic electron
pressure to both converted, broadcast ion pressure components and returns a
shallow terminal-state dict. The original ion-moment dict is retained by
identity. Density, relative charge residual and optional potential are
passed through without numeric or coordinate validation. The saved historical
descriptor claims stronger density broadcasting and validation; those claims
do not describe the maintained callable. A direct regression now protects
this difference, including nonfinite and negative pass-through values. No
scientific source module or public API changed.

The canonical asset participates in the mirror quasineutral graph and its two
outer graph reverse dependencies. The graph still has one undocumented
kinetic-moment leaf, and its iterative state and failure propagation need
separate review. Current catalog coverage is `partial: 71/114`; a structured
callable comparison with the 52-entry historical ledger leaves 43 ledger
assets without exact documents.

`pwsh ./scripts/check.ps1 -Mode affected -BaseRef 9146b42` passed 74 tests
in both the isolated worktree and main checkout. That gate validated the 71
exact documents against runtime signatures and executable examples. These
checks establish the stated current SciRel behavior on tested inputs, not
physical alignment of supplied states, arbitrary overflow behavior, expert
approval, qualified D1 provenance or distribution licensing. No wheel or
release was built.
