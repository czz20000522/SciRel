# r43 offline installed-wheel science check (2026-09-29)

This is a bounded engineering check of the frozen fluidBW r43 **development**
wheel, not a review decision or stable release. It adds fully offline
dependency installation to the earlier source-free installed-wheel evidence.
The wheel is `0.1.0.dev5`, remains `pending_unapproved`, and its 132-document
catalog includes mixed-source material outside the 13-item review candidate.

## Inputs

The existing portable D3 bundle supplied these CPython 3.14 Windows amd64
wheels under `build/verification/fluidbw-r43-development-delivery-20260929/bundle/wheels/`:

| Wheel | SHA-256 |
| --- | --- |
| `scirel-0.1.0.dev5-py3-none-any.whl` | `927b33e4a1051d71698714b30d80dfe9da46c7647ebe25fd9c2fedfc6025deda` |
| `numpy-2.5.3-cp314-cp314-win_amd64.whl` | `2c25dfa72943e4336ddb6b0ee4277b47a0c85bede0807530ec68103bf58e2c10` |
| `scipy-1.18.1-cp314-cp314-win_amd64.whl` | `78a0d7c918e74a232394117160e7e3db503377572a45bcef8826e4ab8a35feba` |

`pip download --only-binary=:all: pytest==9.1.1` used the development
machine's configured local proxy/cache and saved these test dependencies in
`build/verification/fluidbw-r43-offline-pytest-20260929/wheels/`:

| Wheel | SHA-256 |
| --- | --- |
| `pytest-9.1.1-py3-none-any.whl` | `37a86b45efb9a47a61a36449063e8e18d0cab3161329fc099eb21783169c4f0c` |
| `pluggy-1.6.0-py3-none-any.whl` | `e920276dd6813095e9377c0bc5566d94c932c33b27a3e3945d8389c374dd4746` |
| `iniconfig-2.3.0-py3-none-any.whl` | `f631c04d2c48c52b84d0d0549c99ff3859c98df65b3101406327ecc7d53fbf12` |
| `packaging-26.3-py3-none-any.whl` | `d7193f7c8e4e93f444fde0262bf90af30e16fa0ad0ad44cb553c87339b23cd1c` |
| `pygments-2.21.0-py3-none-any.whl` | `2363c69b61c4a97c838da3b130dcd6468f4848992b21a82f2a63ec34377137d9` |
| `colorama-0.4.6-py2.py3-none-any.whl` | `4f1d9991f5acc0ca119f9d443620b77f9d6b33703e51011c16baf57afb285fc6` |

The four copied test files were byte-identical to the SciRel checkout:

| Test file under `tests/` | SHA-256 |
| --- | --- |
| `operator_contracts/test_fluidbw_r43_variants.py` | `3a03f43046f8a14019211f990425c51b7d5fce6d253defabc8f115bd965de8fa` |
| `operator_contracts/test_fluidbw_r43_kinetic.py` | `5ef4e190d9741143652bb307b8e0417c13b16900af4e2f75fc03c3948e715e7b` |
| `operator_contracts/test_fluidbw_r43_fluid.py` | `6dda2f37cfbdba0b1c458dfedf255be22648808764ff36bcab474dc7afcff335` |
| `graph_contracts/test_fluidbw_r43_graphs.py` | `b6af013333e282e49c5d4b721ee4e88d29f2716d344ffe0f08e1c0dfa6a14dea` |

## Execution and limit

A new venv at
`C:/Users/26569/.codex/outbound-runtimes/fluidbw-r43-offline-science-20260929/venv`
has `include-system-site-packages = false`. `pip install --no-index` used only
the two wheel directories above to install SciRel, NumPy, SciPy, pytest, and
pytest's dependencies. Four tests were copied outside the checkout, and
`python -I -m pytest -p no:cacheprovider -q tests` passed **51/51** in 18.08 s.
`python -I` resolved all four imported packages under that venv's
`Lib/site-packages`, with no SciRel `src` path in `sys.path`.

This verifies those exact wheel bytes on Windows CPython 3.14 without the
SciRel source checkout or inherited host packages. It does not establish
cross-platform support, OS-enforced network isolation, a formal release
dependency lock, expert approval, distribution licenses, or a trusted
CodeFusion runtime registration. `scripts/check.ps1 -Mode release` still uses
its existing `.pth` dependency exposure; this separate check does not claim
to have changed or run that release gate.
