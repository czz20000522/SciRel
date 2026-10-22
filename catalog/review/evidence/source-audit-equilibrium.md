# SOURCE-AUDIT-E: axisymmetric anisotropic Picard and direct anisotropic inversion

Read-only audit. No SciRel file, candidate, contract or Git object was modified.
Evidence was read from the E-drive source/project material and from already
present local source snapshots; nothing was copied into the SciRel checkout and
no source code was executed.

## 1. Scope and method

Targets (held):

- `scirel.equilibrium.axisymmetric-anisotropic-picard`
- `scirel.inference.direct-anisotropic-inversion` (composition that consumes an
  equilibrium solver port; HOLD says it depends on the held axisymmetric asset)

E-drive was reached read-only through the user's Windows host
(`ssh tomos-home` + `wsl.exe -d Ubuntu-CodeFusion`), root
`/mnt/e/SciRel-lab`. Relevant material:

- Pleiades project source snapshot:
  `projects/pleiades/source/CURRENT/eepeterson--pleiades--0161abb3e9a1d85143c650f068ec524d672fc9ab.tar.gz`
  (commit `0161abb3e9a1d85143c650f068ec524d672fc9ab`; extracted locally to
  `/tmp/pleiades-src/...` for read-only grep).
- Pleiades project final:
  `projects/pleiades/decomposition/FINAL/` with
  `d2/FINAL_MANIFEST.json` (`source_commit e4ec86fa72d7cdbf74c4799f16127c8b099e7c00`),
  `d2/reproduction/installed-scientific-tests/tests/graph_contracts/...`, and
  `d2/prior/inputs/anisotropy/PACKAGE_CLOSURE_FINAL.json`.
- Pleiades admission/provenance export:
  `projects/fluidbw/decomposition/WORK/home-wsl-continuation-20261018/tmp/xcheck/provenance/admitted-assets.json`
  and `pleiades-import.json`.
- SciRel source snapshots already on the Mac:
  `/tmp/SciReL-ddfb33b-source2/` and `/tmp/SciReL-ec3c296-source/` (both contain
  `tests/graph_contracts/...` and pre-quarantine `src/scirel/...`).
- Candidate code under audit: `catalog/review/candidates/src/scirel/...`.

## 2. Source identity

| item | value |
|---|---|
| Source project (declared) | Pleiades, `source_asset_ref` = `Pleiades/task_graphs/新版轴对称各向异性Picard平衡` and `Pleiades/task_graphs/直接各向异性参数反演` |
| Upstream Pleiades library commit | `0161abb3e9a1d85143c650f068ec524d672fc9ab` |
| Pleiades delivery source commit | `e4ec86fa72d7cdbf74c4799f16127c8b099e7c00` |
| Pleiades anisotropy package closure (SciRel lineage) | candidate `1f0185c2e466c9840157572fc55bb8490d946b07`, canonical `ac8b451b2acc50eb0b56a1fa558fcaa3a1a96dfa`, base `0e7ce4e5713104012f49a09de503adacd1c6301f` |
| Admitted source graph, axisymmetric | `task_graphs/新版轴对称各向异性Picard平衡/graph.py` sha256 `3de0fc07404243ac9db9c5a1438d7af9a4d4f1f91f6a4c4ae23da4e925515650`; `task_graph.yaml` sha256 `3410647a8d47afa3f16bae8e2f795733ee87c9461d44eaf4b413e3b2988effac`; `version_commit_ref vcommit_9ed34fda66feb2cd55150a9f` |
| Admitted source graph, direct inversion | `task_graphs/直接各向异性参数反演/graph.py` sha256 `6d1c3b52b5244ab34110256dd90461d86328a3ac1c4405264a2d07341d328324`; `task_graph.yaml` sha256 `997b3335ca64f1c0be99ca666148990cdf84ed7dd5f77571bc7f1c0f055ee2ce`; `version_commit_ref vcommit_d196fbe74e20d36c0435d3d1` |
| SciRel source snapshot used for comparison | `/tmp/SciReL-ddfb33b-source2` (commit `ddfb33b`); `/tmp/SciReL-ec3c296-source` (commit `ec3c296`) has the same two candidate snapshots |
| Candidate files | `catalog/review/candidates/src/scirel/equilibrium/axisymmetric_anisotropic_picard.py`, `catalog/review/candidates/src/scirel/inference/direct_anisotropic_inversion.py` |

