import json
from pathlib import Path

NARROWING = (
    "Declared r60 pre-review tightening: the saved arm does not gate its "
    "output for finiteness, so extreme-but-valid inputs can overflow to "
    "non-finite results; this asset fail-closes on a non-finite result, per "
    "the exact document's finite-output contract. The saved-arm divergence "
    "is pinned by a bounded regression test."
)

EDITS = {
    "scirel.kinetic.thermal-speed-scale": [],
    "scirel.kinetic.generation-density-reduction": [NARROWING],
    "scirel.kinetic.axisymmetric-neutral-moments": [],
    "scirel.kinetic.elastic-frequency-channels": [],
    "scirel.kinetic.incoming-boundary-flux-normalization": [],
    "scirel.kinetic.spatial-source-shape-normalization": [],
    "scirel.kinetic.neutral-total-collision-frequency": [NARROWING],
    "scirel.kinetic.atomic-scattered-sources-reduction": [NARROWING],
    "scirel.kinetic.molecular-scattered-sources-reduction": [NARROWING],
    "scirel.kinetic.elastic-regeneration-aggregation": [NARROWING],
    "scirel.kinetic.simple-charge-exchange-source": [NARROWING],
}

for asset_id, additions in EDITS.items():
    if not additions:
        continue
    path = Path(f"catalog/examples/{asset_id}.json")
    doc = json.loads(path.read_text(encoding="utf-8"))
    for item in additions:
        if item not in doc["identity"]["assumptions"]:
            doc["identity"]["assumptions"].append(item)
    path.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2, separators=(",", ": ")) + "\n",
        encoding="utf-8", newline="\n",
    )
    print("updated", asset_id)
