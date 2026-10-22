# SOURCE-AUDIT-C — held collision assets

Read-only audit of the 15 collision assets listed in `catalog/review/examples/` and held by `catalog/review/HOLD.json`. No repository, contract, candidate or source archive was modified; no Git commit was made.

## Source anchor

- Source project: `W-M-plasma-group/KN1DPy` (upstream `https://github.com/W-M-plasma-group/KN1DPy`).
- Source archive: `/mnt/e/SciRel-lab/sources/upstream-canonical-20261009/archives/W-M-plasma-group--KN1DPy--bb22c87210f64a899ee3f17719b150fb193985e2.tar.gz` (E drive, WSL `Ubuntu-CodeFusion`).
- Archive SHA-256: `a7bd21f395c6425958d62a08d203260980db31218d86cfa7612d80dcfd4b1d82`.
- Source commit: `bb22c87210f64a899ee3f17719b150fb193985e2` (archive directory name; upstream Git HEAD).
- Source layout at this commit: `KN1DPy/rates/janev/*.py`, `KN1DPy/kinetic_h.py`, `KN1DPy/kinetic_h2.py`. The provenance anchors in the saved review contracts use an older layout (`KN1DPy/sigma/*.py`) and saved implementation SHA-256 values that are **not** upstream blobs at this commit. Those saved files are not present in the E archive, so exact saved-artifact replay is unavailable; comparison below is against the archived upstream source.
- Source archive is not vendored. Candidate files are read from `catalog/review/candidates/src/scirel/collisions/`; direct held tests run with `SCIREL_REVIEW_HOLD=1`.

## Verdict summary

- assets: 15
- source-parity: 10
- source-conflict: 2
- source-defect: 3
- no-source: 0
- hold releases recommended: **none**. Source parity/defect attribution is now explicit, but `HOLD.json` still requires an external physical reference fixture or an owner-written acceptance of the fit limitation; source-package tests are not an external atomic-physics oracle. Source-conflict/defect rows additionally need an owner decision.

## Per-asset table

