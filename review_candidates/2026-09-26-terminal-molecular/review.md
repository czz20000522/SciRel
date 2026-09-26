# Candidate: KN1DPy terminal molecular diagnostics family (six operators)

Status: development candidate prepared for expert review, to be frozen as
the pending_unapproved r65 successor of r64. Nothing here is expert
approval, a trusted version, or a public release.

## Base and comparison scope

- SciRel base: `c8c3a988` (r64-v3, convergence/accumulation family, 120
  assets dev38, `pending_unapproved`).
- Unpublished candidate pool: re-checked by relation for terminal molecular
  flux/velocity, pressure/temperature, heat flux, energy transfer, ion
  state, or conservation diagnostics — none exists. All six incoming
  leaves are **new capabilities**.
- Incoming source (read only): the saved KN1DPy bundle
  `D1待重审历史产物/KN1DPy-631d0bf1` (provisional; strict D1 withdrawn),
  six operator packages, each implementation pinned by SHA-256.
- Qualified L1 consumption: none (delivery root empty; strict D1
  withdrawn). Bounded historical development evidence only.

## Inventory

| Saved callable | Disposition | Proposed SciRel identity | Material differences |
| --- | --- | --- | --- |
| `reduce_terminal_molecular_flux_velocity` (`kinetic_h2.py:1610-1625`) | add new capability | scirel.kinetic.terminal-flux-velocity-reduction | **no repair** — GammaxH2/VxH2 from cylindrical quadrature |
| `reduce_terminal_molecular_pressure_temperature` (`kinetic_h2.py:1630-1690`) | add new capability | scirel.kinetic.terminal-pressure-temperature-reduction | **no repair** — pH2/TH2 with source constants |
| `reduce_terminal_molecular_heat_flux` (`kinetic_h2.py:1693-1760`) | add new capability | scirel.kinetic.terminal-heat-flux-reduction | **no repair** — qxH2/qxH2_total |
| `reduce_terminal_molecular_energy_transfer` (`kinetic_h2.py:1700-1780`) | add new capability | scirel.kinetic.terminal-energy-transfer-reduction | **no repair** — QH2 energy transfer |
| `reduce_terminal_molecular_ion_state` (`kinetic_h2.py:1800-1868`) | add new capability | scirel.kinetic.terminal-ion-state-reduction | **no repair** — nHP/THP/NuDis/NuE |
| `reduce_qh2_total_conservation_diagnostic` (`kinetic_h2.py:1755-1790`) | add new capability | scirel.kinetic.terminal-conservation-diagnostic | **no repair** — QH2_total conservation error |

Relations kept distinct: each produces a different diagnostic from the same
terminal distribution, with different output types and target quantities.

## Composition and analytic evidence

- Composition test: heat flux `total_heat_flux_profile_w_m2` + energy
  transfer `total_energy_transfer_rate_profile_w_m3` -> conservation
  diagnostic, asserting finite [nx] error profile.
- Analytic conservation oracle: linear qx(x)=a*x+b with constant Q=a gives
  exactly zero error.

## Files

Six modules, 2 test files, 6 exact documents under `proposal/`.
Version `0.1.0.dev38` -> `0.1.0.dev39`; catalog 120 -> 126.
