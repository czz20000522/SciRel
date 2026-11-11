# Reception

An extraction package that passes `scripts/validate_extraction_package.py` (format in
[`docs/maintainer/supply-pipeline.md`](../../docs/maintainer/supply-pipeline.md)) reaches the
merge line. This directory holds SciRel's own rules for comparing what it brings with the
current catalog.

An accepted submission is compared with the current catalog and recorded as an
**overlap record**: `none`, `same-relation`, `convention-only` or
`wider-coverage`, with matched asset ids and a difference note. The record does
not decide a merge and carries no capability-gain claim.

Any library change is a separate SciRel decision with implementation, direct
tests, an asset contract and the usual evidence. `scripts/validate_overlap_record.py`
validates reception records.
