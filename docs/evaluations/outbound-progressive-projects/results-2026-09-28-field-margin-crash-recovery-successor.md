# Field-to-margin historical-byte retry successor (2026-09-28)

An independent review of the prior D3 freeze found a P2 in its interrupted
delivery recovery. After complete A and B deliveries, input C produced the
same vacuum CSV bytes as A and new margin bytes. Delivery stopped between
the canonical replacements. The C retry restored both CSVs but omitted
`vacuum__inC.csv`: an older A delivery with the same result hash hid the
missing C record. The reviewer's [reproducer](../../../build/verification/d3-independent-review-20260928/reproduce_historical_bytes_retry.py)
and [observation](../../../build/verification/d3-independent-review-20260928/historical-bytes-retry-observed.json)
are bound in the new [manifest](manifests/2026-09-28-field-margin-crash-recovery-successor.json).

The successor was derived from the unchanged predecessor archive (SHA-256
`e0851619a1d7ab1da438f3b336787bfca352af8af7384d9cb34d126a652b99b9`).
Its new regression failed on that frozen implementation, then passed after
the delivery check began comparing the current canonical bytes with the
same file's **latest** recorded delivery. Earlier matching bytes no longer
stand in for the interrupted C write. The test also verifies that a second
C retry leaves the manifest unchanged. Existing pressure-only cases still
avoid redundant vacuum records.

Focused history and entrypoint tests passed **15/15**. The ordinary dev58
entrypoint exited 0; independent CSV reading found four rows in each output,
and an unchanged-input rerun kept both result files and the manifest
byte-identical. The [successor record](../../../build/verification/field-margin-crash-recovery-successor-20260928/successor-evidence.md)
details the commands and result hashes. The new archive SHA-256 is
`b491bf9a9713e8566eef93c2381b1aeb071941d59bcc746da1da3a455fb0128b`;
all 375 extracted members matched its file manifest.

An independent recheck by `/root/workflow_independent_review` (model and
version `unknown`) found no remaining issue in this A/B/interrupted-C retry
scope. Its [script](../../../build/verification/d3-independent-review-20260928/recheck_successor_historical_bytes_retry.py)
and [observation](../../../build/verification/d3-independent-review-20260928/successor-historical-bytes-retry-observed.json)
confirm both C delivery records, byte-identical normal B and second C retries,
and unchanged predecessor and successor archive hashes. The manifest binds
both recheck files by SHA-256; the review reused the 15/15 test and 375-member
freeze evidence.

This closes the reported A→B→C retry case. It does not make two-file
replacement crash-atomic or change the scientific relations, pending-unapproved
dev58 wheel, earlier freeze, or the project's sampled-arithmetic claim limit.