| asset | source file:lines | source SHA256 | saved implementation SHA256 | candidate file | candidate SHA256 | comparison | verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `scirel.collisions.atomic-hydrogen-1s-radiative-recombination-rate-coefficient` | `KN1DPy/rates/janev/sigmav_rec_h1s.py:4-35` | `a2d800be00dc710f…` | `ad71a46c86538079…` | `atomic_hydrogen_1s_radiative_recombination_rate.py` | `4fb62580cfeea3df…` | exact (max rel 0.0 on positive grid) | **source-parity** |
| `scirel.collisions.atomic-hydrogen-charge-exchange-cross-section` | `KN1DPy/rates/janev/sigma_cx_h0.py:6-45` | `242ec05dc6868657…` | `af55e393c0e7510a…` | `atomic_hydrogen_charge_exchange_cross_section.py` | `c851061e6d8bb2e0…` | exact both branches (max rel 0.0) | **source-parity** |
| `scirel.collisions.atomic-hydrogen-charge-exchange-rate-coefficient` | `KN1DPy/rates/janev/sigmav_cx_h0.py:4-79` | `8a7829191d21b301…` | `9a0037c238cc9fc9…` | `atomic_hydrogen_charge_exchange_rate.py` | `0d66a6fe35f2360b…` | exact on paired finite positive grid (max rel 0.0) | **source-parity** |
| `scirel.collisions.atomic-hydrogen-collision-matrices` | `KN1DPy/kinetic_h.py:1026-1112` | `92600295dfa2ae68…` | `80fcd63681d255fb…` | `atomic_hydrogen_collision_matrices.py` | `c0f3ed66808ad670…` | formula match; embedded fits replaced by maintained leaves; no numeric source class run | **source-parity** |
| `scirel.collisions.atomic-hydrogen-elastic-cross-section` | `KN1DPy/rates/janev/sigma_el_h_h.py:6-45` | `3ff760769cae2972…` | `129bc8e2d541e1ec…` | `atomic_hydrogen_elastic_cross_section.py` | `063ac82ba2d34b48…` | exact both branches (max rel 0.0) | **source-parity** |
| `scirel.collisions.atomic-hydrogen-omega-frequencies` | `KN1DPy/kinetic_h.py:674-739` | `92600295dfa2ae68…` | `5b80ea51cf514902…` | `atomic_hydrogen_omega_frequencies.py` | `163476fa194b2247…` | behavioral divergence: source DeltaVx/Wpp floors + Omega>=0 + global MH_H_sum sentinel; candidate per-cell undefined/negative policy | **source-defect** |
| `scirel.collisions.atomic-molecular-hydrogen-elastic-cross-section` | `KN1DPy/rates/janev/sigma_el_h_hh.py:6-35` | `a5dab5843f4cd06f…` | `4377ae235fbcc0fb…` | `hydrogen_h2_elastic_cross_section.py` | `f63daa0a1e7ece6e…` | values exact after squeeze; candidate adds leading singleton axis absent from latest source | **source-conflict** |
| `scirel.collisions.janev-electron-impact-ionization-rate` | `KN1DPy/rates/janev/sigmav_ion_h0.py:6-41; sigmav_ion_hh.py:6-41` | `247a89445f895cc6…` | `ff9b5f5cf8548706…` | `janev_electron_impact_ionization_rate.py` | `1a74b1f7072116c3…` | exact both species tables (max rel 0.0) | **source-parity** |
| `scirel.collisions.molecular-hydrogen-charge-exchange-cross-section` | `KN1DPy/rates/janev/sigma_cx_hh.py:6-30` | `8ededd676194c799…` | `2be195e5393454e7…` | `molecular_hydrogen_charge_exchange_cross_section.py` | `324d461fa94aa7bc…` | numeric parity to 1.99e-15 relative; not bitwise | **source-parity** |
| `scirel.collisions.molecular-hydrogen-charge-exchange-rate-coefficient` | `KN1DPy/rates/janev/sigmav_cx_hh.py:4-79` | `b3689b42f3642344…` | `8ca54201138f6d1d…` | `hydrogen2_charge_exchange_rate.py` | `094824be1aa4c68e…` | exact on paired finite positive grid (max rel 0.0) | **source-parity** |
| `scirel.collisions.molecular-hydrogen-collision-matrices` | `KN1DPy/kinetic_h2.py:1398-1485` | `0fdbb8e33280a704…` | `34358f11e3ee91fa…` | `molecular_hydrogen_collision_matrices.py` | `6ff5d9af72552178…` | formula match; embedded fits replaced by maintained leaves; no numeric source class run | **source-parity** |
| `scirel.collisions.molecular-hydrogen-elastic-cross-section` | `KN1DPy/rates/janev/sigma_el_hh_hh.py:6-43` | `72610465c3b4aff0…` | `0c10fbb936421268…` | `hydrogen2_hydrogen2_elastic_cross_section.py` | `c72e4ec53f9caadb…` | values exact (max rel 0.0); viscosity=True fallback same coefficients | **source-defect** |
| `scirel.collisions.molecular-hydrogen-omega-frequencies` | `KN1DPy/kinetic_h2.py:740-806` | `0fdbb8e33280a704…` | `13b001078958fa6f…` | `molecular_hydrogen_omega_frequencies.py` | `8a8b6c66f25076ef…` | behavioral divergence: source floors/clamps/global sentinel; candidate per-cell undefined/negative policy | **source-defect** |
| `scirel.collisions.proton-atomic-hydrogen-elastic-cross-section` | `KN1DPy/rates/janev/sigma_el_p_h.py:6-58` | `9a81ed81b92998a1…` | `b92dbb2af1596fa9…` | `hydrogen_proton_elastic_cross_section.py` | `94cf26add4fbdb19…` | differs at exactly 10 eV by 1.1456e-2 relative; candidate adds leading axis; 0 elsewhere | **source-conflict** |
| `scirel.collisions.proton-molecular-hydrogen-elastic-cross-section` | `KN1DPy/rates/janev/sigma_el_p_hh.py:6-39` | `bb33cc7db5f1a43a…` | `99ed2176ae8a27bf…` | `hydrogen2_proton_elastic_cross_section.py` | `0d849538eacc5274…` | exact on accepted grid (max rel 0.0) | **source-parity** |

