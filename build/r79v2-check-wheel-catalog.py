import hashlib
import json
import pathlib

snap = pathlib.Path("build/verification/review-2026-09-27-r79-neutral-merge-family-v1")
manifest = json.loads((snap / "manifest.json").read_text(encoding="utf-8"))
expected = manifest["wheel"]["sha256"]
live = "sha256:" + hashlib.sha256(
    pathlib.Path("build/wheel-r79/scirel-0.1.0.dev56-py3-none-any.whl").read_bytes()
).hexdigest()
print("wheel frozen:", expected)
print("wheel live  :", live)
assert live == expected

live_catalog = json.loads(
    pathlib.Path("build/catalog/r79/release.json").read_text(encoding="utf-8")
)["root_digest"]
frozen_catalog = manifest["catalog"]["root_digest"]
print("catalog frozen:", frozen_catalog)
print("catalog live  :", live_catalog)
assert live_catalog == frozen_catalog
print("R79-V2-WHEEL-AND-CATALOG-BYTE-IDENTITY-PASSED")
