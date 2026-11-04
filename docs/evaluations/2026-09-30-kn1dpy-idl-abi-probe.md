# KN1DPy archived IDL runtime boundary (2026-09-30)

Status: the original IDL `kn1d.pro` terminal path remains OPEN. This is an
additive diagnostic in the original `stage1-KN1DPy-20260916T120118Z` run, not
a replacement for its earlier source records or a D1 `full_freeze` claim.

The existing run-owned GDL arm64 image is
`sha256:62ddb924e7de54cc544b8f37689a0dff57f2a8d3bd0808a5e13fb195e1b9065e`.
No dependency was added. The `gdl-interop-flag-20260930` probe confirmed that
`gfortran -fallow-argument-mismatch` builds `fast_b2val.so` for aarch64, but
the archive's `BS2DR` calls `fast_b2val__`, while default gfortran exports
`fast_b2val_`. The historical `gdl-run-13` already used
`-fsecond-underscore` to match the symbol. A byte-identical replay saved at
`lanes/CFE1-idl-source/attempts/gdl-replay-output-20260930/evidence/gdl-replay.log`
showed `gdl_exit=139`: GDL reached `BS2DR` and segfaulted. Its enclosing
script returned zero, so the probe receipt's exit code alone is not terminal
evidence.

The archive's Fortran `CALL_EXTERNAL` wrappers declare the pointer vector as
`INTEGER*4 ARGV(*)`, an ABI mismatch for the arm64 process. A diagnostic C
bridge in fresh attempt `gdl-abi-terminal-gate-20260930` accepts `void **argv`
and passes the original 14 or 13 pointer arguments to the unchanged Fortran
`fast_b2val_code_` and `b2ink_` routines. Its source is retained in that
attempt's `scratch/kn1d_call_external_abi.c`, SHA-256
`40975466ef5a3b478219109527803d83577c5f8013ad1b7b41455e5d84f0b4b9`.
The diagnostic script SHA-256 is
`6b0aca7029783d42775f2845d8870426b2dfaa392ab43eeb37db835af3b85631`;
the pre-existing raw-input probe was copied unchanged, SHA-256
`07f24f0ae1c8309533a6bf42edbfed4a3b3cf7e7a7dd4ed841733376d6a5c617`.
The source mount was read-only and the candidate mount unavailable.

The bridge removed the segfault and executed the original procedure through
`BS2DR`, `CREATE_SHIFTED_MAXWELLIAN`, and `KINETIC_H2`. It did **not** complete
the terminal path. GDL reported `Kinetic_H2 => x(*) must be increasing with
index!`, then `INTERP_FVRVXX` halted because `fa(*,0,0)` and `Vra` have
different lengths. The strict probe requires `DONE_OK` and recorded exit 70.
Its receipt SHA-256 is
`5a0f477690d7c1c88fa83bf5bb06f0de00f3cc1f8a3fa8054692194b33d811fa`;
the GDL log SHA-256 is
`1c28cbb17176c4524ec50ff14d1efa611ed819773cab0c5b1bd28340ff6cf7dc`.

Next, inspect the source and probe's internal H2 mesh and interpolation array
shapes under a valid source-supported raw input. Establish numerical parity of
the bridge before using it as an oracle; complete and compare all 21 physical
outputs on canonical and independently sealed holdout inputs. Neither this
diagnostic nor the old Python-only 20-output receipts earn IDL target credit.
