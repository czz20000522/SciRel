# r43 corrected-wheel ordinary-user successor (2026-09-29)

This [development manifest](manifests/2026-09-29-fluidbw-r43-b1ab-current-ordinary.json)
continues the [source-free installed-wheel check](results-2026-09-29-fluidbw-r43-cc2fa21-outbound-check.md).
It records one real CodeFusion ordinary-user request on an isolated development
service. It is not scientific approval or stable outbound acceptance.

The request used SciRel source `cc2fa21e03fa7e5152c29f0769165863429e1693`,
corrected wheel SHA-256
`b1abff574c870e17dd4e24adc952ca4279561aa43adcc92250d019e42b2b3684`,
and catalog release SHA-256
`fece59b88ad39480a58b3c35f7678b2007a578f5918a74533f5b0cae6dfe2d02`
(root `sha256:1bd47cc5cce3155cb8ec17676eb4f0296374d85939c7396c8be9a9ee06e7cdfb`).
The admitted input ZIP has SHA-256
`74bbb6d0ec371361a09c55572f353ae8ead33e3b4f35befcf56b570b8c75e17f`.
SciRel rehashed the saved ZIP and both wheel/catalog members. The qualified
r43 L1 ZIP was imported into the same project; its SHA-256 is
`166021e28d6aa6db71b61daff7e3671837f3dede218b41153b4c0d3186cb83bd`.
The L1 freeze does not approve the scientific assets.

CodeFusion source `2d3de66e04d81fcbb94fd069bb7f4d93630cd844` completed
ordinary request `appreq_f9ab1cd4d20826bb_a76d533b66556885` in project
`prj_38c6934b8953fb6651c4e3797e2c0029d3ce` with 27 completed operations.
The CodeFusion owner inspected that request's first kernel checkpoint: it froze
owner-resolved `scirel-solving` revision content digest
`sha256:9bdb51487d777807914e547fb965c37c832f7cf639c718dc5306cec820015220`,
environment version
`envver_ec473521fb8360a86cc4accc15e89a30e78240fc674677dd28cb9cdfff2929e6`,
and a Tool Plan containing `shell`, revision
`tool-plan@sha256:bddc07f3c1841e72be221bcd2987648966d0bc215f2eb34431892a8576c4e09d`.
All 22 shell calls carried that plan; the input ZIP was mounted read-only
under its exact digest. This closes the preceding record's missing same-request
skill/environment/Tool Plan trace for this development case. The full
owner-scoped skill URI remains in the host's local receipt, not in a SciRel
public science contract.

SciRel rehashed the locally saved project script (SHA-256
`4cb19947a848ee4c71c71f9fa7569d8305ce8a2abda82ffd631e99d4fd161da7`)
and result JSON (SHA-256
`582b6e6508654e5d7410630110ad4cb576126ef1a00128c504750b6ca5e1c823`).
The result records two `catalog.discover` pages covering 132 assets,
`asset.read(detail=document)` for Weideman, and two `callable.invoke` calls.
Both numerical checks against SciPy `wofz` passed, with absolute errors 0 and
`2.482534153247273e-16`. CodeFusion owns authentication, checkpoint and
product-state verification; SciRel's local inspection does not independently
authenticate the live service.

The reviewer project's latest host export remains 13 items, one
`needs_evidence`, 12 `review_pending`, and zero approved. Its review plugin
installation has not been bound to this `b1ab...` wheel. The ordinary-user
trace therefore closes one technical gap but does not complete a same-tuple
reviewer/ordinary acceptance. Expert decisions, license clearance,
approved-subset wheel/catalog construction, release checks and `v1` contract
convergence remain prerequisites for stable distribution.
