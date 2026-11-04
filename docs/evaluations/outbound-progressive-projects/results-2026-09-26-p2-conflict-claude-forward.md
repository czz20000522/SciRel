# Claude Code P2 conflicting-source forward test

This was a fresh, staged development evaluation with a structurally different
P2 input: two saved axisymmetric maps in NPZ rather than row CSV, one confirmed
closed-flux side and one conflicting draft/unsigned side. A new Claude Code
2.1.281 session used the `0.1.0.dev24` SciRel wheel, complete 74/74 catalog,
and `scirel-solving` method identified in the [manifest](manifests/2026-09-26-p2-conflict-claude-forward.json).
The CLI reported `claude-fable-5`, while assistant messages carried
`GLM-5.3-Flash`; the underlying model identity is unresolved. The wheel is an
unapproved development artifact.

The first autonomous turn correctly refused to choose between epsilon's draft
`greater_than` entry and tentative `less_than` margin. It asked one focused
question and delivered a rerunnable delta reader NPZ with 72 supported cells.
But its report called the supplied map inconsistent by a factor of `2*pi`:
it had reversed the Wb/rad and total-Wb field-derivative formulas. The
[stage-1 finding](../../../build/verification/p2-conflict-claude-forward/independent-stage1-finding.txt)
was frozen before any feedback.

Only after that delivery did the examiner provide the simulated export owner's
`greater_than` confirmation and a second grid. Claude independently carried
the confirmed declaration into the run. SciRel rejected epsilon on both
grids because the selected outer-flux region was entirely removed by the PML
frame; Claude retained diagnostics but wrote no misleading epsilon reader
file. It delivered delta on both grids. However, it merely described the
owner source in a JSON string: changing the confirmation file in an isolated
copy did not invalidate that accepted claim. The old delta NPZ survived, but
its diagnostics sidecar was rewritten with a fresh timestamp. These failures
are preserved in the [stage-2 finding](../../../build/verification/p2-conflict-claude-forward/independent-stage2-finding.txt).

Two narrow reviewer messages then led Claude to correct the flux convention,
bind accepted declarations to source-file bytes, version result names, keep
unchanged results byte-stable, and test corrected inputs. A further isolated
test caught an empty-binding bypass in the first repair; the second message
closed it. Thus the final package is **reviewer-assisted**, not an autonomous
scientific delivery pass. The [final archive](../../../build/verification/p2-conflict-claude-forward/stage4-reviewed-final.tgz)
has SHA-256 `90fdf0be23f027d79db34cbb980d6bc1aad6a2ef409e553d97bfbf9d7e54e0c2`.

The final archive was independently extracted outside the SciRel source tree.
Its wheel imported from a new venv's `site-packages`; 11 project tests passed.
Both ordinary grid entrypoints returned partial-delivery exit code 1, leaving
delta available and epsilon as rejection diagnostics. A direct call to the
installed SciRel TaskGraph matched all three delivered delta arrays on both
grids (72 support cells each). All 12 archived output files remained
byte-identical after rerun. Changing the owner note or removing a declaration's
bindings in the replay copy caused an explicit refusal before computation.
Commands, hashes and limitations are in the
[independent check](../../../build/verification/p2-conflict-claude-forward/independent-stage4-check.txt).

The result supports a narrow capability claim: Claude can autonomously ask
for a material source clarification and deliver the unaffected branch, then
keep an asset-rejected branch separate. It does **not** show autonomous
scientific explanation or robust source provenance; those required review.
The fixture is synthetic, lacks `B_phi`, and does not validate total device
field or an actual equilibrium. Examiner and solver directories were not
OS-isolated. The replay reused host dependencies and does not prove an offline
wheelhouse installation. A source digest proves bytes, not that the human
statement is scientifically true.
