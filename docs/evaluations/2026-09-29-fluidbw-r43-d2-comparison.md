# fluidBW r43 D2 comparison

This is a D2 development record, not an asset document, expert approval, or
release record. Input is the read-only r43 v2 handoff
`sha256:3c514298bd46be501a097e53766868285928c9e3cdb5f66c06a291289ec26f9a`
and its candidate bundle
`sha256:02b9b01d5224ecd2be0781aaae3540fdbe1526c05203f3748bdad6f9a6bd02fd`.
Comparison base is SciRel Git `590d7b4`. The D1 `full_freeze` qualifies the
declared source scope; it does not approve a D2 identity or a distribution.

| r43 input | D2 disposition | Material comparison with base | Target |
| --- | --- | --- | --- |
| `species_equilibrium_scales` | Reuse / absorb lineage | Same SI species axes, constants, signed gyro-radius, thermal speed and outputs. Existing validation rejects collapsed and nonpositive scales more consistently. | `kinetic.derive_species_equilibrium_scales` |
| `bessel_gamma_functions` | Reuse / absorb lineage | Same scaled `ive` Gamma and neighbor derivative, broadcast axes and complex argument; existing validation is stricter. | `kinetic.evaluate_bessel_gamma` |
| `plasma_dispersion_function` | Retain numerical variant | r43 fixes Weideman `N=64`, exposes `erfc`/rational branch flags and source rounding. Existing `wofz` is the analytic implementation and preserves its own failure contract. The frozen prose's `Z(0)=i*pi` is inconsistent with its implementation; the SciRel document records `i*sqrt(pi)`. | `kinetic.evaluate_plasma_dispersion_weideman` |
| `kinetic_dispersion_sum_n` | Retain numerical/failure variant | Same Maxwellian finite harmonic tensor and SI ports, but r43 uses Weideman `Z` and clamps `abs(kz)<1e-10` to positive `1e-10`; current analytic entry rejects `kz=0`. | `kinetic.evaluate_fluidbw_kinetic_dispersion_sum` |
| `z_pole_coefficients` | Retain | Source-defined `J=8/12` residues and poles, conjugate completion; no matching maintained callable. | `kinetic.get_z_pole_coefficients` |
| `gamma_lpole_coefficients` | Retain | Source-defined L-pole coefficient tables indexed by `|n|+1`; no matching maintained callable. | `kinetic.get_gamma_lpole_coefficients` |
| `fluid_dispersion_matrix` | Retain | Dense `(3*NSL+4)^2` first-order fluid eigenmatrix, distinct from existing cold dielectric tensor. | `kinetic.assemble_fluid_dispersion_matrix` |
| `fluid_wavevector_eigensolve` | Retain | General complex `zgeev` eigenvalues and positive-real/least-damped branch selection; no matching maintained callable. | `kinetic.solve_fluid_wavevector_eigenproblem` |
| `ronnmark_r_function` | Retain | Four-way Taylor/asymptotic/integral selector, including Octave complex comparison and source arithmetic; no matching maintained callable. | `kinetic.evaluate_ronnmark_r` |
| `kinetic_dispersion_ronnmark` | Retain | `J=8` rational-pole/Ronnmark response permits complex `kx` and zero `kz`; distinct from finite sum-n. | `kinetic.evaluate_kinetic_dispersion_ronnmark` |
| `dielectric_tensor_diagnostic` | Retain | `fDtensor` full 3x3 diagnostic uses default `lmx=15`, complex `kx`, explicit six-term determinant, no near-zero `kz` clamp, and returns all tensor components. It is not absorbed by the real-wavepoint sum-n entry. | `kinetic.evaluate_kinetic_dielectric_tensor` |
| `kinetic_wavevector_roots` | Retain | Fixed-seed complex root scan over supplied angular frequencies, Octave-compatible trust-region arithmetic and diagnostic exit flags; no matching maintained callable. | `kinetic.solve_kinetic_wavevector_roots` |
| `fluid_wavevector_scan` | Retain composition | Equilibrium -> L/J poles -> fluid matrix -> eigenbranches, with internally derived frequency ladder and explicit scan outputs. Ordinary dependency DAG. | `kinetic.scan_fluid_wavevectors` |
| `kinetic_dispersion_relation` | Retain composition | One equilibrium and probe feeds both source-method sum-n and Ronnmark tensors; neither path subsumes the other. Ordinary dependency DAG. | `kinetic.evaluate_kinetic_dispersion_relation` |
| `kinetic_wavevector_scan` | Retain composition | Equilibrium -> internally derived frequency ladder and fixed seed -> root scan, accepting absolute `kz` including zero. Ordinary dependency DAG. | `kinetic.scan_kinetic_wavevectors` |

The five current-documentation pages were independently reviewed against this
bundle digest in the r43 handoff. W38 source-first review binds unchanged
non-document code in the preceding digest; r77/r78 bind the same 34
non-document files to the previously passing 15 package suites. Those
receipts bound the D1 claim; D2 changes require their own regression evidence.
The W40 capture failure is not an admitted formal handoff. PDRK remains OPEN.

