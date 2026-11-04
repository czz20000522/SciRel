# Hydrogen population intake: D2 continuation

Status: `pending_unapproved` development comparison. The intake checkout is
read-only at `647d5dbd36404bc5e76d934a875984787e789644`; SciRel comparison
base is `abebd18c4071f879f0143c0f84dcc9dcc381013a`. The saved KN1DPy
bundle's strict D1 qualification is withdrawn. These dispositions do not
qualify its whole source, approve assets or authorize public release.

## Input dispositions

| Intake asset | Disposition | Maintained target and binding | Evidence and limit |
| --- | --- | --- | --- |
| `scirel.collisions.janev-electron-impact-ionization-rate-coefficient` | `reuse` | `scirel.collisions.janev-electron-impact-ionization-rate`; `git://abebd18c4071f879f0143c0f84dcc9dcc381013a/catalog/examples/scirel.collisions.janev-electron-impact-ionization-rate.json`; canonical document `sha256:32efe7556926600638d38b9191cb09df323c0b213a8ee2918323ed9a123789e2` | Same H/H2 nine-coefficient tables, `[0.1, 2.01e4]` eV clipping, ascending-power polynomial order, `1e-6` conversion and `m^3/s` result on finite positive real inputs. Both use the same public signature. Intake source SHA-256 `966ef3bdf8218a09ec6d593166bb80bdfb4b45f6b9b4ce8b95a71c4a97080f64`; maintained source SHA-256 `0fd17b80fb327ba1e0ac36d3b4d305daa88ce2afc20a4d0c7ccdd02eebe6b990`. Intake accepts some numeric-string/boolean temperatures and may raise `TypeError` for unhashable species; maintained code rejects invalid types with `ValueError`. Not an exact duplicate or a claim of identical behavior outside the declared input domain. |
| `scirel.collisions.atomic-hydrogen-1s-radiative-recombination-rate-coefficient` | `reuse` | Same asset ID; `git://abebd18c4071f879f0143c0f84dcc9dcc381013a/catalog/examples/scirel.collisions.atomic-hydrogen-1s-radiative-recombination-rate-coefficient.json`; canonical document `sha256:d3ef10f71cf594c1f3d82bccb6df2e3bfacc08e1415edd0dc44776af3fa5de38` | Same H(1s) ground-state relation, frozen `Ry=13.58`, `A_nl=3.92`, `x_nl=0.35`, `n=1`, endpoint clipping, operation order and `m^3/s` scaling on finite positive real inputs. Intake source SHA-256 `0371ee015d6f58ceeaa3859fbd8ff97188e32eb78b18ce20e024589fd482c21b`; maintained source SHA-256 `2f804f2bd9a9d6c8ff38b3ebe203f481281990098301438dcb59c9c09cac63b0`. Maintained code rejects boolean/numeric-string coercions and checks represented output. Neither side supplies an external physical oracle. |
| `scirel.kinetic.hydrogen-saha-equilibrium-population` | Retain new operator | `scirel.kinetic.hydrogen-saha-equilibrium-population` in this D2 increment; canonical document `sha256:250efcd762ef8326d4b3ced10295841616aa8979fa64fdbb9b4646d949a5a921` | The main base had no equivalent callable. Retains `3.310e-28`, `13.6057 eV`, the saved one-dimensional paired scientific branch and `m^-3` output. The 1e32 source sentinel is rejected. Intake source SHA-256 `36e4a5cb0b00b17b105c3e93e303dd80b39621ecd50d206457f79c7109aacde5`. SciRel rejects boolean and numeric-string coercions and prevents pre-square float rounding of integer levels above `2^53`; its exact document records these differences and the saved document's scalar/profile wording conflict. The intake document's assertion that higher levels are always more populated on its test inputs is not carried forward: the exponential can suppress level 2 at cold temperatures. |

The first two rows are suitable for `input_dispositions` in an attributable
future candidate submission. They do not by themselves form a `no_changes`
workflow: the Saha input is retained as a new review unit, and this comparison
does not fabricate a qualified CandidatePackage or automated L1 checks.

## Development evidence

- A Saha regression failed at import before implementation. A later
  large-integer-level regression failed before its targeted repair. Afterward
  20 direct cases passed, including frozen-constant formula checks at levels
  1/2/3 with `rtol=1e-15`, exact handling above `2^53`, shape/domain rejection
  and non-finite result guard. Direct comparisons with the intake modules were
  elementwise exact on finite positive grids: 2-D Janev H/H2, 2-D H(1s)
  recombination and 1-D Saha at levels 1/2/3.
