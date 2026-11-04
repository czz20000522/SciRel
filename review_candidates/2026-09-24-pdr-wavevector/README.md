# Three frozen L1 inputs: first additive SciRel candidate

This directory is an isolated review proposal. Nothing here is imported by
`src/scirel`, included in `catalog/examples`, or authorized for a wheel.

## Exact comparison view

SciRel Git base: `e3c76fc1b70ec72943e8a15cba94d09c08e7ddc4`.
The scientific source tree at that commit is
`501b84c15c37a976eeb5a6dcd48e9acf0116d1e3`. The Git change after the
earlier `accaf872` baseline affected only the extraction validator and its test.

Saved L1 root (read only):
`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`.
`l1-inventory.json` records every delivered package and its exact package
digest; its inventory digest is
`sha256:2dfdeeab08f91d0b5239b1c584cc0c151b25bbcbf08ee1418d65b65d5d842c68`.

| Project | Source snapshot/tree digest stated by D1 | Saved bundle digest | Operators | TaskGraphs |
| --- | --- | --- | ---: | ---: |
| PDRF | `55824a96fb3abdcf2ae75b15da853084fad64f603560e8523f494ee9979ffb76` | `sha256:f4d3917c570ddef800bd5babba726bfbd54c3e921f4eb6a8f6b916f376023d09` | 7 | 2 |
| PDRK | `7ceab1c6383a474ec55095c7ff19316db5c1b739855e495a6b325f0f110b39e4` | `sha256:cecf9426a96830413c943f34c1d19c401f06f73572212638d5772fbda7ec7614` | 11 | 3 |
| KN1DPy | `0f9b0e28438ed7b08cdcfd8f5cb381425a339b94a590e08353151f3a41b65982` | `sha256:87f62cf9f26af899c4f9a45e2c6ba0124eda78b6f23160addf3304e42532544d` | 84 | 21 |

The generated bundle JSON bodies are retained locally under
`build/standardization/three-l1-20260924/`; they are transport artifacts,
not a new scientific baseline. Structural inventory has zero gaps. D1's
source replay and freeze reports are provenance, not expert approval.

`pool-snapshot.json` records every locally discovered `review_pending`
snapshot: 52 exact Pleiades review units with document/code/test digests,
an older four-item Pleiades review snapshot, and a 21-item gseq snapshot.
These are 77 local rows and 73 distinct asset IDs; the four older Pleiades
IDs also occur in the newer submission. The older workflows have exact file
revisions and asset-document digests but do not expose separate exact trio
digests, so they are comparison context with an explicit material gap. The
snapshot digest is
`sha256:c383bccc25f297a963cb35ad697ef2f71d0c7ff023f13c7412b76a48da44ca6f`.
Structured route/summary and output-port searches found no wavevector match
in these local records or the maintained SciRel source. The host queue has
not been queried; before upload, compare its current full item list and
revisions and refresh this view if it differs.

## Counts and first closure

- Inventoried: **128/128** (102 operators, 26 TaskGraphs).
- Triaged with full scientific contracts: **2/128**. The other 126 retain their
  inventory rows and remain `not_triaged`, without an inferred disposition.
- Candidate ready for a bounded expert decision: **1/128**, the PDRF planar
  wavevector operator. The PDRK operator is triaged as an overlapping scan
  variant and remains unsubmitted.

The selected PDRF and PDRK operators each have no L1 asset dependencies.
Their reverse consumers are PDRF `fluid_dispersion_branch_sweep` and PDRK
`kinetic_dispersion_scan`/`pdrk_main_pipeline`; these graphs are not part of
this first review unit. Selection favors a small, useful relation with a real
cross-source comparison and observable differences in units, state, and
failure behavior. `review.md` contains the requested expert decision;
`proposal/` contains the candidate document, code and distinguishing tests.

The current `submit_standardization` requires coverage of every source asset
in one CandidatePackage. This first closure is therefore **not uploaded** by
adding placeholder units for the remaining 126. Any later sub-batch contract
must bind the parent inventory, selected IDs, remaining dispositions and
dependency closure explicitly.
