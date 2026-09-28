# Mirror ambipolar potential catalog closure

Status: development catalog documentation, not new scientific admission,
expert approval or public release. SciRel comparison base: `4db8ef7`.
The current implementation, direct scientific tests and frozen historical
ledger entry were independently compared with the pending intake candidate.
The SciRel and intake implementation text matched. Intake r81-v1 remains
`pending_unapproved`; the qualified D1 delivery root was read-only checked
and contained zero entries, including hidden entries. No qualified D1 input
was consumed.

`solve_mirror_ambipolar_potential` now has a SciRel-versioned
`scirel.asset-document.v1` exact record. Evaluate mode computes the
prescribed-potential one-way fluxes and returns `converged=True` even for an
unbalanced current; it performs no solve. Solve mode requires paired positive
or paired zero reference densities per surface, ignores `phi_plug_v`, expands
the initial bracket at most eight times and applies bounded bisection.
Joint-vacuum solve surfaces retain the reference potential; an all-vacuum
call still reports one iteration. The stopping test uses the preceding
midpoint's log-current ratio and the next midpoint's potential change, so
the final reported relative residual is diagnostic, not that test. Failed
bracketing or iteration exhaustion returns no result mapping.

New direct regressions cover all-vacuum iteration reporting, ignored
solve-mode `phi_plug_v`, and unbalanced evaluate-mode `converged=True`.
The selector regression confirms that a change to the leaf selects the grid
mirror graph and its outer composition. No scientific source or public API
changed.

Catalog coverage is `partial: 75/114`; a structured callable comparison
with the 52-entry historical ledger leaves 39 assets without exact documents.
All 75 documents passed runtime-signature and executable-example validation.
`pwsh ./scripts/check.ps1 -Mode affected -BaseRef 4db8ef7` passed 91 tests
in the main checkout, after the same 91 tests passed in the isolated worktree.
The grid mirror graph's eight direct tests and its outer composition's two
tests also passed in the isolated worktree. These checks establish selected
numerical behavior and failure paths, not all pitch-integral branches,
arbitrary-root uniqueness, physical model validity, expert approval or
distribution licensing. No wheel or release was built.
