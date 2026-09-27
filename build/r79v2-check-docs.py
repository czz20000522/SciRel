import hashlib
import json
import pathlib

snap = pathlib.Path("build/verification/review-2026-09-27-r79-neutral-merge-family-v1")
manifest = json.loads((snap / "manifest.json").read_text(encoding="utf-8"))
docs = manifest["exact_documents"]
assert len(docs) == 166, len(docs)
mismatch = 0
for entry in docs:
    live = pathlib.Path(entry["path"])
    digest = "sha256:" + hashlib.sha256(live.read_bytes()).hexdigest()
    if digest != entry["sha256"]:
        mismatch += 1
        print("MISMATCH", entry["path"])
print("exact documents checked:", len(docs), "mismatches:", mismatch)
assert mismatch == 0
