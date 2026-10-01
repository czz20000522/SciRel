# KN1DPy 21-output GDL capture (2026-09-30)

Status: the archived IDL `KN1D` terminal target remains OPEN. This record
continues the ABI and interpolation-order diagnostics in
`stage1-KN1DPy-20260916T120118Z`. It captures every declared physical output
of one adapted GDL execution, but does not establish an unmodified IDL oracle,
candidate parity, an independently sealed holdout, or D1 `full_freeze`.

The frozen source archive `KN1D.zip` has SHA-256
`c1a5b6c5250d6b1c095957296b49976182835f5bcbaf15a9bc30d002714583be`.
Its `kn1d.pro` SHA-256 is
`2ac94f565966ee3db01d1c4a1199d249a968e5fdc2f4bac5bfded4fc0493bb1c`;
its `interpol.pro` SHA-256 is
`04a1c79bdaa08d5e44ababb5783a205e19b705da2fcacfeef8ccb46a1f687b91`.
The archived `INTERPOL` contract explicitly permits strictly monotone
descending abscissae and uses piecewise linear interpolation by default.
Reversing both value and abscissa vectors preserves that linear interpolation
mathematically when the abscissae are strictly decreasing. This conditional
source reading does not prove numerical equivalence of GDL and IDL.

The fresh diagnostic attempt is
`lanes/CFE1-idl-source/attempts/gdl-21-output-capture-20260930`. It reused
the previous two one-line mesh overrides (SHA-256
`77826cabaa86d152c4ae38fb98228112de57a2cfadfc9b97ec7cee1d97691b52`
and `712f37ecdf5131050262ee9cf423d73900c122b54d6a64ffbb03f00bd067a22c`)
and the C pointer-width ABI bridge (SHA-256
`40975466ef5a3b478219109527803d83577c5f8013ad1b7b41455e5d84f0b4b9`).
The new GDL capture program and shell wrapper have SHA-256
`ca41923df0af8966251dc12f7a3b8069d02daaa132fc3bc6b30ebdb2624f0ac4`
and `0bede53a5c71dcf0ba2c04b7e212e7819b2ec8b68add9b7136f3ceb29897d8ea`.
The run used the existing GDL arm64 image
`sha256:62ddb924e7de54cc544b8f37689a0dff57f2a8d3bd0808a5e13fb195e1b9065e`,
with frozen source read-only, candidate unavailable, and network `none`.

The probe exited 0 with `ERROR_FLAG=0` and `OUTPUT_21_OK`. Its receipt SHA-256
is `e58d249f831445ecacb7db2b28c8708d1e41af60181b21d0f9e7ff1c4b267f77`;
the GDL log SHA-256 is
`9e951c17d34178fa9fe7aa2b6743f1bbe88371212419f2b03aa87ffdd1f50910`.
The complete decimal capture is
`evidence/kn1d-21-terminals.txt` within that attempt, SHA-256
`9c61cd3acdfecbc190014999a9d3b21be29e9f986aa8c848742bd46b8b215de1`.
It contains nine molecular profiles on 82 points, eleven atomic profiles on
145 points, and scalar `GammaHLim`; all 21 are IDL numeric type 5 (double).
The 21 names and every value were independently parsed as finite, all declared
block lengths match, and both coordinate arrays increase strictly. Parsed
`GammaHLim=9.24012829081771835e20`, Lyman sum `1176488.5150474696`, and
Balmer sum `9431.35980002017` agree with the prior rounded diagnostic printout.

The derived structure check is
`coordination/kn1dpy-gdl-21-output-validation-20260930.json`, SHA-256
`df40296731080880509512f8897a895c4883ecbd1a799530154c1ccc95a8893f`.
Its parser is retained separately at
`coordination/kn1dpy-gdl-21-output-validator-20260930.py`, SHA-256
`df26e1f1d21cc95b02d4a76e06d4bc531f56b5fade0a70c5df1317f1e56f5a76`.
Both are derived coordination artifacts; the probe attempt and its receipt
remain unchanged after execution.

A later isolated run used the archived `INTERPOL` body under a renamed symbol
for the H/H2 cutoff calls. Its 21-terminal decimal capture is byte-identical
to this run's capture. The adaptation comparison and its limits are recorded
in `coordination/kn1dpy-gdl-order-compat-20260930.md`; neither capture is an
unmodified IDL oracle.

An additional derived consistency check applies the archived
`Interp_ScalarX` outside-domain zero rule and `INTERPOL` linear rule to the
captured `xH2`, `GammaxH2`, `xH`, and `GammaxH` vectors. It reconstructs
`GammaHLim=9.240128290817718e20`, exactly matching the captured decimal
value (absolute and relative error 0); 99 of 145 atomic-grid points use the
outside-domain molecular zero. The check uses the captured data and the
single-precision representation of the 0.2 m limiter. Its script is
`coordination/kn1dpy-gamma-consistency-20260930.py`, SHA-256
`1becf2ec4e9935c6e38b110ed007ae614fcfd393c543ee185c2aa9576aebbe78`;
the result is `coordination/kn1dpy-gamma-consistency-20260930.json`, SHA-256
`79eda604bbf42fd6d29b9add45bb088313d276520551b916ae0975ccbb9687f6`.
This internal check does not establish source-to-candidate parity.

Read-only candidate mapping found that
`task_graphs/KN1DPy顶层终态框架装配图/graph.py` (SHA-256
`5f183e6f20fbb6b3eaf95947d7e9333e30af0f065f1d61938db23894e00fce63`)
returns a 20-field public `frame` and does not produce `GammaHLim`. Its
contract (SHA-256
`f54018488371793e1c3aacbd589521f622b3b543ff27d5d94828ccb38368dd5d`)
requires caller-supplied atomic and molecular terminal predecessor states.
The graph also takes `xH2`, `xH`, `nHP`, `THP`, `SH`, `SP`, `SideWallH`, `Lyman`,
and `Balmer` directly from `frame_inputs`. Its optional producer handoff does
not fill those fields. Thus the current graph cannot support a raw-input-to-21-
output comparison; feeding the captured source values into these ports would
conceal missing candidate producers.

Next, obtain independent scientific review of the ABI and descending-grid
adaptations, bind an independently sealed source-supported holdout, and compare
all 21 physical outputs against the exact source-free candidate with the
required tolerances and branch conditions after the missing producers and
combined flux are implemented. Until then, this full output
capture remains a compatibility diagnostic without source-oracle or D2 credit.