Important: the Pleiades **upstream library** at commit `0161abb3` does not
contain the anisotropic pressure model at all. A grep of `pleiades/` for
`anis`, `p_perp`, `p_parallel`, `latin_hypercube`, `least_squares`, and
`observation` returned no matches. Its only equilibrium solver is the isotropic
`pleiades/eq_solve.py` (`compute_equilibrium`, `mirror_equilibrium`). The
anisotropic graphs are Pleiades **assembly/receiver** artifacts that call SciRel
operators; they are not a transcription of Pleiades library formulas.

## 3. Axisymmetric anisotropic Picard

### 3.1 What the source artifact actually specifies

The admitted source asset is a Pleiades task graph. Its YAML (available revision
`53bd311e97c88d8ae902234bd9efaadcef7a61dbea86a3ca90cff5b05aa2a13d` in Pleiades
FINAL and in the `ddfb33b` snapshot; admitted hash is a different, earlier
revision `3410647a...`) specifies:

- order: `psi -> poloidal field -> pressure closure -> cylindrical div(P) ->
  masked J_phi -> Green update -> next psi`;
- terminal re-evaluation of field/closure/force at the returned state;
- failure policy: invalid ports fail closed, nonconvergence returns last state
  with `converged=false`;
- convergence: last relative `psi` change is diagnostic only; the returned-state
  unrelaxed `fixed_point_residual <= tol` decides the fixed point;
- `plasma_mask`: units `boolean`; false cells set `J_phi=0` before Green;
  `state_policy`: caller owns closure, grid, Green matrix and mask policy.

Its node callables are SciRel operators, not Pleiades functions:
`scirel.field.poloidal_field_from_flux`, `scirel.equilibrium.anisotropic_force_balance`,
`scirel.equilibrium.axisymmetric_picard_update`, plus glue `_coerce_pressure`
and `_apply_active_mask`.

### 3.2 Formula comparison

| layer | Pleiades upstream `pleiades/eq_solve.py` | candidate |
|---|---|---|
| current source | isotropic `r * p'(psi) * dr * dz` (lines 63-73) | anisotropic cylindrical `div(P)` toroidal current via `compute_anisotropic_force_balance`; cell currents from `J_phi` with `cell_areas` |
| flux feedback | `psi = g_psi @ plas_currents + psi_vac`, optional `relax` mix (lines 72-77) | same Green-response structure through `axisymmetric_picard_update`, `relax` mixes raw vs old cell currents |
| termination | `Err = ||psi - psi_old|| / |psi_edge|`; `while Err > tol and k < maxiter`; no terminal recompute of field/closure (lines 30-96) | unrelaxed `fixed_point_residual = ||candidate - psi|| / max(||candidate||, ||psi_vac||, tiny)`; break when `<= tol`; terminal state fully recomputed; `converged` from returned-state residual |
| mask | `plas_clip` applied to `pprime` at line 70 (`pprime[plas_clip.flatten()] = 0`); mirror solver computes internal `plas_mask` at 169-170 | caller `plasma_mask` applied to `J_phi` after force; fixed array or callable; `np.asarray(mask, dtype=bool)` |
| gates | none | `minimum_field`, firehose margin, parallel-force compatibility |

Conclusion: the **anisotropic formula has no Pleiades upstream source**. The
candidate matches the Pleiades **task-graph assembly** (callables, order,
terminal re-evaluation, failure policy, convergence semantics), but it is a
SciRel rewrite of the assembly, not a copy of the Pleiades isotropic solver.
The task graph itself calls SciRel operators, so this is assembly parity rather
than independent scientific-source parity.

### 3.3 Terminal ordering: source is silent; candidate follows SciRel contract

- Current candidate: after the iteration loop it recomputes the field, checks
  `minimum_field` **before** `_require_state`/closure/force, then masks and
  evaluates the terminal force (candidate lines ~100-115).
- Candidate contract says exactly this: "terminal minimum-field gate precedes
  terminal closure, mask and force evaluation" (review example
  `verification.scope[0]`).
