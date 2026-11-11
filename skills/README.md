# Skills by role

SciRel has three roles. Each has one entry skill and its own acceptance standard. An agent reads the entry skill for its role and follows it.

| Role | What it does | Entry skill | Done when |
| --- | --- | --- | --- |
| **Supplier** | Extracts a source's core relations into an extraction package in SciReL's final form | [`scientific-computation-asset-extraction`](extraction/scientific-computation-asset-extraction/SKILL.md) | The package's patch passes the full check on the frozen commit, and its manifest and disposition reconcile with the relation count |
| **Merger** | Brings extraction packages into the library: package checks, contract, tests, review, documents | [`scirel-integration`](development/integration/scirel-integration/SKILL.md) | [`scirel-acceptance`](development/scirel-acceptance/SKILL.md) is green, code follows [`scirel-code-style`](development/scirel-code-style/SKILL.md), and the contract, implementation and tests agree |
| **Consumer** | A user's agent answers a question with the delivered package | [`scirel-solving`](development/usage/scirel-solving/SKILL.md) | The report passes its validator and a physicist can follow it; [`scirel-outbound-evaluation`](development/scirel-outbound-evaluation/SKILL.md) measures this for maintainers |

> Supply and integration are currently frozen: no new assets are accepted while the backlog is paid down. See [AGENTS.md「当前状态」](../AGENTS.md#当前状态).

## Audience

- **`development/usage/`** is delivered to every user's agent. It holds only general method and speaks to any user. It never mentions evaluation, cases, repository files or catalog sizes.
- **Everything else** is for maintainers and suppliers and is not delivered.

## Supplier

| Skill | Use |
| --- | --- |
| `extraction/scientific-computation-asset-extraction` | Entry: skeleton, comparison, final-form implementation, extraction package |
| `extraction/scientific-requirements-extraction` | Independent: capability problems for the problem bank |

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
