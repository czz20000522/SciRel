# SOURCE-AUDIT-K: parallel-EM continuation and ion-ion Coulomb log

Read-only audit. No source, test, contract or review file was changed; no Git
commit was made. Source access caveat: `/mnt/e` (the E-drive project root named
in the task) is **not mounted in this session**, so the E checkouts themselves
were NOT_RUN. The audit used:
- the pinned TORAX upstream file (public repository, commit `48448e6`), and
- the PDRK upstream commit `21c08f215ef143aeafdde4c746e393d8a1feaef7`, which is
  the exact `upstream_commit` frozen in the local PDRK provenance record
  (`/private/tmp/SciReL-ec3c296-source/provenance/validation/pdrk-root-full-core-20261014.json`).

If the E snapshots differ from these commits, the owner must rerun the comparison
against the E checkout before acting on the lift recommendations.

## 1. Coulomb-ii

### Source

TORAX `torax/_src/physics/collisions.py`, `calculate_log_lambda_ii`:

```python
"""... Formula 18e in Sauter PoP 1999. See also NRL formulary 2013, page 34. ..."""
T_i_ev = T_i * 1e3
return 30.0 - 0.5 * jnp.log(n_i) + 1.5 * jnp.log(T_i_ev) - 3.0 * jnp.log(Z_i)
```

