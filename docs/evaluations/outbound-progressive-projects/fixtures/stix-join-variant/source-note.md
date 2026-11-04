# Synthetic local plasma tables

The three species labels in `settings.csv` refer to the IDs in `species.csv`; join by ID, not row order. A row's density and collision rate apply only to that species in that setting. The baseline densities are charge-neutral for the stated ion charges. All values and units are explicit in the file headers. The Cartesian field vectors and returned tensors use the same laboratory x-y-z basis; no field-aligned transformation is requested. The time convention is exp(-i omega t).

This is invented locally uniform cold-plasma data, not a measurement of a device. No wave electric field, propagation solution, boundary condition, power deposition, or heating measurement is provided. The frequency rows are discrete evaluation points, not a continuous-band accuracy guarantee. Species charges and masses are rounded reference values recorded for this synthetic fixture.
