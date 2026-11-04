# KN1DPy neutral frequency development integration

Status: development baseline candidate for expert review. Base: `dc2d31c`.
The intake at `647d5db` remains `pending_unapproved`, and the designated
qualified whole-source D1 delivery root was empty on recheck. This is not
expert approval or a public release.

## Scientific boundary

Two leaves are added without a TaskGraph or hidden source construction:

- `elastic-frequency-channels` sums exactly three already-normalized,
  equal-shape profiles in caller order and returns the named frequency field.
- `neutral-total-collision-frequency` forms base + elastic + wall, then adds
  CX only when enabled. The saved wall rule is `2*vr/D` for positive pipe
  diameter and zero wall loss for zero diameter. Disabled CX ignores its
  supplied field; enabled CX requires one.

Both accept explicit caller arrays and have no direct callable dependencies.
The first can feed the second by port, but neither calls the other. SciRel
rejects boolean, string or complex conversion, requires a boolean CX switch,
and rejects non-finite derived output. These tighten the saved input/output
behavior without changing the order of finite real valid-path arithmetic.

## Saved comparison

The archived `KN1DPy-631d0bf1` implementations matched their intake SHA-256
pins: elastic channels
`7058571007eeeb435610369b3db7ed6b7b4757ba49619cd24a605e59e1f769d8`
and total loss
`69c25bd24033e3d7cdbaf2cdbc3becadd35e09a6149f8a1bfea4534c9e35bcbd`.
Seven read-only comparisons asserted the isolated SciRel `src/` import and
matched saved arrays exactly: three channel sets and four total-loss cases
covering CX on/off and zero/positive diameters.

Four separate saved-arm witnesses confirmed that it accepts a numeric string
as a channel, returns `inf` from an overflowing channel sum, treats numeric
zero as a false CX selector, and returns `inf` for wall-ratio overflow. SciRel
fails closed on those corresponding invalid/derived-output conditions.
These are bounded historical comparisons, not whole-source D1 qualification
or an independent transport-physics oracle.

## Verification

- The new direct regression failed at import before implementation and then
  passed 11 tests. It covers saved arithmetic/branch boundaries, overflow,
  shape/count checks and non-real inputs.
- `pwsh ./scripts/check.ps1 -Mode affected` selected six test files and
  passed 92 tests without full-suite fallback.
- All 40 exact documents passed runtime and executable-example validation.
  The development catalog is `partial: 40/87` at `0.1.0.dev5`; no release
  gate or wheel build was run.

Licensing, expert acceptance, version-level trust and full neutral transport
composition remain open.
