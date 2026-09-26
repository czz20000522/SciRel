import hashlib
from pathlib import Path

BASE = Path("review_candidates/2026-09-27-mesh-seam")
INDEX = Path("docs/evaluations/candidate-review-materials-index-2026-09-25.md")

files = ["review.md"] + sorted(
    f"proposal/{p.name}" for p in (BASE / "proposal").iterdir() if p.is_file()
)
lines = [
    "",
    "## Batch r61: KN1DPy adaptive velocity mesh + cross-mesh scalar seam (two operators)",
    "",
    f"Directory: `{BASE.as_posix()}/`",
    "Successor of batch r60: the r60 candidate files below keep their frozen "
    "r60 bytes and digests; this batch binds the new bytes.",
]
for rel in files:
    digest = hashlib.sha256((BASE / rel).read_bytes()).hexdigest()
    lines.append(f"- `{rel}` -- sha256 `{digest}`")

text = INDEX.read_text(encoding="utf-8")
marker = "## Batch r60:"
pos = text.index(marker)
text = text[:pos] + "\n".join(lines) + "\n\n" + text[pos:]
INDEX.write_text(text, encoding="utf-8", newline="\n")
print(f"index updated with {len(files)} entries")
