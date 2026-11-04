# KN1DPy GDL interpolation-order diagnostic (2026-09-30)

Status: the archived IDL `kn1d.pro` terminal target remains OPEN. This is an
additive diagnostic for `stage1-KN1DPy-20260916T120118Z`, continuing the ABI
probe record. It is not an unmodified-source oracle, a 21-output comparison,
or a D1 `full_freeze`.

The source-supported raw input has 108 strictly increasing `x` points
(`min(diff(x)) = 0.00085857511`). The H2 mesh constructor's measured
interpolation abscissa `Y` decreases throughout this input, from 0 to
`-97.158576`; its step range is `[-3.6138132, -9.8051514e-06]`. The H mesh
constructor uses the same interpolation ordering pattern. Under the
run-owned GDL arm64 image, `interpol(x,Y,-10)` returned 0 with the warning
that interpolation abscissae must increase. Reversing both vectors returned
`0.22425508` for the same query. The unchanged H2 mesh had two points,
`[0, 0]`, and one nonpositive step. The monotonicity probe log is at
`lanes/CFE1-idl-source/attempts/gdl-h2-monotonic-20260930/evidence/gdl-h2-mesh.log`,
SHA-256 `4de0bf04b3343486b2842d6d2faf186a6ceb1b8ddb0b9a40bfe71f9884f8975b`.

In the isolated `gdl-order-compat-20260930` attempt, two working copies of
`create_kinetic_h_mesh.pro` and `create_kinetic_h2_mesh.pro` replace the
respective `interpol(x,Y,...)` call with
`interpol(reverse(x),reverse(Y),...)`. The prior C ABI bridge passes
pointer-width arguments to the unchanged Fortran routines. The source mount
was read-only, the candidate mount unavailable, and no dependency was added.
With these diagnostic adaptations, the original `KN1D` procedure reached
`DONE_OK` with `ERROR_FLAG=0`, `GammaHLim=9.2401283e+20`, and 145 Lyman and
145 Balmer samples. Their respective sums were `1176488.5` and `9431.3598`.
The probe receipt SHA-256 is
`4e01c623c1141afdb7c5bac09df274e60339a92e5edb9bcaccc0ed84cdeb8cc1`;
the GDL log SHA-256 is
`d57cb154417b31565ae14777461cd0364e46dcad60b8d503971f74359f41cb4f`.

The successful diagnostic does not establish IDL/GDL numerical equivalence
or validate the bridge. Next, independently review both adaptations and
their numerical consequences, persist all 21 physical outputs, and compare
the exact source and candidate paths on canonical and independently sealed
holdout inputs. Until those gates pass, retain the failed original lane and
do not assign source-oracle or holdout credit to this attempt.

An isolated follow-up `gdl-archived-interpol-20260930` tested whether explicit
compilation of the archive's `interpol.pro` would restore descending-axis
behavior without the two mesh edits. The GDL session reported `Compiled
module: INTERPOL`, yet `interpol([0,1],[0,-1],-0.5)` warned that X was not
strictly increasing and returned 0; linear interpolation on this monotone
descending pair is 0.5. This establishes the observed GDL runtime behavior,
not which implementation GDL dispatched internally. The attempt used the
same image with source read-only, candidate unavailable, and network `none`.
Its script SHA-256 is
`97b4df2f48adf62a824a4305f340898ee32bd426d5b2dc4f432e01f8d8a55fe2`;
the log SHA-256 is
`a9af2dd29abd31bdc00a699567dd8a4eaf8a821086e7c6a9a6bee35931bc9709`;
the probe receipt SHA-256 is
`1eefcbc21cf8df9e6785cd85c52fd75bd743dd9b0494eee948d5934dd5823fce`.
The receipt's exit 0 only confirms that this diagnostic script completed.
Reversing both vectors remains a conditional compatibility adaptation for
strictly descending axes; neither path is yet a verified original-IDL oracle.