Pinned file SHA-256:
`0c3938594ab250c8a5986c871a15cdd6d9f4986b936c069fee66419c9ab0e433`
(<https://github.com/google-deepmind/torax/blob/48448e610eddaa887e8f99b0d6d21f91e1cad674/torax/_src/physics/collisions.py#L227-L246>).

### Candidate

`catalog/review/candidates/src/scirel/physics/coulomb_logs_ii.py` computes:

```python
result = 30.0 + 1.5*(log(1000.0)+log(T)) - 0.5*log(n) - 3.0*log(z)
```

with `T` in keV. This is algebraically the same expression, with a different
floating-point evaluation order (`ln(1000)+ln(T)` instead of `ln(1000*T)`), which
is the declared overflow/underflow-avoidance choice.

### Recheck

- Source formula on source test cases: `T_i_ev=1, n=1, Z=1 -> 30`;
  `T_i_ev=e^8, n=e^42, Z=e^1 -> 18`. Both reproduced.
- Over a `T=1e-3..1e2 keV`, `n=1e10..1e22 m^-3`, `Z=1..10` grid:
  max absolute difference **7.1e-15**, max relative difference **4.5e-16**
  (operation-order roundoff only; no formula/coefficient difference).
- Candidate/source units match: `T_i` keV, `n_i` m^-3, `Z_i` dimensionless.
- Attribution: TORAX itself labels the formula **Sauter PoP 1999 Eq. 18e**, with
  the NRL 2013 page-34 cross-reference. The candidate's existing attribution
  ("Sauter 1999 ion-ion fit, not NRL 2013 Eq. c") matches the source. The
  previously recorded +0.4388 ln Lambda difference is the expected
  Sauter-vs-NRL transcription difference, not a candidate arithmetic error.

### Verdict and hold

**Source parity: YES** (algebraically identical; only evaluation-order
roundoff). **Conflict: NO.** The source resolves the HOLD's model-attribution
question in favour of the candidate's declared Sauter 1999 Eq. 18e.

**Lift recommendation:** the asset is **eligible to leave HOLD** after the owner
records the source reference (TORAX `collisions.py`, Sauter 1999 Eq. 18e) and
accepts the Sauter model. The formula/contract need no numeric change. If the
owner instead wanted NRL 2013 Eq. c, that would be a different model and the
candidate would remain out of parity; the source does not support that
attribution.

## 2. Parallel-EM continuation

### Source

PDRK `examples/beammode/em1d_dr.m` (pinned `21c08f2`, SHA-256
`7fc53df0ec4347fa98afcf76ec17f8cdf6b297d80574eb2158e174cc89008315`,
<https://github.com/hsxie/pdrk/blob/21c08f215ef143aeafdde4c746e393d8a1feaef7/examples/beammode/em1d_dr.m#L18-L29>):

```matlab
kmin=0.01; dk=0.01; kmax=0.5;
k=(kmin:dk:kmax)/cwp;
x0=(0.05+0.04i)*wcs1;
for kk=k
    options=optimset('Display','off');
    x=fsolve(f,x0,options,kk);
    x0=x;
    w=[w,x];
end
```

`f` is the EM1D parallel dispersion relation with `pm`, `wps2`, `vds`, `vtzs`,
`wcs`, `c2`, and `zeta=i*sqrt(pi)*faddeeva`; it uses `k*vtz` (positive k only).

### Candidate

`catalog/review/candidates/src/scirel/kinetic/dispersion/parallel_continuation.py`:

- default `k = arange(1, 51)*0.01/cwp` = **0.01..0.5 / cwp, 50 points**: exact
  source grid;
- default seed `(0.05+0.04j)*wcs1`: exact source seed;
- accepted root becomes the next seed: source feedback preserved;
- `scipy.optimize.root(method='hybr')`: **different solver** from MATLAB
  `fsolve` default (trust-region-dogleg);
- accepts only `success`, finite attempted root/value and
  `|f|/scale <= residual_tolerance`; otherwise raises `ContinuationFailure`.
  The source does not have this gate and assigns `x0=x` after every `fsolve`
  call, including a failed or inaccurate return;
- candidate uses `|k|` in causal denominators and supports negative k/arbitrary
  species; the source example is positive-k, four hard-coded species. These are
  declared derived generalizations, not source parity claims.

### Recheck

- Defaults/grid/seed for positive k: **match** the pinned source. The candidate
  positive-k residual against the source expression (four-species state, x=2.1+0.8j,
  k=0.3, pm=1) differs by **9.9e-17** relative; the source expression and the
  candidate's Faddeeva residual are the same relation for positive k.
- Stopping/failure semantics: **conflict by design**. With a valid three-species
  state, the candidate default call raises `ContinuationFailure` at the first
  seed (reproduced with the review-guarded candidate module); the source would
  carry the `fsolve` return into the next seed regardless of success. The
  candidate's docstring explicitly says the stopping protocol is corrected and
  that no failed root becomes the next seed.
- The candidate's declared default-50-point-seed failure is therefore exactly
  the HOLD reason: branch/seed policy is not source-identical and is not
  agent-decidable.

### Verdict and hold

**Source parity: PARTIAL** (default grid/seed/formula yes; solver, accepted-root
gate and failure propagation no). **Conflict: YES, intentional.** The HOLD stays
valid.

**Lift recommendation: NO as-is.** Owner must choose one policy and record it:
1. accept the fail-closed divergence as a deliberate safety correction and
   restrict/declare the input envelope (then the contract can move to
   pass-with-limits with a regression for the failure path), or
2. reproduce the source's failed-seed carryover under the source solver (not
   recommended without a source-trajectory oracle: it can propagate
   false-success roots), or
3. disallow the implicit default seed/grid and require explicit caller seeds
   with a bounded k policy.

No code or contract change was made in this audit.

## 3. Evidence and commands

- TORAX file: `curl -sL https://raw.githubusercontent.com/google-deepmind/torax/main/torax/_src/physics/collisions.py -o /tmp/torax-collisions.py`;
  pin `48448e610eddaa887e8f99b0d6d21f91e1cad674`.
- PDRK file: `curl -sL https://raw.githubusercontent.com/hsxie/pdrk/21c08f215ef143aeafdde4c746e393d8a1feaef7/examples/beammode/em1d_dr.m -o /tmp/em1d_dr_pinned.m`.
- Coulomb difference probe: 200 log-spaced points per parameter; see report §1.
- Candidate default continuation: loaded the review-guarded candidate module with
  `SCIREL_REVIEW_HOLD=1`; a valid three-species state raised
  `ContinuationFailure` at the first seed.
- No repository file was modified; no commit.

## 4. Boundaries

- E-drive checkouts `/mnt/e/SciRel-lab/projects/{pdrf,pdrk,torax}` were not
  mounted; this audit used pinned public upstream mirrors plus the local frozen
  PDRK provenance commit. If E snapshots differ, re-run the comparison.
- The Coulomb candidate/source check is algebraic and byte-level only for the
  formula; it does not establish external physical calibration.
- The parallel continuation source comparison is semantic, not a root-trajectory
  replay: the source's MATLAB `fsolve` trajectory is not reproduced in SciRel.
