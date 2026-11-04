# TokaGrad and cql3d source-first freeze boundary (2026-09-30)

This read-only D2 check does not replace either original D1 run's frozen
records or qualify an intake. The deployed validator is
`/home/opc/.codex/skills/scientific-computation-asset-extraction/scripts/validate_capability_progress.py`,
SHA-256 `5a1508803dddb543fe4810d29c0315ac50dcc581fb254170061c838ce98ca675`.
Each replay used the original progress, scope manifest, evidence matrix, live
ledger and candidate bundle with `--require-closure-signal`.

## TokaGrad

The `stage1-TokaGrad-20260920T025327Z` progress record, SHA-256
`70ebf8708a6581fc4935c77520f5340814f62c564c9b9edc6493468a91798dd1`,
self-reports 24/24 source partitions, 22/22 paths and `full_freeze`. The
deployed validator returned exit 1, `valid=false`, with 45 errors: missing
`closure_signal.asset_entry_validation` and 44 v1 comparison receipts where
delivery closure requires v2. Relabeling those receipts would not establish
the execution and artifact bindings required by v2.

The separate original-run source-first veto at
`coordination/tokagrad-neural-transport-source-first-reopen-20260925.txt`
(SHA-256 `ac0662ba02ac9b52870b69996180fa73ffca003fb5ce3ee54b4718aa97e9c1de`)
finds a material denominator gap. Public configuration selects
`tglfnn_jax` and `neonn_jax`; the frozen source derives physical
`chi_e`, `chi_i` and `Dn` in those successful branches. The candidate
transport graph routes to an operator that errors or substitutes Bohm/Angioni
fallbacks for those selections. A generic neural forward test does not
reassemble the source-selected transport, face flux or next-state terminals.
Missing model weights are an explicit input/dependency boundary, not evidence
that the successful branch is dead. Recovery must reconcile source-provided
models and external inputs, preserve fallback semantics, and compare the
actual source and source-free candidate terminals on same-input canonical and
independently sealed holdout cases at an exact successor bundle digest.

Read-only inspection of the current frozen-source checkout sharpens that
dependency boundary. `README.md` (SHA-256
`cbda3e978ccabe450029c32c6f8171bf4bceda999f07e25b814c796ec473670b`)
directs users to clone GA's separate `neural` repository under
`external_models/neural`; `.gitignore` (SHA-256
`7aa0597ececa5984b1bcf9d0205cc35aaea62090ae2e28674164a206715a6754`)
excludes that path. A recursive file and symlink search found no
`brainfuse_*.net` file or model-directory symlink in this checkout, and the
tracked Git tree has no matching model file. The configured defaults are
`tglfnn_jax` and `neonn_jax` with model roots at `external_models/neural`
(`src/tokagrad/config.py`, SHA-256
`82490e616fe5c6143be76672f211b8cf717c454db3f1b6ef28257398cf28876c`);
`inputs/iter_flattop_tglfnn.json` selects both branches.

The missing-weight failure is outside each local fallback handler:
`tglfnn_jax_effective_diffusivities` calls `build_tglfnn_features` before its
`try`, and that builder loads the ensemble when `sim` is present
(`src/tokagrad/tglfnn_jax.py`, SHA-256
`db05f101bbdbc09cd299970e117fb7e3577537649d3cfd661c8a910b02958fa6`).
`neonn_jax_diffusivities` similarly calls `build_neonn_features` before its
`try`, which loads the NEO ensemble (`src/tokagrad/neonn_jax.py`, SHA-256
`4b4064de8dee96bcf362d306247df590f03306881d4aeb92cad19439436396d0`).
On this checkout, the default model lookup therefore raises
`FileNotFoundError` before either branch can fall back to Bohm or Angioni.
This is a code-path determination, not an executed numerical receipt. A
success-branch comparison needs identified, digest-bound model bytes and an
isolated source/candidate probe; absence of weights here does not remove the
successful neural path from the source-derived denominator.

## cql3d

The original `stage1-cql3d-20260916T092101Z` r1 progress record, SHA-256
`8bda8a438f5fd0df06f2539733f033a58c5d637a86fcf805b1beb78cef9f8643`,
self-reports `full_freeze` for one declared bounded path. The deployed
validator returned exit 1, `valid=false`, with two errors: schema version
`1.1` instead of strict `1.0`, and missing
`closure_signal.asset_entry_validation`. Its own claim ceiling excludes
whole-program source parity and an independently sealed holdout campaign.

The original-run independent source-first review at
`coordination/source-first-independent-review-20260927.txt` (SHA-256
`563f7ef8d0824269d057951b21c1d81c354101764dadd6c8d6a9727688a25c3a`)
identifies a reachable non-CQLP impurity path: `tdchief.f` calls
`impurity_update`; `ainpla.f` reaches `ADCDO`; the ADC routines produce mean
charge, radiative and ionization losses, charge-state distributions and
`dens_imp`; `netcdfrw2.f` writes terminal `dens_imp_allstates` and `dens_imp`
arrays. The historical partial-ionization operator expressly excludes this
time-and-surface output. The source checkout's tracked tree was dirty at that
review, so its frozen source digest must be checked against the exact bytes
used by future receipts; Git HEAD alone is insufficient.

Both runs require a new source-derived whole-scope denominator, exact-digest
source-free candidate execution, same-input canonical and independent sealed
holdout terminal comparisons, and independent scientific review before a
successor `full_freeze`. The separate cql3d group revision is a different
source snapshot and cannot inherit this run's evidence. Preserve all old
claims and receipts as historical material; no D2 intake or export follows
from this check.
