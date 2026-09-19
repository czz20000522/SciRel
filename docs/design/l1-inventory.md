# Saved L1 inventory reference probe

`scripts/build_l1_inventory.py` is an optional structural probe for saved L1
directories. It reads the source directory and writes an index; it does not copy
source code, import the projects, infer scientific fields, or replace the model's
semantic comparison with the current SciRel baseline.

## Input boundary

Each selected project is expected to contain:

```text
extraction_ledger.md
program_framework_map.md
operators/<name>/{operator.md,scientific_operator.py,test_scientific_operator.py}
task_graphs/<name>/{task_graph.yaml,graph.py,test_task_graph.py}
```

Missing files remain explicit `gaps`. A task graph's `asset_ref` entries are
recorded as dependency references and checked against the same project. The
extractor covers both block mappings (`asset_ref: ...` on its own line) and
flow mappings (`{..., asset_ref: ..., ...}`), including quoted values. YAML
`null`/`~` means that a graph-internal node has no asset dependency. Any other
reference outside `operators/` or `task_graphs/` is an explicit blocking gap. An
unresolved reference, a TaskGraph cycle, or missing direct test fails the
corresponding automated check; it is never silently dropped. TaskGraph
dependencies remain a DAG at this boundary. Checks include a machine-readable
issue code and diagnostic hint, for example `missing_direct_test_mapping`
with `discover_or_generate_test`, `unresolved_task_graph_dependency` with
`resolve_or_request_evidence`, or `task_graph_cycle` with `request_rework`.
Missing direct tests belong only to `direct_test_mapping`; they do not also
produce an `asset_records/request_rework` issue that would override the
automatable retry route. Missing contracts or implementations remain blocking
`asset_records` findings.

## Output boundary

`build_inventory()` returns an `L1Inventory` with deterministic project and
asset digests. Each asset records its project, kind, saved relative paths,
source digest, direct test path, and task-graph references. The development code
can project one project into `CandidatePackage.from_l1()` for deterministic
workflow tests, but real model integration may inspect the L1 directory directly.
Neither projection is the required semantic input format.

The CLI refuses to overwrite an existing output:

```powershell
python scripts/build_l1_inventory.py "D:\Users\26569\Desktop\归档_项目\codefusion\最小闭环压测环境" --project Pleiades --output build/l1-inventory/<new-run>.json
```

Without `--project`, the output is a multi-project inventory index for inspection.

The generated file is task-local evidence, not a standardized asset document,
an Agent protocol, or evidence of expert approval. Standardization still has to
produce exact `scirel.asset-document.v1` records and pass scientific review.

## Current stress input

The historical saved development pressure snapshot contains six projects:
`aorsa3d`, `cql3d`, `FIDASIM`, `gseq`, `KN1DPy`, and `Pleiades`. Its inventory
scan found 928 operators and 487 task graphs (1415 assets). Six concrete
blocking findings were reported across two projects and therefore keep their
candidates from becoming ready. This is historical pressure evidence, not a
claim about every current archive directory.

The currently available CodeFusion archive snapshot contains four projects:
`aorsa3d`, `FIDASIM`, `KN1DPy`, and `Pleiades`. A fresh rescan produced 423
operators, 257 task graphs, 680 assets, and zero gaps. It is a separate input
snapshot and must not be combined with the six-project totals above.

The current `材料/extracted_assets` saved-L1 root is a third snapshot. A
2026-09-19 rescan produced 920 operators and 355 task graphs across eight
projects (1275 assets, zero gaps): `aorsa3d`, `aorsa_tokamak`, `cql3d`,
`FIDASIM`, `genray`, `gseq`, `KN1DPy`, and `Pleiades`. In this snapshot cql3d
has 409 assets and gseq has 21, both with zero gaps. The older cql3d/gseq
findings below remain regression cases; they are not claims about this current
archive. The similarly named `最小闭环/cql3d` and `最小闭环/gseq` directories
are source/reference projects rather than saved-L1 roots and must not be used
as substitutes.

| project | operators | task graphs | assets | candidate gate |
| --- | ---: | ---: | ---: | --- |
| aorsa3d | 100 | 66 | 166 | automated_ready |
| cql3d | 368 | 151 | 519 | automated_rejected |
| FIDASIM | 198 | 159 | 357 | automated_ready |
| gseq | 137 | 79 | 216 | automated_rejected |
| KN1DPy | 84 | 21 | 105 | automated_ready |
| Pleiades | 41 | 11 | 52 | automated_ready |

- `cql3d` has one operator with a missing contract, implementation, and direct
  test mapping (three asset-record findings plus the derived test-mapping
  check), and one TaskGraph dependency cycle;
- The cql3d cycle is `task_graphs/N16N17输出变量族重组图 ->
  task_graphs/N9全量输出变量族重组图 -> task_graphs/N16N17输出变量族重组图`;
- `gseq` has one task-graph reference to an operator that is not present in the
  same project inventory (one dependency-closure finding).

The asset-record check promotes missing contract or implementation files to
project-level blocking findings. The second-stage executor may repair these
records or provide evidence, but it cannot clear them by returning `passed`
without corresponding asset updates.

These are input-quality findings. They do not assert that the underlying
scientific assets are wrong, and they do not create public SciRel assets.