## Per-asset findings / hold impact

### `scirel.collisions.atomic-hydrogen-1s-radiative-recombination-rate-coefficient` — source-parity
- Source: `KN1DPy/rates/janev/sigmav_rec_h1s.py:4-35` at commit `bb22c872…`.
- Saved implementation SHA (provenance): `ad71a46c865380793ee73e4ae267d536f0e0c8384929b1fff4bb18000c2e2528`; archived source file SHA: `a2d800be00dc710fdab1c0380bce97e000c398c42f5ff111edf94cf8621e5e31`; candidate SHA: `4fb62580cfeea3df88f4ebca238d8f33be7ffc456bc6f64d95dea34c6de707c8`.
- Comparison: exact (max rel 0.0 on positive grid).
- Finding: Formula, constants, clipping [0.1,2.01e4] and 1e-6 conversion match. Source silently clips nonpositive/non-real; candidate rejects as documented input repair.
- Hold: remains **blocked on the existing external-oracle/written-limitation decision**; source attribution is resolved but physical validity is not.

### `scirel.collisions.atomic-hydrogen-charge-exchange-cross-section` — source-parity
- Source: `KN1DPy/rates/janev/sigma_cx_h0.py:6-45` at commit `bb22c872…`.
- Saved implementation SHA (provenance): `af55e393c0e7510a0c1734eabc2a635374c1dfe2ec8dcc3ae87386772a80b099`; archived source file SHA: `242ec05dc686865708c62463405552a91210dfcbe4de252467dc771fcd82f748`; candidate SHA: `c851061e6d8bb2e09c146f4baee951c558bf0004df9019930b323fddba0b312b`.
- Comparison: exact both branches (max rel 0.0).
- Finding: Janev and Freeman-Jones coefficients/clipping match. Source silently clips negative energy and reduces array selector with np.any; candidate rejects, documented repair.
- Hold: remains **blocked on the existing external-oracle/written-limitation decision**; source attribution is resolved but physical validity is not.

### `scirel.collisions.atomic-hydrogen-charge-exchange-rate-coefficient` — source-parity
- Source: `KN1DPy/rates/janev/sigmav_cx_h0.py:4-79` at commit `bb22c872…`.
- Saved implementation SHA (provenance): `9a0037c238cc9fc99eabfa17984368d954c56ef9aa651e47967b5b1c273a1bfa`; archived source file SHA: `8a7829191d21b3018a5fdef3793ef3155586f654ca1cc3d9b1db96714c906a34`; candidate SHA: `0d66a6fe35f2360bdc47d4ade2f29d07291f46e6fe3c8546645219a476257502`.
- Comparison: exact on paired finite positive grid (max rel 0.0).
- Finding: 9x9 table, temperature/energy clipping and source exponent order match. Source silently clips nonpositive T/negative E; candidate rejects, documented repair.
- Hold: remains **blocked on the existing external-oracle/written-limitation decision**; source attribution is resolved but physical validity is not.

