# Skills by role

SciRel has three roles. Each has one entry skill and its own acceptance standard. An agent reads the entry skill for its role and follows it.

| Role | What it does | Entry skill | Done when |
| --- | --- | --- | --- |
| **Supplier** | Extracts scientific functions from a source project as self-contained candidates | [`scientific-computation-asset-extraction`](extraction/scientific-computation-asset-extraction/SKILL.md) | The packet passes `scripts/validate_admission.py` against [`contracts/admission`](../contracts/admission/README.md) and carries boundary tests and evidence |
| **Merger** | Brings candidates into the library: admission, contract, tests, review, documents | [`scirel-integration`](development/integration/scirel-integration/SKILL.md) | [`scirel-acceptance`](development/scirel-acceptance/SKILL.md) is green, code follows [`scirel-code-style`](development/scirel-code-style/SKILL.md), and the contract, implementation and tests agree |
| **Consumer** | A user's agent answers a question with the delivered package | [`scirel-solving`](development/usage/scirel-solving/SKILL.md) | The report passes its validator and a physicist can follow it; [`scirel-outbound-evaluation`](development/scirel-outbound-evaluation/SKILL.md) measures this for maintainers |

## Audience

- **`development/usage/`** is delivered to every user's agent. It holds only general method and speaks to any user. It never mentions evaluation, cases, repository files or catalog sizes.
- **Everything else** is for maintainers and suppliers and is not delivered.

## Supplier

| Skill | Use |
| --- | --- |
| `extraction/scientific-computation-asset-extraction` | Entry: D0 and D1 extraction |
| `extraction/scientific-operator-review` | Review one extracted operator |
| `extraction/scientific-relation-implementation` | Implement one relation |
| `extraction/scientific-d2-decomposition`, `extraction/scientific-d3-decomposition` | D2 and D3 stages |
| `extraction/scientific-requirements-extraction` | Requirement cases from a source |

## Merger

| Skill | Use |
| --- | --- |
| `development/integration/scirel-integration` | Entry: integrate candidates |
| `development/integration/scientific-asset-normalization`, `scientific-asset-correctness`, `scirel-review-preparation` | Steps it routes to |
| `development/scirel-acceptance` | Local checks for every change |
| `development/scirel-code-style` | Code style and public API rules |
| `development/api-design-method` | The general method for reviewing and improving an API |
| `development/scientific-computation-validation`, `development/scientific-runtime-dataset-construction` | Validation and dataset routes |
| `development/scirel-outbound-evaluation` | Test the delivered package with clean agents |
| `development/post-acceptance-runtime-cleanup` | Clean up after a run |

## Consumer

| Skill | Use |
| --- | --- |
| `development/usage/scirel-solving` | Entry: the five-stage solving method |
| `development/usage/scirel-capability-discovery` | Find and read contracts |
| `development/usage/scirel-result-validation` | Check a result before delivery |
