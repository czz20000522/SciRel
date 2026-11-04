# Inversion and pressure leaf catalog closure

Status: development catalog documentation, not new scientific admission,
expert approval or public release. SciRel comparison base: `1d9bd17`.
Three public callables were compared individually with their current
implementations, direct tests, historical Pleiades mappings and pending
intake candidates. SciRel and intake source text matched after LF
normalization for each. Intake r81-v1 remains `pending_unapproved`;
the previously checked qualified D1 delivery root contained zero
entries. No qualified D1 input was consumed.

`reduce_observation_residuals` concatenates matched, sigma-normalized
flux-loop and Thomson-like channel differences in a fixed order, then
returns their squared norm. Unmatched Thomson-like channels are skipped.
`sample_latin_hypercube` makes seeded independent marginal strata
within selected parameter bounds; it does not infer a prior or solve
the inversion. `evaluate_tabulated_pressure` interpolates a supplied
one-dimensional isotropic or two-dimensional `(B,psi)` pressure table;
its branch marker does not certify physical isotropy. It does not
convert historical Wb and Wb/rad flux labels. No scientific source
module or public API changed.

Catalog coverage is `partial: 98/114`; structured public-callable
comparison with the 52-entry historical ledger finds 36 matches and
16 assets without exact documents. All 98 runtime signatures and
examples validated in the isolated worktree. The three direct
scientific test modules passed 10/10; isolated and main affected
checks each passed 14/14, with the main checkout using
`pwsh ./scripts/check.ps1 -Mode affected -BaseRef 1d9bd17`.

These checks do not establish measurement alignment, statistical
quality across RNG implementations, physical pressure laws, expert
approval or public distribution licensing. No wheel or release was
built.
