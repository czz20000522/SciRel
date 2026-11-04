# Thermal-unit clarification: progressive Claude Code evaluation

This synthetic evaluation asked a nonprogramming user to obtain a reusable
Maxwellian fusion-reactivity table from a CSV with two explicit keV rows and
two blank-unit rows. An unsigned legacy note said the blanks might be eV or
keV. A later turn supplied a simulated export-owner confirmation scoped to a
new five-row CSV. The [manifest](manifests/2026-09-26-thermal-note-forward.json)
binds the exact inputs, unapproved SciRel dev24 wheel and 74/74 catalog,
skills, three project archives, raw Claude traces, examiner mutations and
independent checks. Claude Code `2.1.281` ran the two user turns and one
review turn in session `27ab3f38-0280-4c96-b5be-96b3b3a403b2`. No model
flag or call/fee limit was passed. CLI init said `claude-fable-5`, assistant
events said `GLM-5.3-Flash`; the underlying model was not confirmed. Examiner
and solver files were separated by directory, not OS permissions.

The first **autonomous** turn found the host-mounted catalog and selected
`scirel.fusion.bosch-hale-reactivity`. It computed only the two explicit keV
rows, left gamma/delta without numbers, and asked one consequential question
about their temperature unit. It did not invent fusion yield or power. The
second **autonomous** turn read the owner's follow-up note, applied eV to the
three named blank cells, converted 5000/12000/15000 eV to 5/12/15 keV, and
called the SciRel asset for all five rows. The first CSV and summary retained
their original SHA-256 bytes. In a source-free SciRel-wheel environment,
17/17 project tests passed; a separate checker recomputed all five values
from raw CSV and the installed SciRel callable at the output's six-significant-
digit precision (maximum relative rounding difference `4.142e-07`).

The autonomous result was **not** a complete pass. The [independent stage-2
finding](../../../build/verification/thermal-note-forward/independent-stage2-finding.txt)
preserves three negative tests, with exact mutated project copies:

- A later sentence from the same simulated owner withdrew gamma's eV claim.
  The project noticed changed note bytes but still reported gamma as computed
  at 5 keV; its regex prose parser treated the old positive sentence as
  authoritative.
- Changing only the production eV-to-keV factor to `1/100` left the ordinary
  "source-to-port witness" green and produced gamma at 50 keV. Its witness
  compared two CSV parses, not the actual port sent to SciRel. The external
  raw-input checker rejected the result.
- Changing the original alpha input from 10 to 11 keV made the ordinary
  follow-up command overwrite both first-delivery files while saying their
  content was unchanged. Its test compared against the already current file.

One [review message](../../../build/verification/thermal-note-forward/review-feedback-1.txt)
fed back those symptoms and the intended boundary: an Agent interprets the
current prose once, while ordinary code validates a structured, source-bound
claim and exact runtime mapping. The [reviewed
archive](../../../build/verification/thermal-note-forward/stage3-reviewed.tgz)
contains `input/owner_interpretation.json` with named rows, the quoted
assignment and note digest. Its runtime does not parse arbitrary changed
English into a new scientific claim; changed note bytes require a human or
Agent to re-derive the declaration. The SciRel call wrapper records actual
ports, which are checked against a separately derived raw-CSV expectation
before follow-up files are written. Historical first-delivery bytes are kept;
changed first input generates separately named rerun files. Unsupported
fit-domain confidence wording was removed.

In a separate extraction of the reviewed archive, 29/29 project tests and
the ordinary Python entrypoint passed. The [independent stage-3
check](../../../build/verification/thermal-note-forward/independent-stage3-check.txt)
and its frozen check copies show all five output values match the installed
SciRel relation, with the two old SHA-256 values unchanged. Reapplying the
same three mutations now caused: exit 1 and unchanged follow-up outputs on
note withdrawal; exit 1 with the explicit `5 keV` versus `50 keV` port
mismatch and unchanged follow-up outputs on wrong conversion; and a new
digest-suffixed result with the original CSV/summary untouched on changed
first input. This is **one-review-assisted bounded repair**, not autonomous
success on source provenance, mapping witness or result ownership.

The owner confirmation is simulated user-supplied information, not an
independent physical measurement. Binding a declaration to exact note bytes
does not prove that the note is true or that an Agent will interpret another
note correctly. The checker tests mapping to the dev24 relation and output
serialization, not the physical accuracy of the Bosch-Hale fit, fuel density,
power or device yield. The wheel/catalog are unapproved development assets,
not a trusted/public v1 release. There was no CodeFusion integration. The
reviewed project gives separate historical rerun filenames but does not
define a general multi-file transactional run-ID contract. Existing SciRel
skills already asked for source-linked claims, actual-port witnesses and old
result preservation; these failures are method adherence evidence, not a
reason to add another universal gate from this one fixture.
