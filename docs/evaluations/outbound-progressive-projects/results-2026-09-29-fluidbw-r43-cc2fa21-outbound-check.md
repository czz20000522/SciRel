# r43 corrected-wheel outbound check (2026-09-29)

This is an independent installed-wheel development check, not a scientific
approval or stable outbound release. The [manifest](manifests/2026-09-29-fluidbw-r43-cc2fa21-outbound-check.json)
binds the exact inputs and local results. The corrected wheel was extracted
from CodeFusion's saved one-file ZIP (SHA-256
`fc3300c61f5dce85de006643c9c4f2fa82518c04a319f1d4e4b209e8c310fa34`),
then copied into the local evidence directory. Both extracted copies have
SHA-256 `b1abff574c870e17dd4e24adc952ca4279561aa43adcc92250d019e42b2b3684`.

The wheel is associated with SciRel Git `cc2fa21e03fa7e5152c29f0769165863429e1693`.
D2 separately checks its package members and wheel `RECORD` against that
revision. The catalog used here is the existing 132-document development
snapshot: `release.json` SHA-256
`fece59b88ad39480a58b3c35f7678b2007a578f5918a74533f5b0cae6dfe2d02`,
root `sha256:1bd47cc5cce3155cb8ec17676eb4f0296374d85939c7396c8be9a9ee06e7cdfb`.
The matching root does not make the earlier `927b33...` wheel interchangeable
with this corrected wheel or transfer its D3 case results.

## Installed-wheel execution

An isolated Windows CPython 3.14.3 venv outside the SciRel checkout has
`include-system-site-packages = false`. `pip --no-index` installed the
corrected wheel with saved NumPy 2.5.3, SciPy 1.18.1, pytest 9.1.1 and test
dependencies. Four r43 scientific test files, byte-identical to Git `cc2fa21`,
ran outside the checkout under `python -I`: **51 passed, zero failed**. The
JUnit record is `build/verification/fluidbw-r43-cc2fa21-outbound-acceptance-20260929/science-tests.xml`.
An initial JUnit-path command error exited before test collection; the
corrected command produced the recorded 51-test result.

The same installed wheel and catalog passed local adapter discovery (four
pages), `asset.read(detail=document)`, and `callable.invoke` for
`scirel.kinetic.plasma-dispersion-weideman` at `z=0` and `z=0.5+0.25j`.
The response was strict JSON, with `erfc`/`rational` method labels and maximum
absolute difference `1.11e-16` from SciPy's `i sqrt(pi) wofz(z)` reference.
Both SciRel and its adapter resolved inside the venv's `site-packages`, with
no SciRel `src` entry in `sys.path`. The exact probe and JSON output are in
`build/verification/fluidbw-r43-cc2fa21-outbound-acceptance-20260929/`.

## Dual-chain boundary

The current isolated reviewer project has 13 r43 items, with one Weideman
`request-evidence` successor, 12 `review_pending`, one `needs_evidence`, and
zero approved. Its successor digest is
`sha256:cad374f922e0b7ea4bed6d2141244bc3b86450ee162163a46b1523c27d24c475`;
the next host export digest is
`sha256:9ed3e5d329bee9d01dc0f7f128bb55abd69bcbfdd59903da08e5a78aca37fe99`.
Those records share the `cc2fa21` candidate source identity but do not approve
or bind this mixed-source wheel as a reviewed release.

CodeFusion's ordinary-user development trace used the corrected wheel and
reported this catalog root, but its handoff does not list the owner-resolved
immutable `scirel-solving` skill revision required by the consumer contract.
The local skill file is SHA-256
`b988367cbd38fa687bcc4af33d6bd26174cda67b0de9e9c1161e14162e7bf73a`;
that file digest does not replace the missing product trace binding.

A same-tuple **technical** dual-chain check can run once D2 binds this exact
wheel, catalog, source and current review successor, and CodeFusion records
the skill revision, frozen environment, shell Tool Plan, adapter operations,
domain checks and bounded result for one ordinary request alongside an
authenticated reviewer export. A trusted release additionally needs actual
expert approvals on exact revisions, license decisions, a selected-source
wheel/catalog built from the approved dependency closure, release checks,
authorization and `v1` contract convergence. The present 132-document wheel
contains mixed-source development material outside the 13-item review slice.
