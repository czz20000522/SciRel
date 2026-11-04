# fluidBW r43 portable development delivery (2026-09-29)

The [portable bundle](../../../build/verification/fluidbw-r43-development-delivery-20260929/bundle/README.md)
and [single replay entrypoint](../../../build/verification/fluidbw-r43-development-delivery-20260929/bundle/replay.ps1)
are the locator for this bounded r43 D2/D3 development handoff. The archive is
`build/verification/fluidbw-r43-development-delivery-20260929/fluidbw-r43-development-delivery.tgz`,
SHA-256 `51864f4fe401b4995847bff533f26244304e0bfd264f9286337dbbd83e4f63e5`.
Its manifest binds 177 portable files; the archive contains those files and
the manifest as 178 individually verified members. It can be extracted
outside the SciRel checkout and replayed from there.

This selects the exact `0.1.0.dev5` wheel SHA-256
`927b33e4a1051d71698714b30d80dfe9da46c7647ebe25fd9c2fedfc6025deda`
and matching catalog root
`sha256:1bd47cc5cce3155cb8ec17676eb4f0296374d85939c7396c8be9a9ee06e7cdfb`.
Those bytes remain in the frozen graph D3 handoff and were actually consumed
by the Weideman and physical-input TaskGraph D3 cases. The later `cc2fa21`
adapter wheel has SHA-256
`b1abff574c870e17dd4e24adc952ca4279561aa43adcc92250d019e42b2b3684`;
its identical `dev5` version label does not make it this wheel or transfer
the two D3 case results to it. D2's current development release-index
governance distinguishes candidate and released entries from a catalog
snapshot. This bundle is not a released index entry. The catalog has 132/132
exact documents but includes historical provisional material beyond the
qualified r43 slice. Its state remains `pending_unapproved`.

For Windows amd64 CPython 3.14, the archive includes SciRel, NumPy `2.5.3`
and SciPy `1.18.1` wheels with explicit hashes. The public wheel declares
`numpy>=1.24` and `scipy>=1.10`; the packaged wheels are one tested installable
resolution. `replay.ps1` verifies the bundle and all 135 catalog partitions,
creates or refreshes a venv outside the bundle with `--no-index`, checks all
147 installed SciRel package files against the exact wheel, and runs both
saved D3 cases and their separate raw-input readers. The two primary skills
are `scirel-solving` for scientific request normalization and execution, and
`scientific-project-implementation` for working project delivery. Their
`scientific-asset-navigation` helper and relative reference documents are
included. These methods do not themselves approve or release an asset.

The actual test used a new venv without system site packages. `python -I`
resolved SciRel, NumPy and SciPy from that venv, then produced four CSVs
byte-identical to the prior frozen results: Weideman 2-point baseline and
4-point current table, plus physical-input graph 1-point baseline and
2-point current table. The same entrypoint passed after the archive was
extracted under `C:\Users\26569\.codex\outbound-runtimes\` outside the SciRel
source tree. This closes the external install/replay gap for this Windows
runtime and exact case, without rerunning D1/D2 source qualification. It is
not a cross-platform or long-duration availability result.

The [manifest](manifests/2026-09-29-fluidbw-r43-development-delivery.json)
binds the archive, wheelhouse and replay entrypoint. Both examples use
evaluator-manufactured input, not measured plasma data. They are function
evaluations at finite points, not dispersion roots, growth/damping rates or
a stability verdict. Neither the development bundle nor its replay replaces
expert science approval, license decisions, approved-item to wheel binding,
or final release verification.
