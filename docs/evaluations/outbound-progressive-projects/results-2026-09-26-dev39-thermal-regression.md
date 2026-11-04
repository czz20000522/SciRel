# Dev39 thermal-project compatibility regression

This is a software compatibility check of an existing, review-assisted
thermal-reactivity project. It is not a new autonomous Agent trial. The source
project is the frozen `stage3-reviewed.tgz` from the
[thermal-note case](results-2026-09-26-thermal-note-forward.md), SHA-256
`aed166cfcf78cc96b9d8b0a8b3bbcb2528c75eeee530d54b6370029c0a40a064`.
The copied project ran at
`D:/Users/26569/Desktop/scirel-dev39-thermal-regression-20260926/scirel-thermal-note-forward-20260926`;
the original archive was not changed.

The sole code adaptation in the copy was to rebind `IMPLEMENTATION_VERSION`
from `0.1.0.dev24` to `0.1.0.dev39` and `CATALOG_ROOT_DIGEST` from
`sha256:030f8a3704c5388e8d08d005ff8067129cb3f998926c37f7a9e0c5ce64974b90`
to `sha256:434249fe5f6df457b712992182a0d5631918a1002861db9d415723fcd86e3fca`.
The adapted `thermal_reactivity/pipeline.py` SHA-256 is
`0c35740bf74b16fc5520216cab1600bfac652e3fde1e0f95b55b6d2010a4cd32`.
The selected asset remains `scirel.fusion.bosch-hale-reactivity`; its dev39
catalog record has the same callable and 10 keV DT example as the earlier
project. This rebind prevents the output from falsely naming dev24.

The wheel came from the unapproved r65-v6 review snapshot, manifest SHA-256
`d0b70682df281647f64ca927276cf147e5fe495814752274010cd75d21140e59`:
`scirel-0.1.0.dev39-py3-none-any.whl` SHA-256
`be5a2a2b40461ded5c486d9c9689ceaaed987923b9ba428da73ab59ca1eef9b8`.
Its catalog is complete at 126/126, but `pending_unapproved`. A fresh venv
used `--system-site-packages` and installed this wheel with `--no-deps`;
`python -I` reported SciRel from that venv's `site-packages` and version
`0.1.0.dev39`. Host scientific dependencies were reused, so this is not an
offline dependency-install proof.

The first pytest attempt from a copy under SciRel's own `build/` failed at
collection because repository-level pytest configuration contaminated the
import path with the checkout's older SciRel source. The dev39 wheel itself
contains the requested module, and isolated import succeeded. The test was
therefore rerun from the external project path above, without suppressing the
original failure as though it were a product regression.

In that external copy, `29 passed`; ordinary `python run.py` exited 0. The
first-delivery `outputs/results.csv` and `outputs/summary.md` retained SHA-256
`8758acfb2ad14b1447608f0ffa64316b92dd6dbaeaa7a33464f8fa60e5b84519`
and `af9f15f8627aab06cecb0aad29833a0628eb163cea7adcaca1aff81fc493edac`.
The run generated a separately named current summary and the follow-up table;
the follow-up summary names dev39 and the exact catalog root. The independent
raw-CSV checker recomputed all five follow-up rows through the installed
SciRel callable, checked the owner note's byte binding, and reported maximum
six-significant-digit serialization relative error `4.142e-07`.

This establishes that one previously reviewed user entrypoint still runs on
the pinned dev39 development package after an explicit provenance rebind.
It does not establish autonomous model reliability, new TaskGraph composition,
physical fit validity, expert approval, license disposition or public v1
release. The original project remains a reviewed example, not a fresh
uncoached case.
