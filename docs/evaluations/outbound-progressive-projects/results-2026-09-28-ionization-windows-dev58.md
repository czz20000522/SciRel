# Ionization windows, result ambiguity and numeric delivery (2026-09-28)

This synthetic two-stage project tested the revised outbound usage method with
the frozen r81/dev58 development wheel and complete 169/169 catalog. The
[manifest](manifests/2026-09-28-ionization-windows-dev58.json) binds the
opening inputs, pre-generated oracle, prompts, raw traces and three frozen
project states. The solver received no SciRel source checkout; separation from
examiner files was by prompt and directory layout, not OS isolation. All
catalog assets were `pending_unapproved`.

## Stage 1: unresolved result definition

The initial request said "ionization rate" for three electron-density and
temperature windows without a neutral H0 density. The solver found two
applicable H0 electron-impact ionization coefficient relations, COLLRAD and
Janev-H. It delivered both coefficient and per-neutral frequency columns,
marked volumetric columns `n/a_neutral_density_missing`, and left the single
featured-fit choice open. It did not invent a neutral density. Independent CSV
parsing against the pre-run COLLRAD oracle matched all three coefficients and
frequencies at the file's six-decimal scientific precision. Its ordinary
entrypoint exited 0 and 8 project tests passed. The first project and trace
were frozen before the later request was disclosed.

The first report also called `ne * <sigma*v> * duration` (about 15, 72 and
1098) the number of ionizations or fate of one H0 atom. Those numeric values
are integrated hazards, but one initially neutral atom cannot undergo that
many H0 ionizations without a replenishment model. This is a real scientific
interpretation error in the autonomous stage-1 delivery, separate from the
unresolved choice of rate coefficient or quantity.

## Stage 2: neutral-density follow-up

In the same Claude Code session, the solver received the later request and a
neutral H0 table whose rows were deliberately out of order. It joined by
`window_id`, kept the first comparison files, and added readable and numeric
volumetric-rate tables for both relations. Independent parsing of every
numeric CSV cell and comparison against the pre-run oracle matched the
COLLRAD event rates (W_A/B/C: `1.236484e22`, `4.797571e22`,
`1.372872e23 m^-3 s^-1`) and duration integrals within serialized precision.
The first CSV was byte-identical to the stage-1 archive. The ordinary
entrypoint exited 0 and 13 project tests passed. This is an autonomous pass
for the requested stage-2 **numeric calculation and file delivery**, while
the inherited per-atom interpretation remained wrong. The autonomous
project and trace were frozen before feedback.

## One recorded rescue

Independent review then supplied one focused correction: the per-atom
quantity is integrated hazard, a single initially neutral atom has
probability `1 - exp(-hazard)` of ionizing under the constant hazard, and the
stage-2 event integral assumes the prescribed neutral density is maintained
throughout each window. The solver renamed CSV columns, added probability
columns, corrected the generated explanations, and preserved the original
stage-1 CSV/Markdown in `results/superseded_stage1_20260928/` with an erratum.
The original files' hashes match the first frozen project. All coefficient,
frequency, hazard, volumetric-rate and event-integral numbers stayed the same.

Independent review parsed every final numeric CSV cell with an ordinary
reader, checked the hazard/probability and the ID-joined volumetric values
against the pre-generated oracle, and verified original-file preservation.
The ordinary entrypoint regenerated four result files byte-identical to the
final freeze; 17 project tests passed. This final result is **one-rescue
assisted**, not an autonomous scientific-interpretation pass. The usage-method
change itself passed `scripts/check.ps1 -Mode affected` with 7/7 selected
documentation tests. No SciRel scientific source or public API changed.

The solver used Bash-style tool commands in each round despite the explicit
`pwsh` 7+ instruction; the raw traces preserve that execution deviation. The
host-side examiner commands used `pwsh` 7+. The CLI was Claude Code 2.1.281
with requested alias `fable`; the trace labels responses `GLM-5.3-Flash`, so
the alias-to-model identity is not independently established.

The earlier [unseen probe-sampling case](results-2026-09-28-unseen-probe-sampling-dev58.md)
had 14 comparisons against a preselected grid-sampling oracle because an
ambiguous request allowed a different, scientifically valid exact-coordinate
calculation. Those 14 are a result-definition discrepancy, not proof of bad
arithmetic. This ionization case separately tests missing physical input,
numeric file readability, later ID-based data joining, and a real hazard
interpretation correction. Neither case establishes expert approval, an
external atomic-physics validation, a public release, or a CodeFusion-host
comparison.
