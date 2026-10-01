# KN1DPy Python/archived-IDL cross-version diagnostic (2026-09-30)

Status: both scientific source paths remain distinct and OPEN for strict D1
closure. This is a same-raw-input, cross-version diagnostic in the original
`stage1-KN1DPy-20260916T120118Z` run. It is neither an unmodified IDL oracle
nor a source-to-candidate comparison or an independently sealed IDL holdout.

The input was the older Python-path `sealed_holdout` NPZ, SHA-256
`c81aa6cc9773e062ec3962181f74cb30b120affc968d38653cf9f82c8b202192`.
The historical Python source-runtime receipt binds its 20-output result at
`lanes/CFD1-strict-oracle/attempts/src-runtime-3/evidence/source_runtime_result_sealed_holdout.npz`,
SHA-256 `ac53ecdff613437d7bd0cd3701acaf39c4dd4828b32d1139443902bdecd5752d`.
This input and result were already used in the Python-path comparison, so
they cannot serve as an unseen holdout for the newly reopened IDL target.

The eleven NPZ inputs match the archived `KN1D` raw call parameters: `x`,
`xlimiter`, `xsep`, `GaugeH2`, `mu`, `Ti`, `Te`, `n`, `vxi`, `LC`, and `PipeDia`.
The 101-point x array increases strictly; `mu=2` and `GaugeH2=0.1`.
`coordination/kn1dpy-old-holdout-export-20260930.py` (SHA-256
`1d1d504299aa3e7f9f6b5cbda8baecd60d82955663de1571c83d3b83f1124218`)
exported them in that order as little-endian float64 bytes, SHA-256
`512fbae733c916add44e132268cbbf5a3361cb2402109c49743c632cc2557f8e`.
The export metadata is `coordination/kn1dpy-old-holdout-export-20260930.json`,
SHA-256 `bec274dd2d9a8442954d50a103da6e11cdcfcd06b54808a1321f70180112e008`.
An isolated GDL read/write probe in `gdl-old-holdout-roundtrip-20260930`
returned byte-identical input (`cmp` exit 0); its receipt SHA-256 is
`1594e4c5db44e7b82e679d3fbdd56c08eb6bdb176d6a3f327335f81dd40d7996`.

Fresh attempt `gdl-old-python-holdout-20260930` used the unchanged C ABI
bridge and the two previously documented descending-grid GDL adaptations.
It used the existing GDL arm64 image with source read-only, candidate
unavailable, and network `none`. It reached `ERROR_FLAG=0` and `OUTPUT_21_OK`.
The GDL input/capture program SHA-256 is
`14b9a7d754960c8d9cdd899a51bc79bebbb9c1b35c32fc32e9be47571503a347`;
the wrapper SHA-256 is
`5581136a1469e7724fcd16c89a344a2d59215630ac39768745611c54fe892390`;
the log SHA-256 is
`b3ef294c814609a58c1b7ffdd89006e607b4fd451e9630864a6bf577cc98451f`;
and the probe receipt SHA-256 is
`bfbb9d591c9532e01def462c66c28c99baff534e96b4ae978bb3ece578ac522b`.
The 21-terminal capture SHA-256 is
`ed73daf339471859cf4fd11a55d45a2dec26068bb8c35a3e6c1a53f13fd6ef9b`.
The existing parser accepted all 21 double terminals, with 54 molecular and
61 atomic points; its derived validation JSON SHA-256 is
`cbe978c8be117e5f32ffe4142003fb11373411e05a1605ee195a73b0dd262420`.

The structured comparison is
`coordination/kn1dpy-source-version-comparison-20260930.json`, SHA-256
`f35555dcd5c92ef343230838eefbd3be34e5de9587d6e43c68e08590b82ca736`;
its parser SHA-256 is
`ec416fcd79f9bce805534ae4bfaecdd4fe93a0952b3a12e596b69804c84f7abf`.
On this exact input, the Python path returned 20 fields, including a 296-point
atomic x grid and scalar zero Lyman/Balmer values. The archived path returned
21 fields, a 61-point atomic x grid, nonzero 61-point Lyman and Balmer
profiles, and `GammaHLim=9.888935733545995e20`. Both molecular grids have
54 points, with maximum coordinate difference `4.0746156060311733e-08`.
These are source-version differences, not candidate defects. The two terminal
denominators and their version-specific contracts must be reviewed separately;
neither old 20-output receipts nor this diagnostic close the IDL 21-output
target or qualify a D2 handoff.

Scope follow-up: `evidence_out/scope_manifest_20260925_r3.json` names the
archived IDL procedure as a 21-output source version, while
`evidence_out/capability_progress_20260925_r3.json` enumerates separate IDL
target paths only for `GammaHLim`, `Lyman`, and `Balmer`. Its umbrella target
still carries the earlier Python 20-output reassembly refs and remains
`partial`. The common-named outputs are not automatically equivalent across
versions: this diagnostic already observes different atomic grids on the same
raw input. Before closing any IDL terminal path, the coordinator must bind an
IDL-specific denominator and compare all 21 declared physical outputs from
raw input through the exact source-free candidate for both canonical and an
independently sealed same-path holdout. The existing candidate ledger and
top-level graph describe the Python 20-output path; their frozen bundle digest
must not be silently rebound to the IDL claim.