## Independent intake boundary

The independent r43 macro review is bound by SHA-256
`7b67725beb8622e70711aee00677a9d737a5aa5eccb0bbe83d09dc622ce79fa5`.
It verified 54/54 named files and source scope, reused the unchanged 15-suite
package evidence, and checked 14 canonical/holdout comparison records with 92
terminal rows within their original tolerances. It did not rerun scientific
execution. Its r74 entry validation and r57 package tests both had `/source`
mounted; r75 checked structure only. None of those D1 receipts proves runtime
behavior with the original source unavailable.

## D2 implementation and verification

The 13 retained assets have one exact `scirel.asset-document.v1` each in
`catalog/examples/`; the two absorbed assets retain their existing documents.
Their public functions use package-local imports and no source-checkout, network,
database or CodeFusion runtime. Scalar pole/harmonic counts and coefficient
indices now reject fractional values instead of silently truncating. The
Weideman and source-method sum entries reject nonfinite input and output; the
source-method sum also rejects zero species charge. Valid source numerical
branches, near-zero `kz` behavior and old analytic entries are unchanged.

Direct D2 tests cover the three compositions, fluid matrix/eigenbranch path,
Weideman and sum-n variants, Ronnmark and full tensor values, signed roots,
two-species dual determinants, and complex `kx` source points. Earlier read-only
local comparison of saved arrays found all 77 CASE1 and 77 CASE2 signed roots
on the same branch (maximum relative differences 0 and
`9.380750763125947e-15`; exit flags 77/77 and 76/77). Five complete fluid
single-point cases stayed inside the saved `1e-4` absolute bound; these finite
cases do not establish arbitrary-input parity.

The 132-document development catalog has root digest
`sha256:dfaba59e130a4aeb97a3c62cf908ddd052d04242a6703cec176fc9d99c550e6f`.
The development wheel SHA-256 is
`46efa025c10f97b3cc42c6e087461c252c6de79724ce03e2bb75b407b03edac4`.
In a worktree-external directory, four D2 test files passed 47/47 against that
installed wheel under `python -I`; `scirel` resolved from venv site-packages and
the import path contained neither SciRel `src` nor D1 implementation paths.
An offline Podman image `56b20a317975ad0cb839761431b2d179c3f0bed56c1c39f81fcd336e2499d32e`
was built with only that wheel, Linux dependency wheels and the four test files.
With no bind mounts and `--network none`, it passed the same 47/47 tests;
`scirel` resolved from `/usr/local/lib/python3.11/site-packages` and `/source`
did not exist. This establishes the tested SciRel chain without access to the
original source or D1 implementation tree inside that container. It does not
retroactively change the narrower D1 r74/r57 evidence or replace expert review.

The container used Python 3.11, NumPy 2.2.6 and SciPy 1.16.3. The final local
`scripts/check.ps1 -Mode affected` run passed 145/145 selected tests.

## Bounded D2 review successor

An independent Agent review of Git `412b507` is bound by
`d2-review-412b5070.json` SHA-256
`94554fcb309414ac50077c5102d21c84a0a70dc65198fb3510395b9a52899fb9`.
Its installed-wheel boundary probe and observed output are bound by SHA-256
`4f71d3b234f5ee479a089afeb020df0d2f162acd708b9f6a3924588724e39b69`
and `e9f88ccc9987a91c0d7bae91377d2c14f2b3e66795bd373562cf740fca84bb3b`.
The review requested four bounded fixes: exact complex port types, real `B0`
and nonzero `qs` in the full-tensor diagnostic, a finite fluid matrix at the
source resonance boundary, and the diagnostic module export. The successor
keeps the original source arithmetic and valid-case assertions. It rejects
singular fluid resonance denominators and nonfinite assembled matrices rather
than returning them as ordinary results.

The successor development catalog is in `build/catalog/fluidbw-r43-d2-review-fix`
with root digest
`sha256:6397450433d8fe6ac4b58cb28515505bb0e66d9caf4be1abf910dd7c6c31d696`.
The successor development wheel is in `build/wheels/fluidbw-r43-d2-review-fix`
with SHA-256
`927b33e4a1051d71698714b30d80dfe9da46c7647ebe25fd9c2fedfc6025deda`.
The original `412b507` wheel and catalog above remain unchanged. All 132 exact
documents passed runtime-signature and example validation, and the affected
selector passed 56/56 tests. In a worktree-external venv, `python -I` passed
42/42 tests across the three affected D2 files; the two changed modules were
byte-identical to the installed wheel copies, and `scirel` resolved from that
venv's site-packages. This successor venv reused host NumPy/SciPy; the earlier
offline Podman result applies to the original wheel only. The successor awaits
narrow independent rereview and remains `pending_unapproved`, not a public
release or expert-approved scientific baseline.