- The older SciRel source snapshot `ddfb33b`/`ec3c296` has the opposite order
  (closure/force first, then the minimum-field gate). Diff of candidate versus
  `ddfb33b` shows this ordering move plus docstring/naming changes only.
- The available Pleiades task-graph YAML does **not** specify the order of the
  terminal gates; it only requires final re-evaluation and fail-closed behavior.

So the ordering is a **SciRel API/terminal-order policy decision** (already
documented in the contract and matching the current candidate), not a source
behavior. If "source parity" is defined against the only available older SciRel
snapshot, this is a source conflict; if defined against the Pleiades task graph,
the source is underdetermined and does not block release on this point.

### 3.4 Mask: SciRel API policy, not source behavior

- Source task graph: `plasma_mask` is declared boolean, false cells zero
  `J_phi`, and `state_policy` explicitly gives mask policy to the caller.
- Pleiades upstream: `plas_clip` is a raw index mask on `pprime` (line 70); an
  integer mask would be interpreted as indices, so the upstream convention is
  not portable and is not the graph's mask contract. `mirror_equilibrium`
  computes its own internal boolean `plas_mask` (169-170).
- Candidate: fixed mask is `np.asarray(mask_port, dtype=bool)`; a callable mask
  is supported and returns `(B, psi) -> mask`; false cells zero `J_phi`.
  This coercion and the callable form are SciRel API policy.

Therefore HOLD's "unified strict-bool policy or documented coercion" decision is
**not a source-parity question**. The source does not prescribe strictness; it
only says the graph applies a caller-declared boolean selector.

### 3.5 Verdict

`source parity (Pleiades task-graph assembly) + no upstream source for the
anisotropic formula; terminal gate ordering is SciRel API policy (source
underdetermined; differs from older SciRel snapshot); mask is SciRel API policy,
not source behavior.`

Not a `source defect`: no source implementation contradicts a scientific claim
in the admitted graph; the upstream Pleiades library simply has no anisotropic
equilibrium model. Not clean `source parity` either, because the scientific
formula is not present in the source project and the only source code state that
shows terminal ordering has the opposite order.

### 3.6 Conditions to lift the hold

1. Owner records the mask decision (strict bool or documented coercion) in the
   HOLD decision and contract/zh ledger, and a regression covers the chosen
   behavior. This is an API policy decision; source parity does not decide it.
2. Owner records source status explicitly: Pleiades task-graph assembly parity;
   no upstream Pleiades anisotropic formula; candidate is a maintained SciRel
   rewrite (admission record already states "not byte-identical").
3. Terminal ordering: accept the contract's floor-before-closure as SciRel API
   policy and keep the terminal-order regression, or require a source artifact
   that actually specifies gate order. The currently available source graph does
   not.
4. Bind the release decision to the exact admitted source graph revision
   (`version_commit_ref vcommit_9ed34...`, admitted graph hashes above), because
   the Pleiades FINAL copy of the YAML is a later revision (`53bd311e...`); do
   not claim byte parity across revisions.

## 4. Direct anisotropic inversion

### 4.1 Source artifact and wiring

The admitted Pleiades source asset is the task graph
`task_graphs/直接各向异性参数反演/graph.py` (sha256 `6d1c3b52...`) with
`task_graph.yaml` (sha256 `997b3335...`), version commit `vcommit_d196...`.
The graph:

- takes `equilibrium_solver` and `diagnostic_evaluator` as caller ports;
- binds observation layout and residual reduction to
  `scirel.diagnostics.observation_residuals`;
- calls `scirel.inference.anisotropic_trial_evaluation`;
- optionally calls `scirel.inference.latin_hypercube_sampling` for the initial
  design;
- runs `scirel.inference.anisotropic_parameter_optimization`;
- returns best parameters, residual vector, equilibrium, evaluation log,
  `converged`, `failure_reason`, optimizer summary.

Candidate `run_composition` in
`catalog/review/candidates/src/scirel/inference/direct_anisotropic_inversion.py`
implements exactly this wiring. Diff versus the `ddfb33b` source snapshot is
limited to docstrings, `run_composition` vs `run_graph`, and
`asset_loader` vs `operator_loader`; the computation and port semantics are the
same. So the composition is at **source parity with the Pleiades task-graph
assembly** (again, the graph itself calls SciRel leaves, so no upstream numeric
inversion source exists).