### `scirel.collisions.atomic-hydrogen-collision-matrices` — source-parity
- Source: `KN1DPy/kinetic_h.py:1026-1112` at commit `bb22c872…`.
- Saved implementation SHA (provenance): `80fcd63681d255fbe6a2a0fc2e400d63143c9809099d1181bb30ef3266a956fe`; archived source file SHA: `92600295dfa2ae682575156e92a90b5664dfa3d33ff51c0ac92089e82172bad8`; candidate SHA: `c0f3ed66808ad6705ddfcaf1997a21271472ce62953fdc7aec87a709c04a18bc`.
- Comparison: formula match; embedded fits replaced by maintained leaves; no numeric source class run.
- Finding: SIG_CX, SIG_H_H, SIG_H_H2 and SIG_H_P use the source energy factors, Fortran ordering, 5-angle midpoint rule and /8 viscosity factor. Candidate adds strict increasing-grid/scalar normalization validation; no formula change.
- Hold: remains **blocked on the existing external-oracle/written-limitation decision**; source attribution is resolved but physical validity is not.

### `scirel.collisions.atomic-hydrogen-elastic-cross-section` — source-parity
- Source: `KN1DPy/rates/janev/sigma_el_h_h.py:6-45` at commit `bb22c872…`.
- Saved implementation SHA (provenance): `129bc8e2d541e1ecde21584b01c89e6ebfc48115b5c582b0e15452e2f753c42c`; archived source file SHA: `3ff760769cae2972dd2ad619a5d0afe74fc368cb7a2f103eb780366716dddbea`; candidate SHA: `063ac82ba2d34b48bf5f5ba27ebca80e1b80c3fea412d3989ee85659bf5322d5`.
- Comparison: exact both branches (max rel 0.0).
- Finding: Momentum-transfer/viscosity five-coefficient fits and [0.03,1.01e4] clipping match. Source clips negative energy and uses bool() coercion for selector; candidate rejects, documented repair.
- Hold: remains **blocked on the existing external-oracle/written-limitation decision**; source attribution is resolved but physical validity is not.

### `scirel.collisions.atomic-hydrogen-omega-frequencies` — source-defect
- Source: `KN1DPy/kinetic_h.py:674-739` at commit `bb22c872…`.
- Saved implementation SHA (provenance): `5b80ea51cf51490208c5e39d71ca5a56c9a4610943a703e066cbbfa4ea6d9038`; archived source file SHA: `92600295dfa2ae682575156e92a90b5664dfa3d33ff51c0ac92089e82172bad8`; candidate SHA: `163476fa194b2247c72b15d32a10e2c794c2dd7c6ff0e491c3163a4136310327`.
- Comparison: behavioral divergence: source DeltaVx/Wpp floors + Omega>=0 + global MH_H_sum sentinel; candidate per-cell undefined/negative policy.
- Finding: Source uses DeltaVx_tol/Wpp_tol floors, clamps Omega to nonnegative and uses global MH_H_sum to switch target branch; candidate returns NaN/negative with defined/status and per-cell target_distribution. This is a deliberate source-defect repair/decision, not parity.
- Hold: remains **blocked on owner acceptance of the source-defect repair**; the candidate deliberately differs from the archived source behavior.

### `scirel.collisions.atomic-molecular-hydrogen-elastic-cross-section` — source-conflict
- Source: `KN1DPy/rates/janev/sigma_el_h_hh.py:6-35` at commit `bb22c872…`.
- Saved implementation SHA (provenance): `4377ae235fbcc0fb798253c995f44cf1e91aedecc99ce1b6bcbd1418b6c8d1bb`; archived source file SHA: `a5dab5843f4cd06fdc64d643d438c816d3841837ac1e0a83e0eefbac60ba21f3`; candidate SHA: `f63daa0a1e7ece6e0e16d6aa7bb98cbb944b0060fa64bd573e749ef756add5ed`.
- Comparison: values exact after squeeze; candidate adds leading singleton axis absent from latest source.
- Finding: Coefficient fit and clipping match, but latest upstream returns input shape; candidate adds one leading axis based on the saved-package wrapper claim. This is an observable API/shape conflict against the E archive source.
- Hold: remains **blocked by source conflict** (latest upstream shape/branch vs candidate/saved-package claim); owner must choose the API/branch contract before exposure.