A separate diagnostic renamed only the function symbol in an extracted
`interpol.pro` work copy to `INTERPOL_ARCHIVE`, leaving the archived linear
algorithm intact. In attempt `gdl-archive-renamed-20260930`, it and the
reversed-vector GDL call both returned 0.5 inside a descending two-point
interval and 1.5/-0.5 on its two extrapolation sides. The log SHA-256 is
`fd03b41f6c236a513e11b6a08c498f5ea3a3d2423f887726c153569a1d1ff2b9`;
the probe script SHA-256 is
`da496aeea85f123cedbc93f2769f43904dd8a3037c82f0098efe80f97e8b1702`;
the receipt SHA-256 is
`2f4962565c59ed6ad1b6ecdf376af98e4c9dd63d4cc88630c2d305f5018ccb3e`.

The corrected canonical comparison used the original 108-point input and
source reaction-rate formulas with `mu=2` for both H2 and H, as passed by
`kn1d.pro`. Both Y arrays decreased strictly. In fresh attempt
`gdl-archive-canonical-mu2-20260930`, the renamed archived function and
reversed-vector GDL call gave H2 cutoff `0.22425508` with printed difference
0 and H cutoff `0.30030279` with difference `3.8857806e-16`. Its probe source
SHA-256 is
`9277aa4ac63ef76f645e5d92a13c42fc91979fe485c0c55c69437858f716b6fd`;
its wrapper SHA-256 is
`cf2a5614193cf3e9b0c5b4ba47a27a5faa71ff0e245324808e06e10b0471920e`;
log SHA-256 is
`2232c00758e34327743437edf4ad701c823fe18fdb89edb7d3ff0279bceeb366`;
receipt SHA-256 is
`f0e9d1037a93eb0ce529fe3b0281ded8264fb8fdb26452c0c0a80a4a40b53f17`.
The earlier `gdl-archive-canonical-20260930` H result used `mu=1` and is
retained only as a misparameterized diagnostic; it is not canonical evidence.
These comparisons validate the local interpolation adaptation on this input,
not the C ABI bridge, GDL/IDL whole-program equivalence, or any sealed holdout.

The full 21-output path was then run in fresh attempt
`gdl-archive-21-output-20260930` with the same frozen raw input, byte-identical
capture program (SHA-256
`ca41923df0af8966251dc12f7a3b8069d02daaa132fc3bc6b30ebdb2624f0ac4`)
and C ABI bridge (SHA-256
`40975466ef5a3b478219109527803d83577c5f8013ad1b7b41455e5d84f0b4b9`).
The extracted work copies differ from the archive only at the H2 and H
`interpol_archive(x,Y,...)` calls and the renamed function declaration in
`interpol.pro`. The wrapper SHA-256 is
`bef054e819255d6fc13d69acd2a637f3d94fcd89dd4d584224defb321400a1d0`.
The probe used source read-only, candidate unavailable, network `none`, and
the same image digest. It reached `ERROR_FLAG=0` and `OUTPUT_21_OK`; its log
SHA-256 is
`148f5fe8939e8c1459d878c96f12f2f45989d2beb90b4e7aaffe3cd7d583b19e`
and receipt SHA-256 is
`3b8db63f1e9d396f196f5c1db78a5e7d9a02457405a24a95eb394b973c2e1f76`.

The new 21-terminal decimal capture has SHA-256
`9c61cd3acdfecbc190014999a9d3b21be29e9f986aa8c848742bd46b8b215de1`,
identical to the earlier reversed-vector capture; `cmp` confirmed byte-for-byte
identity. The existing structure validator independently accepted 21 double
terminals, 82 molecular-grid points and 145 atomic-grid points. Its new
derived result is
`coordination/kn1dpy-gdl-21-output-archive-validation-20260930.json`,
SHA-256 `fa3208225326e46662b1736f7a0909510295fb9aa40e3687a206d3aa74c1030b`.
That JSON matches the earlier validation after normalizing CRLF/LF line
endings; the captured terminal text itself is byte-identical. This is strong
canonical evidence that the two GDL interpolation adaptations give the same
terminal values for this input. The unchanged ABI bridge and GDL runtime still
lack independent original-IDL parity, and there is no sealed same-path
holdout or source-free candidate comparison. The KN1D target remains OPEN.
