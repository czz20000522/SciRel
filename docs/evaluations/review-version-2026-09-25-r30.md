# SciRel free-boundary required-port successor r30

Status: development review pending, not expert-approved, trusted, or publicly released. The qualified L1 delivery root remains empty. There is no trusted baseline, so the first expert review still covers all 68 public assets; r29 is only a development comparison.

## Change and scientific scope

`solve_free_boundary_anisotropic_picard` now checks its required ports before indexing `r_grid` and `z_grid`. Omitting either grid key previously raised `KeyError` despite the graph's required-port `ValueError` contract. A regression first reproduced that failure and then passed after moving the existing port check. Valid-input computation, numerical defaults, dependencies, and public signature are unchanged. The graph's exact document now states the observed failure behavior. Earlier ordering of errors for an input that is simultaneously missing a required port and has an invalid grid can change; this is the intended validation precedence.

The implementation version advances from `0.1.0.dev15` to `0.1.0.dev16` so two different source trees do not share a wheel identity. All 68 exact documents carry the new implementation version; only `scirel.equilibrium.free-boundary-anisotropic-picard` has a non-mechanical document change. The legacy admitted-only ledger and its source digests remain untouched. Its reproduction tests read the pinned `dev15` Git source and still require every historical digest to match; current public callable availability is checked separately. Those old admission labels do not approve this version.

The development catalog still covers 68/68 documented public assets. This count says nothing about full scientific capability, source-project closure, licensing, or expert approval. The domain drafts and dated integration records remain review material with their documented evidence ceilings. No new qualified L1 or source parity is claimed. Expert review must consider the changed graph's failure contract and affected consumers; unchanged scientific evidence may be reused only where its assumptions and implementation remain valid.

## Verification and limits

The graph regression failed before the fix with `KeyError: 'r_grid'`, then its direct file passed 16 tests. `scripts/check.ps1 -Mode affected` ran the full suite because `pyproject.toml` changed: 902 passed, 43 skipped. All 68 exact documents passed source-runtime signature and executable-example validation. The internal dev16 wheel was installed with `--no-index --no-deps` in a venv and imported from its site-packages under `python -I`; a valid graph ran and missing `r_grid`/`z_grid` each raised `ValueError`. All 68 documents also passed installed-runtime signature/example validation, and the source-free user acceptance's three tasks passed. The venv reused host scientific dependencies and does not prove a clean offline dependency wheelhouse or any project's complete source reproduction.

The frozen manifest binds the exact commit, wheel, catalog, documents, review materials, and test evidence. The prior r29 snapshot remains unchanged. Version-level expert promotion, source licenses, and public release are still outstanding.
