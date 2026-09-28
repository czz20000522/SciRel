# fluidBW r43 physical-input TaskGraph D3 successor (2026-09-29)

This same-project successor keeps the frozen [Weideman D3 case](results-2026-09-29-fluidbw-r43-weideman-d3.md)
read-only and adds a physical equilibrium-to-determinant chain under
[`solver/graph/`](../../../build/verification/fluidbw-r43-d3-graph-successor-20260929/solver/graph/README.md).
The old archive SHA-256 remains
`125b59bbdbe29298684f4aa25aac608816d9cde00bf40d31936bba673c3a5849`.
Inputs are evaluator-manufactured, not measured or supplied user data.

The exact `0.1.0.dev5` wheel SHA-256 is
`927b33e4a1051d71698714b30d80dfe9da46c7647ebe25fd9c2fedfc6025deda`;
its matching catalog root is
`sha256:1bd47cc5cce3155cb8ec17676eb4f0296374d85939c7396c8be9a9ee06e7cdfb`
(132/132 exact documents, `pending_unapproved`). Catalog routing and the
graph/dependency exact documents selected
`scirel.kinetic.kinetic-dispersion-relation`: one equilibrium-scales node
feeds the finite-harmonic and Ronnmark determinant paths at the same derived
wavepoint. Its public API supplies the physical `omega`, `f` and `kx` from
the caller's SI state, `omega_fraction` and `kx_fraction`. The graph is a DAG;
`kz` is an absolute nonzero parallel wave number. No source checkout,
CodeFusion service, database or network is used by the science call.

The wheel was installed offline into an external Python 3.14.3 venv.
`python -I` resolved SciRel from that venv's `site-packages`; NumPy and SciPy
were inherited with `--system-site-packages`, so dependency installation was
not hermetic. The one-point G0 baseline was retained separately from the
two-point G0/G1 result. The two result files are byte-identical for G0.
At G0, the graph returned `omega=431047494.35601676 rad/s`,
`f=68603339.43413593 Hz`, `kx=656.5372832698083 m^-1`, sum determinant
`84156144001125.875+29822940983252.742j`, and Ronnmark determinant
`84154917089965.141+29822444270111.691j`. At G1,
`omega=718412490.59336126 rad/s` and the determinants are
`13174325513551.053+8828415003972.582j` and
`13173663914380.654+8828066693749.1387j` respectively.

The ordinary entrypoint checked finite `(3,3)` tensors and finite scalars,
plus the graph's `omega/wn`, `kx/kn` and `f=omega/(2*pi)` connections. A
separate raw JSON/CSV reader reran all delivered cells through the installed
graph; Windows `Import-Csv` read both files. A malformed appended row failed
with exit code 1 while both prior result hashes stayed unchanged. Corrected
ordinary-entrypoint rerun reproduced the current CSV byte for byte. The
focused delivery regression passed 1/1 and compared both determinants with
the pre-existing finite two-species source references at `rel=1e-12`.

The frozen successor archive SHA-256 is
`e2723c8b729a90067fbafc0e3e1facd34cfe0f6b79d8b8d84c87a4cd8b0778bc`;
all 165 members passed individual hash and size checks. The
[case evidence](../../../build/verification/fluidbw-r43-d3-graph-successor-20260929/graph-case-evidence.md)
records commands, values and checks; the [manifest](manifests/2026-09-29-fluidbw-r43-graph-successor.json)
binds the exact artifacts. These are determinant evaluations at given
wavepoints, not roots, growth/damping rates or a stability decision.
Agreement between the two methods is not an error bound. No arbitrary-input
source parity, whole-fluidBW qualification, human approval or public release
follows from this case.
