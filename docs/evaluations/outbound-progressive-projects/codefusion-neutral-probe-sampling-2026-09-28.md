# Dev58 probe-sampling neutral-host handoff

Status: ready for a controlled CodeFusion host comparison using the same
development science package and user materials. This is a task-specific
evaluation handoff, not a product contract or scientific approval. The SciRel
Claude result, including autonomous divergence and two rescues, is recorded in
[the manifest](manifests/2026-09-28-unseen-probe-sampling-dev58.json) and
[result record](results-2026-09-28-unseen-probe-sampling-dev58.md).

## Exact materials

- Opening package:
  `build/verification/unseen-probe-sampling-20260928/examiner/neutral-stage1.tgz`,
  SHA-256 `d99e7d06fa65835a770745c661deca73a12730d3f654dfb82a3872799e3a5684`.
  Its 185 files contain `request_stage1.txt`, five initial `input/` files,
  `host-assets/` with the dev58 wheel and 169/169 catalog, and three `method/`
  bodies. Install the bundled wheel locally if needed; do not use SciRel source,
  CodeFusion internals or a network service for the scientific function.
- Later package, withheld until the first delivery is frozen:
  `build/verification/unseen-probe-sampling-20260928/examiner/neutral-stage2.tgz`,
  SHA-256 `470ecf35132ebeeb8356195ce5b91ce90409aa994e15a01e7f01739428a3696e`.
  It contains only `request_stage2.txt`, `input/probes.csv` and
  `input/pressures.csv` (3 files).
- The Claude evaluation envelopes are
  `examiner/evaluation_prompt_stage1.txt` (SHA-256
  `f89d9d9994ddf7e0a7ed2885333fadcc6b808d46a6f98f79d418e60ada66cc5e`)
  and `examiner/evaluation_prompt_stage2.txt` (SHA-256
  `a11575d35be2d69948af0bb6a29634c40dfea5358c491cc28be210480183ac9c`).
  Preserve the two user requests verbatim; the host may adapt only the
  tool-access wrapper.

The wheel SHA-256 is
`60ce811067e2c808b7ed0176bdb4572bf8bea322badc40b7eca3e8f42bc7090a`.
The catalog root digest is
`sha256:61bb7e828098e244a0285bfb772f59a9f43e3d3576caa907d9ca769c09e5ae4d`.
The frozen r81 manifest SHA-256 is
`a9924e8926ad240b1e6c3aaaf57cc2896a262c3776ea33daa786cd6884ab4dc0`.
All 169 assets are `pending_unapproved`; only the multi-coil contract and
three direct dependencies received bounded independent review.

## Two-stage sequence

1. Give the agent only the opening package's files and the first user request.
   Record its answer, outputs, ordinary rerun path, tool failures, questions,
   scientific claims and any intervention. Freeze the first project before
   opening the later package.
2. Add the three later files to the same project and send the later user request
   unchanged. Record the first second-stage result before any clarification.
   Do not provide `expected.json`, the examiner scripts, the prior solver
   project, or the two rescue prompts to the agent.
3. If the host or user clarifies the meaning of "sampled field", record that as
   a separate rescue turn and keep the initial interpretation and output. If a
   format or project defect needs a later repair, count it separately.

CodeFusion owns the chat, project files, tool execution, permissions and
artifact presentation. SciRel owns the scientific meaning of the wheel,
catalog and methods. A direct wheel call within a host project can establish
neutral workflow evidence; it does not by itself establish a complete
`ThinMcpAdapter` discover/read/invoke product path.

## Examiner checks

The first-stage table has 9 grid points for each of two settings. The
pre-generated examiner oracle combines a direct installed-wheel port-mapping
check with an independent on-axis Biot-Savart loop witness. The later files
contain four probe IDs and pressure rows deliberately out of order; joins
must use `(setting, probe_id)`, not row position. The pre-bound comparison
samples the first grid componentwise with four-corner bilinear arithmetic,
then computes `B_R^2 + B_Z^2` divided by `4*pi*1e-7 H/m` plus the supplied
pressure difference. The point at `r=35 cm` lies outside the grid and may be
reported unavailable. A host that directly recomputes the vacuum field at
each probe has made a different, physically meaningful interpretation; retain
it and count a later interpolation clarification as assistance. Keep the
first-stage grid result accessible.

The examiner oracle and scripts are under
`build/verification/unseen-probe-sampling-20260928/examiner/`; they are for
assessment after each delivery only. The final Claude project archive is
separate evidence and must not be used as a host starter.

Return the actual host/model/runtime labels, exact package hashes, first
failure and rescue count, runnable entrypoint, result files, independent
checks and remaining limits. Neither a green project test nor a matching
number establishes plasma equilibrium, stability, device validity, expert
approval, public release or complete CodeFusion integration.
