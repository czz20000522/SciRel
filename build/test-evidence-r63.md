# r63 test evidence — KN1DPy transport-step family

Base r62 `965028c` (113 assets, dev35) -> r63 `0.1.0.dev37` (116 assets).
Three new operators in `scirel.kinetic`:
1. `neutral-upwind-transport-coefficients` — assembles forward/backward
   trapezoidal transport coefficients (Ak/Bk/Fk/Ck/Dk/Gk) from x and vx
   only (no velocity-space axes; r62 cross-mesh domain does not apply).
2. `neutral-generation-propagation` — bidirectional propagation for
   first_flight and scattered generations. Bk is the scattered-branch
   forward source coefficient; Fk is the first-flight forward source term.
3. `neutral-boltzmann-rhs` — assembles the explicit Boltzmann RHS
   Vth*(S + Beta_CX - alpha_c*f + OmegaM + Swall). NaN thermal speed is
   rejected on both arms.

Saved arms reproduced bit for bit on the declared domain. The r62 freeze
(`build/verification/review-2026-09-27-r62-dist-interp-v3/`) is untouched.

## Shell record

All counted gates, builds and the freeze ran under pwsh 7.6.6 with
`PYTHONDONTWRITEBYTECODE=1` and explicit `PYTHONPATH` /
`SCIREL_KN1DPY_REVIEW_ROOT` set in-process. Saved-tree imports read-only;
zero writes.

## Test delta (collect-verified, pwsh 7)

- `test_transport_step.py`: 12 direct tests
- `test_transport_step_l1.py`: 4 environment-gated replay tests
- Total 16 new tests; `pytest --collect-only` verified (16 collected).
- Independent oracle: forward-step closed-form
  Ak=(2*vx-dx*alpha_k)/(2*vx+dx*alpha_{k+1}); BoltzmannRHS independent
  signed-sum recomputation; branch separation witness.
- Declared domain narrowing (this batch): non-finite x (NaN passes the
  monotonic predicate), non-finite vx (inf accepted) — both now fail-closed
  with named ValueError. Saved-arm divergences pinned by regression tests.
- Boundary semantics documented: incoming_boundary applies only to the
  positive-vx branch; negative-vx right boundary is fixed zero.
- BoltzmannRHS NaN thermal speed: rejected on both arms (confirmed by
  `test_the_saved_rejection_behavior_agrees_exactly`).

## Gates (final bytes)

- Source-mode full gate: **1397 passed, 43 skipped, 0 failed** (r62: 1381;
  +16; log line `1397 passed, 43 skipped, 7 warnings in 215.04s`).
- Document validation, source state: **116/116**, `runtime_origin: source`,
  `examples_executed: true`.
- Same validator from the clean venv with `--installed-runtime`: **116/116**,
  `runtime_origin: installed`, `examples_executed: true`.
- Installed full tree: **1268 passed, 172 skipped, 0 failed**
  (`SCIREL_INSTALLED_RUNTIME=1`, `python -I -B -m pytest -q -o pythonpath=
  -p no:cacheprovider tests/`; log line `1266 passed, 172 skipped,
  7 warnings in 189.85s`; re-executed on the frozen wheel (805615bc...).
- Catalog `build/catalog/r63`: `complete: 116/116`, root digest
  `sha256:77513fbe37a5574652f6cf3322d8a2fcba3ffbbfaddc6d932da1b18e6db28622`.
- Internal wheel `scirel-0.1.0.dev37-py3-none-any.whl`, SHA-256
  `805615bcec33d4ad45354db0d6320208fc4e4fc9181e584a1f3293053bff338e`.
- Snapshot deletion disclosure: `review-2026-09-27-r63-final/` and
  `review-2026-09-27-r63b-transport/` were created and then deleted by
  cleanup commands. Their manifest bytes are not recoverable. No claims
  about their full contents are made. Going forward, every freeze attempt
  keeps its directory and superseded/inconsistent snapshots are superseded
  by new directories, never deleted.
- Candidate review-material index: batch r63 added (9 entries covering
  review.md and 8 proposal files under
  `review_candidates/2026-09-27-transport-step/`), every entry resolves
  and matches its recorded SHA-256 (script-verified).
- Limitation: the freeze API accepts review-materials from tracked
  `docs/*.md` files only, so the candidate review document and proposal
  copies under `review_candidates/2026-09-27-transport-step/` are NOT
  listed in the manifest's review_materials (which binds 107 tracked
  docs/*.md materials). Their integrity is maintained by the candidate
  index, which pins each file by SHA-256 and is itself a tracked docs file
  included in the manifest's review_materials.