### `scirel.collisions.janev-electron-impact-ionization-rate` — source-parity
- Source: `KN1DPy/rates/janev/sigmav_ion_h0.py:6-41; sigmav_ion_hh.py:6-41` at commit `bb22c872…`.
- Saved implementation SHA (provenance): `ff9b5f5cf854870608ce9e7e7ec8effe8718dbf5ddfa16b1bc90f42df908e3d1`; archived source file SHA: `247a89445f895cc642d6cbdf67cdafd863a7403be28792049941d9ce712c4799`; candidate SHA: `1a74b1f7072116c3019bdc27c24ecf00493d11f7c8be4daf46e3d4a2c0d7970c`.
- Comparison: exact both species tables (max rel 0.0).
- Finding: H/H2 nine-coefficient tables, clipping and poly order match. Source clips nonpositive temperature; candidate rejects, documented repair.
- Hold: remains **blocked on the existing external-oracle/written-limitation decision**; source attribution is resolved but physical validity is not.

### `scirel.collisions.molecular-hydrogen-charge-exchange-cross-section` — source-parity
- Source: `KN1DPy/rates/janev/sigma_cx_hh.py:6-30` at commit `bb22c872…`.
- Saved implementation SHA (provenance): `2be195e5393454e78a728eee8de53a12974865ad3fef470b8566b61ff3806a5f`; archived source file SHA: `8ededd676194c7991541ea7c9b1c99ddd4523fee5672d5a8942f6f3b94ae7c5b`; candidate SHA: `324d461fa94aa7bc2f5f7e64d797cc54674632b6c8f55c4489b31f6d57243b14`.
- Comparison: numeric parity to 1.99e-15 relative; not bitwise.
- Finding: Coefficient/clipping relation matches; candidate polynomial evaluator differs from source Horner order by <=2e-15 relative. Provenance claim of bit-for-bit arithmetic is too strong. Source clips negative energy; candidate rejects.
- Hold: remains **blocked on the existing external-oracle/written-limitation decision**; source attribution is resolved but physical validity is not.

### `scirel.collisions.molecular-hydrogen-charge-exchange-rate-coefficient` — source-parity
- Source: `KN1DPy/rates/janev/sigmav_cx_hh.py:4-79` at commit `bb22c872…`.
- Saved implementation SHA (provenance): `8ca54201138f6d1d19803e2bfb042b80980b2a9367bad36d53eafccdfc6bfd22`; archived source file SHA: `b3689b42f3642344da42f8bc480b60cb122583508e85673b14b4df07826433fa`; candidate SHA: `094824be1aa4c68e1a545990e6a117e231ef2424dc37e74bf2128ca8cadd8fcf`.
- Comparison: exact on paired finite positive grid (max rel 0.0).
- Finding: Molecular 9x9 table, clipping and accumulation order match. Source clips nonpositive T/negative E; candidate rejects, documented repair.
- Hold: remains **blocked on the existing external-oracle/written-limitation decision**; source attribution is resolved but physical validity is not.

### `scirel.collisions.molecular-hydrogen-collision-matrices` — source-parity
- Source: `KN1DPy/kinetic_h2.py:1398-1485` at commit `bb22c872…`.
- Saved implementation SHA (provenance): `34358f11e3ee91fa6768c8cf89d22eb1a2edbe2707f9e58d0b91472bf1b50d06`; archived source file SHA: `0fdbb8e33280a7045c8e5607a1eb7245e0883892191e5695fa11173aaca7000a`; candidate SHA: `6ff5d9af72552178204b68d627587d2eb3375258d0233c3f207a0b2f288624ac`.
- Comparison: formula match; embedded fits replaced by maintained leaves; no numeric source class run.
- Finding: SIG_CX (no 0.5/mu), SIG_H2_H, SIG_H2_P, SIG_H2_H2 viscosity /8 and Fortran ordering match source. Candidate adds validation repairs only.
- Hold: remains **blocked on the existing external-oracle/written-limitation decision**; source attribution is resolved but physical validity is not.