- `scripts/check.ps1 -Mode affected` selected exactly the Saha direct test and
  passed 20/20. All 119 exact documents passed schema, runtime-signature and
  executable-example validation. Catalog/MCP tests passed 31/31.
- Development catalog: `build/catalog/d2-saha-final-20260928`, `119/119`, root
  `sha256:6bc1e701225f0389bcc529577272b840025c5eb991a9f7026e691b4252fa03e9`.
  Development wheel: `build/verification/d2-saha-final-20260928/wheel/scirel-0.1.0.dev5-py3-none-any.whl`,
  SHA-256 `9e9ed8f4faf93471fd7753e16a5fdd774f52295f9753bcb84c243e3872a77b7d`.
  A `python -I` import from a separate virtual environment resolved SciRel
  under its `site-packages` and evaluated a finite positive two-sample Saha
  result through both domain and root public exports.
- An accidental unclassified affected path triggered the whole suite before
  count fixtures were updated: 1711 passed, 82 skipped, 7 failed and 16
  errors. Document-count and catalog-total failures were addressed in this
  increment. The two affected-selector assertions also failed on the unchanged
  `abebd18` main baseline; they are not Saha regressions. The isolated tree's
  outbound-manifest hash failure is outside this scientific asset change.

No external atomic-physics oracle, current qualified D1 source root, expert
decision or public distribution license is established by these checks.

## Successor verification at `ce0763e`

The preceding development evidence describes the earlier D2 snapshot. The
successor at `ce0763e` makes the `n_H+ = n_e` premise explicit in the exact
document, accepts Python integer `principal_level=2**64` without pre-square
rounding, and preserves the public `ValueError` failure under a caller's
`np.errstate(all="raise")`. Two focused regressions failed before the repair.
The affected selector chose the Saha direct test and passed 22/22; the changed
exact document passed schema, runtime-signature and executable-example checks.
The earlier 119-document validation is not claimed to have been repeated for
this successor.

- Development catalog: `build/catalog/d2-saha-fix-ce0763e/release.json`,
  `119/119`, root
  `sha256:874fa326905d1375eee8df9d7abad2a8e31415fa60d0e7ac60a89a744b7e1348`.
- Development wheel: `build/verification/d2-saha-fix-ce0763e/wheel/scirel-0.1.0.dev5-py3-none-any.whl`,
  SHA-256 `8e8bf38af6949b0cd5d09dbb25c10a3a39cd3633e9864b85089c5798ce360153`.
  It was installed with `pip --no-index --no-deps` into that run's `venv`.
  From outside the SciRel checkout, `python -I` resolved `scirel` under this
  venv's `Lib/site-packages`, confirmed the root and kinetic exports are the
  same callable, matched the `2**64` formula result exactly
  (`3.9821942897304742e+46` for `n_e=1e18 m^-3`, `T_e=2 eV`), and observed
  `ValueError` on an overflowing input under strict NumPy errors.

This remains a `pending_unapproved` development comparison. In particular,
the saved KN1DPy input is not a qualified D1 source freeze; these successor
checks do not expand its source or scientific validity claims.

The bounded independent successor review was performed by collaboration task
`/root/workflow_independent_review` under coordination thread
`01a0d158-0127-78e1-a7b2-5af28e50876a`; its verifiable model/version is
unknown. The reviewer compared `d2b64a971c41a05fcc6dc8321013cf93ba4b7152`
with `ce0763ee7db2d5ba8bdf249b83b3b1be4d0c0661`, replayed the large
integer and strict NumPy counterexamples, checked that caller error policy is
restored and the population expression's AST is unchanged, and inspected the
three-file diff for the `n_H+ = n_e` scope premise. All three original findings
were closed for that exact successor. The review's tool-output chunks are
`8025fe` (diff and identity) and `87dc67` (counterexamples); these identify
thread tool records, not saved artifacts or content digests. No separate raw
review report or script was retained. The retrospective coordination summary
is at `../CodeFusion/build/coordination/three-day-20260925/workflow-redesign-20260928.md`
in its Saha successor review and reviewer-identity addendum. This review does
not establish D1 source qualification, human approval or release status.
