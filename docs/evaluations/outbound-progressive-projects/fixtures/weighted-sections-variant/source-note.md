# Synthetic section data

These are invented axisymmetric rectangular winding sections, not measurements of a device. Each `total_kA_turns` is the signed ampere-turn total for one section in one setting. The rows in `filament_shares.csv` partition that section's total among its representative circular filaments; their shares sum to one per section. Indices are zero-based. A positive sign follows the model's positive toroidal-current convention; the outer section is driven oppositely. The grid axes and sites are in cylindrical metres.

The requested ideal vacuum result excludes plasma current, material and finite-conductor effects. No accuracy or uncertainty estimate for a physical device is supplied. The files specify no continuous-domain error bound between sampled locations.
