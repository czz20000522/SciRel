# fluidBW r43 first-wheel D3 user project (2026-09-29)

This run consumed the exact r43 D2 development wheel from SciRel commit
`c69a9473c7a4446efbbd36d351397ace8ce737c1`: wheel SHA-256
`927b33e4a1051d71698714b30d80dfe9da46c7647ebe25fd9c2fedfc6025deda`,
catalog root `sha256:1bd47cc5cce3155cb8ec17676eb4f0296374d85939c7396c8be9a9ee06e7cdfb`
with 132/132 exact documents. The copied wheel was installed offline into
the project's Python 3.14 venv; `python -I` imported SciRel from that venv's
`site-packages`. The [manifest](manifests/2026-09-29-fluidbw-r43-weideman-d3.json)
binds those inputs and the independent bounded D2 acceptance.

The evaluator-owned user scenario supplied already dimensionless complex
phase arguments `z` and requested the fluidBW N=64 Weideman `Z(z)`, `w(z)`
and method labels. Catalog matching selected
`scirel.kinetic.plasma-dispersion-weideman`; the nearby analytic function is
a different method without the requested branch labels. The runnable
[project](../../../build/verification/fluidbw-r43-d3-weideman-20260929/solver/README.md)
uses the selected installed callable in its ordinary entrypoint. Input values
are manufactured for this D3 case, not represented as measured plasma data.

The entrypoint delivered a 2-row baseline, then a separate 4-row result after
P2 and P3 were appended. A fifth malformed row was rejected at line 6 with
exit code 1; both earlier CSVs remained byte-identical. Restoring the valid
input and rerunning exited 0. A separate raw-CSV reader and installed-wheel
rerun checked every delivered numeric cell and method label in both outputs;
PowerShell `Import-Csv` read both files. At `z=0`, the delivered value was
`Z=1.7724538509055159i`, `w=1`, method `erfc`. The added points used the
`rational` branch. One delivery-flow regression passed; all 150 extracted
archive members matched the file manifest. The [case record](../../../build/verification/fluidbw-r43-d3-weideman-20260929/case-evidence.md)
lists the commands, hashes, checks and Agent repair of a case-insensitive
output-header collision found by `Import-Csv`.

The frozen D3 archive SHA-256 is
`125b59bbdbe29298684f4aa25aac608816d9cde00bf40d31936bba673c3a5849`.
The result is a bounded function table, not a dispersion root, growth rate,
stability verdict or arbitrary-input accuracy bound. This wheel is still
`pending_unapproved`; the earlier 47/47 no-mount container run belongs to a
different wheel, and this case does not qualify the whole fluidBW source or
grant human or public-release approval.
