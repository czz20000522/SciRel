# TORAX D2 profile-leaf closure: algebra/grid decision

This bounded D2 increment retains five distinct TORAX relations after comparison
with the current SciRel tree. No exact SciRel duplicate has the same ports,
units, assumptions, or failure behavior: midpoint interpolation has no mesh
coordinate port, dilution exposes `Z_eff` and impurity charge, and the three
Coulomb logarithms have distinct collision pairs and coefficients.

The source anchors are the retained Apache-2.0 TORAX snapshot
`8cd1184007c82ff379d118b2ad22753358820fe5`, tree
`1a77b880c34fb333aa1910350967b107f41521c8`:

* `torax/_src/geometry/geometry.py:face_to_cell`, SHA-256
  `cae147cb1cb4cdb59e0f8a5756592ec768751099d62771008095aa53617faa90`;
* `torax/_src/physics/formulas.py:calculate_main_ion_dilution_factor`,
  SHA-256 `825c3730c8d7d057b82de2ac716b0d8588fb1098c14e995470c039c098ded10d`;
* `torax/_src/physics/collisions.py:calculate_log_lambda_{ee,ei,ii}`,
  SHA-256 `2c85c1dca99fd140f1ecc29df6129c6f5a837212f51bf3a1e1f6e1cf6fd20980`.

Independent SciRel tests verify hand algebra, broadcast shapes, endpoint and
singular domains, smallest-subnormal midpoint behavior, finite endpoint
overflow avoidance, and stable Coulomb evaluation at large finite
temperatures. The source's implicit invalid-value behavior is made explicit:
invalid inputs raise `ValueError`, and an otherwise finite input whose output
cannot be represented raises `FloatingPointError`. Coulomb results are
mathematical weak-coupling estimates; positivity/adequacy for a particular
collision model remains a caller precondition.

The retained source and comparison records remain read-only. These documents
are development exact records pending later human decisions and release
binding; they do not claim TORAX project completion or physical calibration.

Human decision points for this increment are bounded to the five records:

* retain all five as separate identities under their current module paths;
* accept the explicit SciRel `ValueError`/`FloatingPointError` boundaries as
  the maintained successor behavior;
* retain the supplied Apache-2.0 license and TORAX attribution in the selected
  distribution; any release decision remains separate from this source-license fact.

The evidence supports these implementation and contract decisions only. It does
not approve the source project, widen the weak-coupling Coulomb applicability,
or admit a full TORAX wheel.

Receiver documentation successor
-------------------------------

The receiver retains the exact scientific equations, units, domains, failure
contracts and examples of the five final records. Public provenance now states
the supplied Apache-2.0 license fact. Private review, human decision and release
status belong on this review page and in the separate qualification record.
The original author records remain available without modification.

The author's final-review document hashes predate the final documents. The
receiver therefore binds and reviews the actual final bytes separately. The
source report also contains a 41-character tree identifier; the empty receiving
checkout establishes the actual 40-character tree
`f8db14726742fcebf0b60261ef209fb56157672e` for source commit
`f21a878998abd74e6812f57d8bb8891641fecfc6`. This source repair is separate from
the five API source anchors above.

The five scientific identities require explicit human decisions before final
approval. Acceptance of this internal selected package is not human approval,
publication approval, full TORAX D2 completion, or D3 application validation.
Previously recorded source failures and unqualified families remain open.

The final input dtype descriptions explicitly distinguish the required
one-dimensional face vector from scalar-shaped main-ion charge. This clarifies
the existing verified shape contract; it changes no numerical implementation.
