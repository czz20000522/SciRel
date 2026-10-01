# PDRK W23 runner canary review veto (2026-09-30)

Status: W23 is sealed but **not accepted**. The root-owned seal proves that the
attempt and handoff were retained; it does not satisfy the independent terminal
review gate for new controlled worker dispatch.

The exact lane is `stage1-PDRK-20260919T214903Z/lanes/W23-runner-v1-canary`,
attempt `runner-v1-canary-20260930-02`. Worker exit was 0 and the sealed-attempt
receipt recorded the handoff SHA-256
`412b85e0f00b32f7d06a805c9ab9769252654585eed597e1a09ab8feb203d230`.
The immutable versioned reviewer at
`tooling/stage1/versions/handoff-20260929-v1/review-worker.py` has SHA-256
`e1c4c0a0c93f7ae4161d8f2fcdfba184e8707dd6e07fcf37cd2aef64dcd97455`.
An independent invocation without changes to the worker lane saved
`coordination/reviews/w23-runner-v1-canary-supervisor-independent-rejected-20260930.json`,
SHA-256 `5970ffc940324869e48f6edb81f92748a50f7167c863463368376c183f2fa1d9`.
Its verdict is `rejected`: 32 of 34 checks passed, and two failed.

- `expected_artifacts_bound_to_handoff`: the packet's expected
  `scratch/candidate-digest-observation.json` (SHA-256
  `e4496637bb7f5996fcd865c4b941f5c4775318621fabecb406f0ec6c7d9b0459`)
  and `scratch/canary-probe-output.txt` (SHA-256
  `b6dbf5ff396bfaca43d9f725bcde063675b9dcab95f19ee2c55a66cad64e609a`)
  have no SHA-256 bindings in `handoff.evidence`. The probe receipt itself is
  bound correctly.
- `source_anchor_digests_match`: the immutable W23 packet has no nonempty
  `frozen_inputs.source_anchor_sha256` map, which this versioned reviewer
  requires even for a runner-identity canary.

W22 and W23 remain historical attempts. Do not edit their packets, handoffs,
receipts, or sealed content to turn this into a pass. A fresh packet, work item,
and attempt must bind real source anchors and all expected artifact digests,
then pass the same independent reviewer on the newly sealed attempt. At each
new launch, bind the then-current candidate digest and check live slot capacity.
Until an accepted terminal review exists, cql3d r1 stays unassigned; the
PDRK scientific targets, including fixed J-pole, retain their strict
canonical plus independent sealed holdout requirements.

The 2026-09-30 user decision explicitly keeps
`T-PDRK-JPOLE-GENERATOR` open under that two-axis gate. No canonical-only
exception or validator change is authorized; the fixed `J=12`/`I=16`
canonical case alone does not close the target.

An older `RUNNER_CANARY/stage1-runner-contract-prod-20260928` attempt has an
accepted review from 2026-09-28. A read-only replay with the frozen
`handoff-20260929-v1/review-worker.py` on 2026-09-30 also returned `accepted`
with no failed checks or warnings. This checks the retained handoff's structure;
it does not establish that the versioned runner launched that historical
attempt. Its recorded launcher SHA-256 was
`4d5ecc27a2417cb3b31f98164503a495f440a011d7a803ec0ffbd480b0555c49`,
whereas the frozen versioned launcher is
`2aed0eff8f6641eceaeea6284bc8b68ab6179ebbcf759281b8baf31b07ec6237`.
That historical replay grants no scientific or dispatch credit.

The fresh `W26-runner-v1-canary` subsequently ran through the frozen
`handoff-20260929-v1` runner on the exact d34 candidate. Packet SHA-256 is
`392b57ce48f8470a721be4e0716c334395e0a48e7b9fd1d810cb82fcc2973c15`.
The worker exited 0 and the root-owned sealed receipt SHA-256 is
`eb4bde298aea2d0f320f5b5b4f406a607e0cee2e58f8d2537fe56d672e1a3471`.
The saved independent versioned review SHA-256 is
`8f5e4283cc128217a32fc478b82cf12b102fe48cf8150f98de256e9b5ef65f0d`;
its verdict is `accepted` with no failed checks or warnings. A separate
read-only invocation of the same frozen reviewer also returned `accepted`.
W26 proves the frozen versioned runner can execute and pass terminal review.
Whether that stack is the authorized launcher for cql3d r1 remains under
contract review; its packet pins the deployed probe wrapper but no launcher
path. Before cql3d r1 dispatch, its coordinator must resolve that runner
identity, then recheck live slot capacity, its own packet SHA-256, source
identity and anchors, candidate digest, and fresh attempt. No PDRK scientific
status or cql3d source comparison transfers from this canary.