### 4.2 Dependency status

- Contract dependencies are only
  `observation-residuals`, `anisotropic-trial-evaluation`,
  `anisotropic-parameter-optimization`, `latin-hypercube-sampling`.
- The candidate does **not** import the axisymmetric Picard module.
- The link to the held asset is entirely through the caller-provided
  `equilibrium_solver` port (task graph calls it "调用方 N6 callable" and lists
  N6 in `related_pfm_nodes`). The graph is responsible for unit-compatible
  observation wiring and parameter control; the forward port owns the physical
  equilibrium.
- HOLD's "composition depends on the held axisymmetric capability" is therefore
  an **application/provenance dependency**, not a static code dependency.

### 4.3 Verdict and hold condition

`source parity (Pleiades task-graph composition); no upstream numeric inversion
source; dependency on the held axisymmetric capability is through the caller
equilibrium_solver port only.`

Direct inversion cannot be released independently *as an anisotropic inversion
capability* while its intended N6 forward port is held. Lift requires one of:

1. release the axisymmetric capability first with its mask policy decided; or
2. replace/qualify `equilibrium_solver` with a released (or separately admitted)
   forward solver and re-audit the composition against that solver's contract.

Restore/bind the exact source graph artifact as well: Pleiades FINAL declares
`tests/graph_contracts/direct_anisotropic_inversion` but the payload contains no
such directory; the admitted hashes (`997b3335...`, `6d1c3b52...`) and the
SciRel snapshot YAML (`1b086c7f...`) are currently the only source identities.

## 5. Cross-check of candidate vs available source snapshots

Commands used (read-only):

- `diff <(sed '/HELD: human-review exposure guard/,+2d' candidate) snapshot`
- sha256 of candidate, snapshot and admitted source files
- YAML hash comparison against Pleiades FINAL

Results:

| pair | difference |
|---|---|
| candidate axisymmetric vs `ddfb33b` source | docstrings + `run_composition`/`run_graph` naming + terminal minimum-field gate moved **before** terminal closure (old snapshot: after closure) |
| candidate direct inversion vs `ddfb33b` source | docstrings + `run_composition`/`run_graph` + `asset_loader`/`operator_loader` + error text only; semantics identical |
| Pleiades FINAL axisymmetric YAML sha256 | `53bd311e...`, identical to `ddfb33b` snapshot YAML |
| admitted axisymmetric source graph hashes | `graph.py 3de0fc07...`, `task_graph.yaml 3410647a...` (different revision from FINAL YAML) |
| admitted direct source graph hashes | `graph.py 6d1c3b52...`, `task_graph.yaml 997b3335...` (different revision from `ddfb33b` snapshot YAML `1b086c7f...`) |

Candidate file hashes (LF-normalized) are `307a213e...` (axisymmetric) and
`c7777c93...` (direct inversion); they do not equal the admitted input or
snapshot hashes, consistent with the admission record's "maintained SciRel
implementation, not byte-identical" statement.

## 6. Residual risks and NOT_RUN

- No source code was executed; conclusions are from source/task-graph text and
  candidate inspection. NOT RUN: Pleiades or SciRel runtime comparison,
  numerical parity probes, mask coercion probes.
- The Pleiades upstream commit `0161abb3` has no anisotropic code; the graph
  source is an assembly artifact, so "source parity" cannot mean formula parity
  with an upstream solver there.
- Source revision drift: admitted graph hashes differ from the Pleiades FINAL
  YAML copy; a release record must bind the exact admitted revision.
- Direct inversion's graph artifact is declared but absent from the Pleiades
  FINAL payload; only its hashes and a later SciRel snapshot copy exist.
- Terminal gate ordering is not specified by the source graph and conflicts with
  the older SciRel snapshot; it is currently a documented SciRel API policy.
- Mask semantics are caller/API policy; source uses raw index-like `plas_clip`
  while candidate coerces to bool and supports a callable.
- HOLD reasons remain open for human decision; this audit does not change HOLD,
  contracts, candidate code or Git.
