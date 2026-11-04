# VEQpy diagnostic terminal denominator audit (2026-09-30)

Status: `T-DIAGNOSTICS` remains open. This is a read-only, static scope
check, not a numerical comparison receipt or a D1 freeze. No frozen source,
harness, candidate bundle, or prior receipt was changed.

The frozen `veqpy/model/equilibrium.py` SHA-256 is
`37702ed0ae3cd1c1c97bd20e9e321095fa921e6f353b8820f8daf625062d369a`.
The existing `coordination/d1_harnesses/reassemble_diagnostics.py` SHA-256 is
`b0ae1dc150c2241b2e530aa9b04e4a2c233ce760afdb2e74581c0df8dbddfb76`.
Both files are in the frozen VEQpy source/run under
`/home/opc/codefusion-decomposition`.

Python AST enumeration of non-private `@property` definitions directly in
`Equilibrium` found 68 names. Structured extraction of the harness's
`VECTOR_OUTPUTS`, `MATRIX_OUTPUTS`, and `SCALAR_OUTPUTS`, including the generated
`gm1` through `gm9`, found 68 unique `TERMINAL_OUTPUT_IDS`. A case-sensitive
set comparison found zero names unique to either side and zero exact
duplicates. Case sensitivity matters: `R`/`r`, `S`/`s`, and `V`/`v` are distinct
source properties. The harness source oracle reads every declared name with
`getattr(eq, name)`; the bundle side reads every name from its produced
`merged` mapping before emitting the terminal IDs.

This establishes the denominator only for the 68 directly declared public
computed properties of `Equilibrium`. Its 14 `root_properties` are installed
dynamically by `Reactive.__init_subclass__` and carry construction/solve state;
they are outside that 68-property set. `Reactive.is_frozen` is inherited state
metadata. The class also exposes `plot`, `resample`, `to_geqdsk`, and
`serial_attributes`; the module has separate public `update_*` calculation
functions. This check makes no completeness claim for those APIs or for the
whole VEQpy project.

The name match does not test numerical values, failure behavior, provenance,
or the independent sealed same-path holdout. Existing private `.v1` comparisons
cannot substitute for strict receipts bound to the exact candidate digest.
Keep `T-DIAGNOSTICS` open until those gates are satisfied.
