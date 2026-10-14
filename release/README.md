# SciRel release boundaries

SciRel has three separate records:

1. External project FINAL artifacts live on the Home E drive under
   `/e/SciRel-lab/projects/<project>/decomposition/FINAL/`. Source snapshots and
   D0-D3 work remain outside this repository.
2. The wheel line records cumulative SciRel runtime versions and exact wheel
   digests. A wheel record names the selected capabilities and the external
   project FINAL manifests consumed by that integration.
3. The documentation line records handbook/catalog versions independently. A
   documentation record may advance without rebuilding the wheel, but it must
   state the compatible SciRel API/wheel baseline.

Only the final project manifest is an intake surface. Intermediate candidates,
source checkouts, run directories, and local build scratch are not release
inputs.
