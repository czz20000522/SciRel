# SciRel decomposition skill bundle

## 来源侧需求题库

[`scientific-requirements-extraction`](scientific-requirements-extraction/SKILL.md)
是独立入口：从冻结源码、论文与案例盘点物理能力，
估算需求题数量与投入，并生成来源中立的题面、私有参考复现及覆盖缺口记录。
它不审查算法正确性、不接收入库，也不自动恢复 D0–D3 拆解；不属于下述固定七入口交付包。

## D0–D3 拆解包

This directory is the standalone D0-D3 decomposition package. Give the bundle,
the target project and an authorized Codex/Claude execution environment to a
worker; the result is a digest-bound decomposition packet for a separate
development owner.

The extraction `SKILL.md` is the first instruction an extraction worker reads.
It carries the phase card, dynamic probe, boundary-test matrix and handoff
requirements. The reference files explain a method when a step needs detail;
they are not a substitute for the executable skill protocol.

The D0/D1 entrypoints preserve source intake, extraction, operator review and relation implementation. Computation validation and runtime dataset construction are shared canonical routes under `../development/`; extraction calls them in D1/source-fidelity mode. The two stage entrypoints add D2 claim decomposition and D3 application observation. They emit raw material and evidence only. They do not import a development checkout, merge candidates, modify a user project, approve, publish or release.

Stage standards live in this skill bundle. The final submission is governed by
SciRel's admission contract (`contracts/admission/`): one `decomposition/FINAL/`
directory with `FINAL.json`, `FILES.json`, `PATH_MAP.json` and `ROOT.sha256`, no
version-suffixed schema and no required D0-D3 package records. See the live
receiver contract in `../contracts/admission/`.

A bundle digest proves the payload, not scientific truth or downstream acceptance.
