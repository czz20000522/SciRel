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
