# Axisymmetric Picard update catalog closure

Status: development catalog documentation, not new scientific admission,
expert approval or public release. SciRel comparison base: `064d009`.
The current implementation and direct tests were compared with the frozen
historical Pleiades mapping, pending intake candidate and the existing
2026-09-25 flux-convention audit. SciRel and intake implementation text
matched. Intake r81-v1 remains `pending_unapproved`; the qualified D1
delivery root was read-only checked and contained zero entries, including
hidden entries. No qualified D1 input was consumed.

`update_axisymmetric_picard_flux` now has a current-version
`scirel.asset-document.v1` record. It forms raw cell currents from the first
R and Z spacings, projects them through a dense C-order Green matrix, then
relaxes the resulting flux with the previous flux. Previous cell currents
affect only the current-change diagnostic. New direct regressions cover a
selected nonuniform grid's first-spacing area rule and this diagnostic-only
previous-current behavior. No scientific source or public API changed.

The pending candidate document claimed a circular-filament Green comparison
in its verification scope, but the current direct tests do not contain that
experiment. The current record therefore makes no Green normalization claim.
It also does not resolve the vacuum-field records' `Wb` label against this
field chain's `Wb/rad` convention or authorize direct wiring. The selector
regression retains the reduced Hall graph and outer kinetic mirror Hall
composition as reverse consumers.

Catalog coverage is `partial: 78/114`; structured callable comparison with
the historical 52-entry ledger leaves 36 assets without exact documents.
The isolated worktree and main checkout each passed 79 affected tests, with
the latter using `pwsh ./scripts/check.ps1 -Mode affected -BaseRef 064d009`.
The reduced Hall graph's eight tests and the outer composition's two tests
also passed separately in the isolated worktree. Runtime signatures and
examples executed for all 78 documents. These checks establish selected
single-step arithmetic and failure paths, not arbitrary Green-response
normalization, containing-graph convergence, expert approval or distribution
licensing. No wheel or release was built.