### `scirel.collisions.molecular-hydrogen-elastic-cross-section` — source-defect
- Source: `KN1DPy/rates/janev/sigma_el_hh_hh.py:6-43` at commit `bb22c872…`.
- Saved implementation SHA (provenance): `0c10fbb9364212681e6d8c023b5db707a09b02f73e984948be1d4448e7daccac`; archived source file SHA: `72610465c3b4aff0dee0bad4be2acd7bf31b163290b67e83314f2b6f1da987f1`; candidate SHA: `c72e4ec53f9caadbc7b1c7946bfebfdf1de45e9cb8739d28318ccc9bace4ee44`.
- Comparison: values exact (max rel 0.0); viscosity=True fallback same coefficients.
- Finding: Latest source prints a warning and has duplicate vis/non-vis coefficient branches; candidate exposes the same fallback values without the noisy warning and validates selector. Source cleanup/defect; no numeric conflict.
- Hold: remains **blocked on owner acceptance of the source-defect repair**; the candidate deliberately differs from the archived source behavior.

### `scirel.collisions.molecular-hydrogen-omega-frequencies` — source-defect
- Source: `KN1DPy/kinetic_h2.py:740-806` at commit `bb22c872…`.
- Saved implementation SHA (provenance): `13b001078958fa6fd8a819e65340a3a4e22fbfb6a3dbb58e4451db92e81f78d9`; archived source file SHA: `0fdbb8e33280a7045c8e5607a1eb7245e0883892191e5695fa11173aaca7000a`; candidate SHA: `8a8b6c66f25076efc1185ff847ce5ce7d3379d875b509bb2e26b452dc1c31926`.
- Comparison: behavioral divergence: source floors/clamps/global sentinel; candidate per-cell undefined/negative policy.
- Finding: Source DeltaVx/Wpp floors, Omega>=0 clamp and global MH2_H2_sum sentinel; candidate uses explicit defined/status and target_distribution. Deliberate source-defect repair, not parity.
- Hold: remains **blocked on owner acceptance of the source-defect repair**; the candidate deliberately differs from the archived source behavior.

### `scirel.collisions.proton-atomic-hydrogen-elastic-cross-section` — source-conflict
- Source: `KN1DPy/rates/janev/sigma_el_p_h.py:6-58` at commit `bb22c872…`.
- Saved implementation SHA (provenance): `b92dbb2af1596fa9aa505cb478b3be1cdc4ca92c1bf40321d2b52472c64c6daf`; archived source file SHA: `9a81ed81b92998a1d49135c9f38b6440871e3131aaca69a70b3779df55f92544`; candidate SHA: `94cf26add4fbdb196e44361a6dbea226c0578fc7fdb507d2d184cfc59e2f6b8e`.
- Comparison: differs at exactly 10 eV by 1.1456e-2 relative; candidate adds leading axis; 0 elsewhere.
- Finding: Latest upstream Python uses low branch for E<10 and high branch at exactly 10; candidate uses low at 10 (IDL/saved-package claim). Source branch and output shape conflict with latest archive; owner must choose.
- Hold: remains **blocked by source conflict** (latest upstream shape/branch vs candidate/saved-package claim); owner must choose the API/branch contract before exposure.

### `scirel.collisions.proton-molecular-hydrogen-elastic-cross-section` — source-parity
- Source: `KN1DPy/rates/janev/sigma_el_p_hh.py:6-39` at commit `bb22c872…`.
- Saved implementation SHA (provenance): `99ed2176ae8a27bfa7c551d53eec9a3b6c2abcea6acaa526a2201b96cb3239ed`; archived source file SHA: `bb33cc7db5f1a43a41de9c6ea0de60a1830566fea8076eca81e5f9a21fdef89c`; candidate SHA: `0d849538eacc5274e954bae6e439c8399183b752bb4d1df96877923dfbb8a8f8`.
- Comparison: exact on accepted grid (max rel 0.0).
- Finding: Five-coefficient fit and [0.03,1.01e4] clipping match; source clips negative energy, candidate rejects. Shape same as latest source.
- Hold: remains **blocked on the existing external-oracle/written-limitation decision**; source attribution is resolved but physical validity is not.

## Principal findings

1. **All 15 assets have a genuine upstream source**: KN1DPy commit `bb22c872…`. Eleven leaf fits have no substantive arithmetic conflict: 1s recombination, both CX cross-section branches, atomic CX rate, atomic elastic branches, Janev H/H2 ionization, molecular CX cross section (to 2e-15), molecular CX rate, H2-H2 elastic, and H2-on-H+ elastic.
2. **Source conflict — H-on-H2 and H+-on-H elastic shape**: latest upstream `sigma_el_h_hh` and `sigma_el_p_h` return the input shape; candidates add one leading singleton axis based on the saved-package wrapper. The candidates are not shape-compatible with the E-archive upstream source.
3. **Source conflict — proton-on-H 10 eV breakpoint**: latest upstream Python selects the high-energy branch for exactly 10 eV (`low = E < 10.0`); the candidate selects the low branch (`<=10`). This gives a 1.1456e-2 relative difference at exactly 10 eV and zero difference below/above. The candidate documents this as an IDL/saved-package repair; the latest upstream branch does not support the claimed “strict-branch zero” wording.
4. **Source defects — atomic/molecular Omega**: upstream uses `DeltaVx_tol`/`Wpp_tol` floors, `np.maximum(Omega, 0)` and global `MH_H_sum`/`MH2_H2_sum` sentinels; candidates instead return explicit NaN/negative status and per-cell target states. This is a deliberate behavioral divergence and needs owner acceptance, not parity.
5. **Source defect — H2-H2 viscosity**: upstream `sigma_el_hh_hh(vis=True)` prints a warning and duplicates the same coefficient branch as momentum transfer; candidate keeps the same numerical fallback without the warning and with selector validation.
6. **Input-contract repairs are not parity**: upstream leaf functions silently clip negative/nonpositive energy/temperature and accept some coercions; candidates reject them. This is the documented source-defect/input-policy repair, and no formula values change on accepted domains.
7. **Provenance issue common to all rows**: the review contracts record saved-implementation SHA-256 values from an older layout (`KN1DPy/sigma/…`) that do not match the upstream archive blobs and are not available in the E archive. Exact saved-artifact replay is not possible from the E source; only upstream formula comparison is. This should be recorded as a source-revision/evidence conflict, distinct from mathematical parity.

## Hold decision

No held collision asset can leave `human-review` from this audit alone: `HOLD.json` requires an external physical fixture or a written owner acceptance of the fit limitation. The source audit can reclassify the reason from “source absent/unclear” to “source parity verified; external physical oracle still absent” for ten assets, but the exposure gate remains. The two shape/branch conflicts and the two Omega source-defect repairs need explicit owner decisions before any rebind.

## Method / limits

- Read the E-drive archive without writing to E; extracted a read-only copy under `/tmp` for local source inspection.
- Compared leaf functions numerically on finite accepted grids, including endpoint clipping and both branch/selector paths; source modules were imported with a stub for missing `tomli_w`.
- Matrix/Omega comparison is structural (source lines vs candidate formulas); full upstream KN1DPy runtime was not executed because its dependency set is not installed in this checkout. Matrix candidates are covered by held direct tests: **413 passed, 1 xfailed** in `tests/collisions`.
- Candidate tests are direct unit/composition tests, not an external physical collision oracle; source package records `validation_oracle_gap`.
- No source, candidate, contract or repository file was modified; no Git commit.
