# Candidate review-material index (r56)

The freeze script originally bound review materials to tracked `docs/*.md`
files only, so the expert-review entry point for each integration batch --
the candidate document, its comparison inventory (README) and the proposal
files under `review_candidates/` -- is not listed in any snapshot manifest
material list, even though the frozen commit tree contains the bytes. This
index binds those files by exact SHA-256 at the batch's freeze commit so the
manifest chain points an expert to them. Since the r66 v3 freeze the script
also accepts exactly `review_candidates/<batch>/review.md` and
`review_candidates/<batch>/proposal/*.py|*.json` as `--review-material`
arguments, and the r66 batch's seven candidate files are snapshotted directly
in `review-2026-09-27-r66-alpha-contraction-v3`. Every entry path is relative
to its batch Directory and resolvable from it (verified by script after the
r55 path correction); any drift between a digest below and the working tree
means the candidate text changed after this index was written and the batch
needs a successor, not a silent edit.












## Batch r76: FIDASIM DCX/HALO iteration-feedback family (one operator + one bounded sequence graph)

Directory: `review_candidates/2026-09-27-halo-iteration-feedback/`
Successor of batch r75: the r75 candidate files below keep their frozen
r75-v2 bytes and digests; this batch binds the new bytes.
- `review.md` -- sha256 `169e650f6748807b54d51fc15dbf9c9b464f4a7daf0bb8e673cdb5402c39c46e`
- `proposal/halo_iteration_feedback.py` -- sha256 `94b6add329557bb9f574b2880965620507d966a8c6228cb4557119daf68d0560`
- `proposal/halo_iteration_feedback_sequence.py` -- sha256 `4108066910e3bfc887f6b8624ec90912b4d15338365c2c54485b537a96efe3ec`
- `proposal/test_halo_iteration_feedback.py` -- sha256 `453a49f06eeb742fbe7eefca24a31235ff926413a52e04a4294d3066aa49686a`
- `proposal/scirel.fusion.halo-iteration-feedback.json` -- sha256 `ec4992310954bd9db039f1b01652628990bb77b1089d81d60a8517828250d646`
- `proposal/scirel.fusion.halo-iteration-feedback-sequence.json` -- sha256 `c2ccb9a4095bff2b6295fb12652500cbdacb7c2116e669ec1c4b5010d6cdc2a6`

## Batch r75: FIDASIM NBI source-geometry family (two operators + one task graph)

Directory: `review_candidates/2026-09-27-nbi-source-geometry/`
Successor of batch r73 in this index: the r73 candidate files below keep
their frozen r73 bytes and digests (r74 was a wording-only round with no
candidate packet; r75's science bytes were frozen as r75-v1 at commit
`6f57c69` before this packet existed, so this index binds the packet bytes
at the r75-v2 evidence-only successor freeze, which snapshots them directly
as review materials).
- `review.md` -- sha256 `c11d94039fe8d9f841fb70c0cbfc8a201b75986fe82338c30366fccfa05a3eac`
- `proposal/nbi_source_plane_ray.py` -- sha256 `1f0d49ce4cdd1e24a8d3c63a4386b997571bbca1b4a043a6fb95a010d22159de`
- `proposal/beam_grid_ray_intersection.py` -- sha256 `b3d8a93de492f8b1a1df32bf8a0a7c3186767cbd2392448ecc8fe9612cd3a279`
- `proposal/nbi_trajectory_initialization.py` -- sha256 `5ec1bb75cbcc3d50326dfe785f9d3ae698341dfa6c4e6be8de12d6cd69e7344f`
- `proposal/test_nbi_source_geometry.py` -- sha256 `9dc368c413829ef0d701ef86238e9f0c6e757c56cbba72290c6d1edb9c3d19c3`
- `proposal/test_graph_nbi_trajectory_initialization.py` -- sha256 `0e0b9cb8730975f78b534c07e279c6f28ad5edf15b13e81ac77815d5777fbbaa`
- `proposal/scirel.fusion.nbi-source-plane-ray.json` -- sha256 `78b5ca56783bb6f6ccdf09f06d2d96598a8c7e5c8a92a24a000cf19aa889619f`
- `proposal/scirel.fusion.beam-grid-ray-intersection.json` -- sha256 `d7a6cc760da64430e512c05851bb67163972c8e66e1b1212b6837f1f78bf66c9`
- `proposal/scirel.fusion.nbi-trajectory-initialization.json` -- sha256 `0dde8f74df59a6264f6282f57748d8287974cab86b3165df99b61db42c907365`

## Batch r73: pointwise firehose-margin relation (one operator)

Directory: `review_candidates/2026-09-27-pointwise-firehose-margin/`
Successor of batch r72: the r72 candidate files below keep their frozen r72 v3 bytes and digests; this batch binds the new bytes.
- `review.md` -- sha256 `230a013a90658b97eae5cc0679e4c0e5fd282bf1a4e5ae6303837b7b64516079`
- `proposal/pointwise_firehose_margin.py` -- sha256 `9f622a0527ae31788158b6f7e1b6fa7e0af696cd3508f317005cdb628fa6bba2`
- `proposal/test_pointwise_firehose_margin.py` -- sha256 `447e9101a379076f60b6b6e82937895e947db2e38de90bc6609b7fcac10d70e1`
- `proposal/scirel.diagnostics.pointwise-firehose-margin.json` -- sha256 `a011d39533006cfe3ee0124fa2b734e756f039d91ea45d400d92ae1947eefb63`


## Batch r72: FIDASIM cross-node leaf family (five operators)

Directory: `review_candidates/2026-09-27-cross-node-leaves/`
Successor of batch r71: the r71 candidate files below keep their frozen r71 v2 bytes and digests; this batch binds the new bytes.
- `review.md` -- sha256 `b1db6b3c3762c7767555432985a6d1d482c600800ee42908e113a5a123c53ae6`
- `proposal/dd_rate_table_interpolation.py` -- sha256 `c840d5051f013f170d67819b256f4d399a38fe6d105df7f7f1a61dcb29f40b68`
- `proposal/fast_ion_relative_energy.py` -- sha256 `29a4f0c5f61c57c746dbbe15fa5610f15e12301691bc074171276e70dba095ff`
- `proposal/mc_marker_weight_allocation.py` -- sha256 `9d751ea51949b32608e95506611a8e7f8b8024ab9c51fc39d6a86da70a885139`
- `proposal/nbi_cell_directed_ray.py` -- sha256 `be045ae284bd1ec4f1fec71f9b99c57d3979a17087d0e9fd83fb7891b0198fcb`
- `proposal/nbi_injected_neutrals_normalization.py` -- sha256 `98167771be31a9592e38f603e34c1ccd5131f7a0faf789c119710dda1c6ab4de`
- `proposal/scirel.fusion.dd-rate-table-interpolation.json` -- sha256 `5e65c05906fdb310704580b9aaa1f123e0b11057dee80378fcffefd93d9ee555`
- `proposal/scirel.fusion.fast-ion-relative-energy.json` -- sha256 `bf990a879e1ef069ba087f22fe848f797502a9ce54314112ce758e348fb167a4`
- `proposal/scirel.fusion.mc-marker-weight-allocation.json` -- sha256 `b107bbf994e34204ee3b83bb908e6bf75e22a7b09958896b4336eaa8d61887a1`
- `proposal/scirel.fusion.nbi-cell-directed-ray.json` -- sha256 `6d7ca0dd17acc4ee9c0be4d550e7bfdec0cc0cd403f16c848c8545d11609545d`
- `proposal/scirel.fusion.nbi-injected-neutrals-normalization.json` -- sha256 `a47e75dabf5b6ace9c58a5df5a4a5e3b0ececebca70d3a01ed03f3b6442bcd06`
- `proposal/test_cross_node_leaves.py` -- sha256 `d86883545ee5cf3da9fb1f3409efaf54634c91e5bb4005fe0f5a5f04597fdafe`

## Batch r71: FIDASIM fast-ion/neutral cross-node leaf family (five operators)

Directory: `review_candidates/2026-09-27-nbi-birth-leaves/`
Successor of batch r70: the r70 candidate files below keep their frozen r70 v1 bytes and digests; this batch binds the new bytes (r70-v3 is the comparison baseline).
- `review.md` -- sha256 `ad82f6b8559e7b5719257f05251b9775cb1cce60036e6dfe9735509e58f19932`
- `proposal/beam_grid_cell_sampling.py` -- sha256 `0058dd2e7e4b47bd3c79f6812c8c8e7e55fc3504c37d3c553d8d75d88717bdb8`
- `proposal/halo_velocity_sampling.py` -- sha256 `a4c101f750eb41a1edde6beb794397fd744a8ac0c0f0bd0e54e9ea4eb827352b`
- `proposal/nbi_component_initial_state.py` -- sha256 `ec1eaaed29b6b0c0d6f7416d05583ae9defc0a6083488dc78ed335e3a6671dd9`
- `proposal/nbi_energy_component_velocity.py` -- sha256 `1aa61f268ed6ed0a3be349149d0f8a2db4d7e8ba53959c86747c2d7843039dd8`
- `proposal/pitch_gyro_direction.py` -- sha256 `a4ac289c8932d45a37b7103008db41cdb54f335029fcea119d4efda3204601fb`
- `proposal/scirel.fusion.beam-grid-cell-sampling.json` -- sha256 `a52bf837fa4c148faa2c8459ddc4df54dc2f660892e1ceefbb4f4ea8f6a22124`
- `proposal/scirel.fusion.nbi-component-initial-state.json` -- sha256 `ebbe425fb1110548f39ed7db6c8017a254b51f396c393de4f45baff26e6a5d91`
- `proposal/scirel.fusion.nbi-energy-component-velocity.json` -- sha256 `2b15c5682d20378db3fe97b5c45a634d1ab8ad95a70f63674a71319e390ba102`
- `proposal/scirel.fusion.pitch-gyro-velocity-direction.json` -- sha256 `135defbed548bd4cd778e779ebc9fa483491667cf4b215c96183e383d6ddcbb8`
- `proposal/scirel.fusion.thermal-halo-velocity-sampling.json` -- sha256 `219015acf1faaed581104ae7ef02cbca94cc0d5918f2c6a39888a3e162c8e4d4`
- `proposal/test_nbi_birth_leaves.py` -- sha256 `3f975c3db1e858b57e7490c2017f741c0945fdbdd92b627e8a34e3961c0610de`

## Batch r70: FIDASIM fast-ion kinematics family (two operators; DD lab energy reused, no new identity)

Directory: `review_candidates/2026-09-27-fast-ion-kinematics/`
Successor of batch r69: the r69 candidate files below keep their frozen r69 v2 bytes and digests; this batch binds the new bytes.
- `review.md` -- sha256 `c90bd63ec45e981d859a9381cd7a6068eb4c612dc17d14bfb6e71c035b7bc6ed`
- `proposal/dd_neutron_kinematic_anisotropy.py` -- sha256 `713809f148888d7b9dbb16d262e9cb3ef91ae1a406c3335c8c0db1573d7baa03`
- `proposal/first_order_larmor_correction.py` -- sha256 `9d9cbf88b2dd4b4b51fbe6123429fc6184eda50a90e3489f5a0f8eda3fbc2acb`
- `proposal/scirel.fusion.dd-neutron-emission-anisotropy.json` -- sha256 `b84312ef8bde0524ea9f926270716d1b1a55d4e5cf25ec35ead6ecacdbaeeaa3`
- `proposal/scirel.fusion.first-order-larmor-correction.json` -- sha256 `5bbd776e7a91dc84b93e2ee1cc5a58ff739775d952e6338d9cf4154d4719a494`
- `proposal/test_fast_ion_kinematics.py` -- sha256 `d25903db3e23cf9fd95523d9ca3d8aac0b27fb56c533382dca2994306a4f6e14`

## Batch r69: GSEQ filament-coil Green family (three operators)

Directory: `review_candidates/2026-09-27-gseq-green/`
Successor of batch r68: the r68 candidate files below keep their frozen r68 v1 bytes and digests; this batch binds the new bytes.
- `review.md` -- sha256 `ffe26453061a662d49c519e3896e975fe24c29e0962806f6171a1d429bb41eab`
- `proposal/coil_green_geometry.py` -- sha256 `e4bebba8a4acf5f75ca565a2644abbbc8615ec1210a3b2d6bd7d27a87d1f8098`
- `proposal/complete_elliptic_integrals_approx.py` -- sha256 `07a2b468c38a2cb8569f4a34913632cad029d90d65e6a1007cb5634cf0c8e90e`
- `proposal/filament_coil_green_field.py` -- sha256 `76ed8621d21e85f91e5e2a2036a418d638fd50db1e07563b6c600783f3e0dff6`
- `proposal/scirel.field.coil-green-geometry.json` -- sha256 `4f08c91065143d831f956cf28a32d3a870fed3fd0fee044085cc928e57f46b0b`
- `proposal/scirel.field.complete-elliptic-integrals-approx.json` -- sha256 `f692854493a0c7d0353036ef871b51738938331a73316f2f7c63706bfdee7396`
- `proposal/scirel.field.filament-coil-green-field.json` -- sha256 `5e53e55005ba3679c08fa5bf371b80fcbfdd791aae0d046d4d5ac67b37818db3`
- `proposal/test_filament_coil_green_gseq.py` -- sha256 `33de0db701e6cee1de7bc502d6825ea5b55289f5cea3b2a97e581b5a2310b287`

## Batch r68: KN1DPy Omega aggregation family (two operators)

Directory: `review_candidates/2026-09-27-omega-aggregation/`
Successor of batch r67: the r67 candidate files below keep their frozen r67 v1 bytes and digests; this batch binds the new bytes.
- `review.md` -- sha256 `d9f3998430c6bff3963d38d0de7fc207aa6ec2da3be6d214231a994bd124054e`
- `proposal/atomic_omega_aggregation.py` -- sha256 `0bc27000e23ee28759d358f4a71c6c5f2bd49ab279d172223bdc780fcb48c63f`
- `proposal/molecular_omega_aggregation.py` -- sha256 `90361f9016d19846bf47b053b2e856b3f6bc676005560873ea9bab2761b0b6fa`
- `proposal/scirel.kinetic.atomic-omega-aggregation.json` -- sha256 `494e8fae0bc1611efa6c777886c858b1c6ef10b842407138b7e9bee2b8a7bc4a`
- `proposal/scirel.kinetic.molecular-omega-aggregation.json` -- sha256 `ff3a61b19a2919a1f7cde7de33e0c152cbf787a450e99bcb35a88b1585b74523`
- `proposal/test_omega_aggregation.py` -- sha256 `405ff413b3a099df684a3342429a8b9372d694e8d933c933b4924f6bdf02a31e`
- `proposal/test_omega_aggregation_l1.py` -- sha256 `c90d290b6147552315d1b1c2d2c7e3c133433c9e42703a78047cb16f245f2692`

## Batch r67: KN1DPy collision-matrix assembly family (two operators)

Directory: `review_candidates/2026-09-27-collision-matrix-assembly/`
Successor of batch r66: the r66 candidate files below keep their frozen r66 v3 bytes and digests; this batch binds the new bytes.
- `review.md` -- sha256 `09baa7128df4e1605856431fedd899b226f8296f9a2a02097c93aebbcbedb408`
- `proposal/atomic_collision_matrix_assembly.py` -- sha256 `a93bb9168d6652be8f89e1a08753a000afa6e93f32bed49606b43d6cc587af27`
- `proposal/molecular_collision_matrix_assembly.py` -- sha256 `64873059223ee93229b9feaa477a347f81968275e54fdf2616b90d2717199585`
- `proposal/scirel.kinetic.atomic-collision-matrix-assembly.json` -- sha256 `db18d0e796befc029946d7cf1b8d0f9b988e22b3d3f062f1087797c9bb2e69a5`
- `proposal/scirel.kinetic.molecular-collision-matrix-assembly.json` -- sha256 `604e61e9493d19f314907a09da5cd976707cbfc2ef73af404873c86c4b5b0bcc`
- `proposal/test_collision_matrix_assembly.py` -- sha256 `570f79c7e4c546bbe330abcb08bef3ba92d58bce793a1b81870193c260441f43`
- `proposal/test_collision_matrix_assembly_l1.py` -- sha256 `1aff6826a60147c9246315b59a83433f947a5871160596eb3d655c854bc28e01`

## Batch r66: KN1DPy collision frequency contraction family (two operators)

Directory: `review_candidates/2026-09-27-alpha-contraction/`
Successor of batch r65: the r65 candidate files below keep their frozen r65 bytes and digests; this batch binds the new bytes. r66 v1 (`review-2026-09-27-r66-alpha-contraction-v1`) froze the r66 bytes listed here in their original form; the v3 freeze (`review-2026-09-27-r66-alpha-contraction-v3`) binds the corrected bytes below and snapshots all seven files directly (v2 is preserved but superseded: its freeze script allowed any tracked file under `review_candidates/`; the tightened rule admits exactly the same 7-file set).
- `review.md` -- sha256 `89bfd2d64db6c5d986cdf6c83a4f00457901f4c2bda6b4282746f9c82450eb6b`
- `proposal/scirel.kinetic.atomic-alpha-contraction.json` -- sha256 `956b2a9136440f12f9bb08d2559b36c9887c9ad6d389fd4c44e952a8e62bbc79`
- `proposal/scirel.kinetic.molecular-alpha-contraction.json` -- sha256 `baad00637887f9cbed6bbe9c1ad0ad3f9c4c8c1a8516233c23d56bd9f7f40464`
- `proposal/atomic_alpha_contraction.py` -- sha256 `3cc121f1325fd9faaa58e566f6d5d6a98544247cb9fa20d8b208ea792efe7a34`
- `proposal/molecular_alpha_contraction.py` -- sha256 `9bac6b3857d3dee377a77b6ac29ace02efee4ff0287618e67f1a8c6837b7f4ce`
- `proposal/test_alpha_contraction.py` -- sha256 `2d53ba24395a362a1c49d16a53abf5a8cb2f1757d406a5ce725c62adecdb7712`
- `proposal/test_alpha_contraction_l1.py` -- sha256 `c6ac9dc550757aef8823d3a28d924ee84bf4efcb4db3fd7447208ebca59502b5`

## Batch r65: KN1DPy terminal molecular diagnostics family (six operators)

Directory: `review_candidates/2026-09-26-terminal-molecular/`
Successor of batch r64: the r64 candidate files below keep their frozen r64 bytes and digests; this batch binds the new bytes.
- `review.md` -- sha256 `96d9dfebe222842d819d8b7f8245c084c2c9fed1f1800d414ebcaeb3469dc5d2`
- `proposal/scirel.kinetic.terminal-conservation-diagnostic.json` -- sha256 `c53a3f87af24b8e6c07948e6a724192c2ccb330d1c4c855401c366dabdd1b2e2`
- `proposal/scirel.kinetic.terminal-energy-transfer-reduction.json` -- sha256 `44358a0c23e833380941949d1808518790af7a76898f3ba8bc43dba836bb5ec0`
- `proposal/scirel.kinetic.terminal-flux-velocity-reduction.json` -- sha256 `c0c2a7af06c49db3421864b61f90a3ee6ead398857150e3acccefe4730a15d4e`
- `proposal/scirel.kinetic.terminal-heat-flux-reduction.json` -- sha256 `599f187a152733f79502a81b7d8312b3b2b0f928518953f66d8ec03755b360c7`
- `proposal/scirel.kinetic.terminal-ion-state-reduction.json` -- sha256 `1f40e027c63b0980af608b37cb926ba023a1158c3b72fd863956293e4ce6eb0a`
- `proposal/scirel.kinetic.terminal-pressure-temperature-reduction.json` -- sha256 `1d5b5c0b54c0d77e05e26293be1b7370bb8cfeb51def3d93669eb453e0b18e15`
- `proposal/terminal_conservation_diagnostic.py` -- sha256 `258ef36f7d265f5a7cc08f021cbf91fbd83ad9ce6876a1c56d1064655d4c2af3`
- `proposal/terminal_energy_transfer_reduction.py` -- sha256 `da8da87c2030fadcb2c21cd7ae064398dbf91aeb461a591d11a641ccdc5b44b3`
- `proposal/terminal_flux_velocity_reduction.py` -- sha256 `73dfe7df71e537f35c69d9ac7470303501fb933c43eced6772e915498f873ea9`
- `proposal/terminal_heat_flux_reduction.py` -- sha256 `46e9c00fb9cce1f2d6e82efa83a176a91500ea06c00de4f224aa2a337bdf7aeb`
- `proposal/terminal_ion_state_reduction.py` -- sha256 `a04b3049e4d33af713eb5632f88135777e683f7df257dfc061c8a853c06edb57`
- `proposal/terminal_pressure_temperature_reduction.py` -- sha256 `5574ec2415d1df7cddc373432f82553c23595b61620ce9689b093dc39c8a116a`
- `proposal/test_terminal_molecular.py` -- sha256 `6677c9b66e1b5c97fc1c869ae75b6d1af900ec15f0c3a8003e652f678f262d2e`
- `proposal/test_terminal_molecular_l1.py` -- sha256 `2ebf2c68c56a019e8ea438c252c2de2ce4f4a885be018a5c811f3bea4058cf18`

## Batch r63: KN1DPy transport-step family (three operators)

Directory: `review_candidates/2026-09-27-transport-step/`
Successor of batch r62: the r62 candidate files below keep their frozen r62 bytes and digests; this batch binds the new bytes.
- `review.md` -- sha256 `725c7596e30cae86c8117386ea6699b4de80165a550f9cf9cb5bbcf4b8ee4050`
- `proposal/neutral_boltzmann_rhs.py` -- sha256 `9ccae2821f3cdf0006a15d2d852d218e557089f4b8962df6d2e90d959f20c6b5`
- `proposal/neutral_generation_propagation.py` -- sha256 `460b1f1f351b49de30d4e7a03cea2d590b286842284499b0c619268d1ba99a8e`
- `proposal/scirel.kinetic.neutral-boltzmann-rhs.json` -- sha256 `1d9c0284416bc9f08c104a36d48bfd8f40b6e8a2f61634fc3ba2192da7b14bec`
- `proposal/scirel.kinetic.neutral-generation-propagation.json` -- sha256 `9bcd1b40c1179749114ccee7f02e7783950ee57319f4e9427eef8328fdecc44d`
- `proposal/scirel.kinetic.neutral-upwind-transport-coefficients.json` -- sha256 `91321bcef01becbffcda76cdfbe1c5affb44287df34b4c034a7987ee76cd759a`
- `proposal/test_transport_step.py` -- sha256 `3382fcc219aa058b014841bc361c9717739cf058831891fedff3eb54e8093a74`
- `proposal/test_transport_step_l1.py` -- sha256 `8dec764e96e2b1384c6255b07d3a4dbfa02d25596e9fe49c7dc7fc58e8d5a743`
- `proposal/upwind_transport_coefficients.py` -- sha256 `13b496fe0bb7a8b163aa699d6c2ab56ea6f3c4535ca78b723939121cd7a881cd`

## Batch r62: KN1DPy cross-mesh distribution interpolation (one operator)

Directory: `review_candidates/2026-09-27-mesh-seam/`
Successor of batch r61: the r61 candidate files below keep their frozen r61 bytes and digests; this batch binds the new bytes.
- `review.md` -- sha256 `b6c5b7d9be704daa5c49366a08939bae54d8c89659a51bdf57aade1d7166200b`
- `proposal/adaptive_neutral_velocity_mesh.py` -- sha256 `9f4c925f768179309fcdc77845bce15e99a7bb55a3b7e0252958395290fdc069`
- `proposal/cross_mesh_distribution_interpolation.py` -- sha256 `0119dc7655d5e5bcec42db6d48f6a1afba6d775c4d86ab89e4384bb7b869bd0a`
- `proposal/cross_mesh_scalar_interpolation.py` -- sha256 `b7ae07ac9b02645ebc2261054823f2a70b8ca394708d41734b8dba2950164ad2`
- `proposal/scirel.kinetic.adaptive-neutral-velocity-mesh.json` -- sha256 `4ed7a942e1cf6325b15887d2c7a9bd414d0b16029c4e9513bc47c5cc7e04f8a2`
- `proposal/scirel.kinetic.cross-mesh-distribution-interpolation.json` -- sha256 `b1ccd63791a1372530474969895c49f20896475f4762ddf61fb20838d1e14e6e`
- `proposal/scirel.kinetic.cross-mesh-scalar-interpolation.json` -- sha256 `8601d76c545b1fb7d444319210f3d04a4c0fa011f2a5c51b88e56ee3e7939d7a`
- `proposal/test_cross_mesh_distribution.py` -- sha256 `3c24a5ebad54818fc20a0dd685e1664763d6393dca3645d565fc7d8ef7a9c1fb`
- `proposal/test_cross_mesh_distribution_l1.py` -- sha256 `331022eb4934433bf12998958263b8535878e30e050235fbb445c3b0259832ab`
- `proposal/test_mesh_and_seam.py` -- sha256 `b567cd015176ee06e5f99b694fd6130c8695c55016aaaa46f4b1c84defc85db1`
- `proposal/test_mesh_and_seam_l1.py` -- sha256 `d6fe9485034d53d4b7283e6cc3033ce5f591732211d4b8b4629c8a4b74554bb4`

## Batch r61: KN1DPy adaptive velocity mesh + cross-mesh scalar seam (two operators)

Directory: `review_candidates/2026-09-27-mesh-seam/`
Successor of batch r60: the r60 candidate files below keep their frozen r60 bytes and digests; this batch binds the new bytes.
- `review.md` -- sha256 `e3974f0cdc54331feefc4d94ba55da536095eb8e7f9ec91638b61d7b1ea99f1e`
- `proposal/adaptive_neutral_velocity_mesh.py` -- sha256 `4fee650ce4ff79c14a1fcba08fef6d2a4cddfb9422c0155b3351c75732e52157`
- `proposal/cross_mesh_scalar_interpolation.py` -- sha256 `d0d221fed33cca709f987e582f4dc26e5ec80973125b5932efad74ee1a536933`
- `proposal/scirel.kinetic.adaptive-neutral-velocity-mesh.json` -- sha256 `bad9469a3ae3d0e2beb17befc673d88728cf6a78c93d1d68406ed7c1ddf64f8a`
- `proposal/scirel.kinetic.cross-mesh-scalar-interpolation.json` -- sha256 `1acd915dd64c447d4ac48cff24f62d96dfa1ca9e5bba5d3ed763038782f51faa`
- `proposal/test_mesh_and_seam.py` -- sha256 `9e301431a5881924477f8d4bc5faa1119e4668ebcb721e7162162e2da57e2dcb`
- `proposal/test_mesh_and_seam_l1.py` -- sha256 `d6fe9485034d53d4b7283e6cc3033ce5f591732211d4b8b4629c8a4b74554bb4`

## Batch r60: KN1DPy neutral-moment diagnostics family (eleven operators)

Directory: `review_candidates/2026-09-26-neutral-moments/`
Successor of batch r59: the r59 candidate files below keep their frozen r59 bytes and digests; this batch binds the new bytes.
- `review.md` -- sha256 `77860b8c5e0c58b59d863792de27431a5186fd5f37623d3d69e1384ea127c0cc`
- `proposal/atomic_scattered_sources_reduction.py` -- sha256 `2add8a48273ccda8ccc98a6efc5ac375671c264c2c2e9a6eb78d81ac796213b6`
- `proposal/axisymmetric_neutral_moments.py` -- sha256 `a1b2e460bc89872d802a51474698e3e8eb160aa57db43dedb796a940f4a0adb6`
- `proposal/elastic_frequency_channels.py` -- sha256 `e68b718635e07dac5c5a0ecd3c190d0e3856c6e228d1c4c66b3510e6bede8ea5`
- `proposal/elastic_regeneration_aggregation.py` -- sha256 `e7711eca11016548c44d9d5146ffea2e3dea8d8472dab3e14d2a9354d4a4f1f6`
- `proposal/generation_density_reduction.py` -- sha256 `8dfa16d9a38f417d80d40e265dc28ab536a77dac600fa519bdfad5b83c1a7fa3`
- `proposal/incoming_boundary_flux_normalization.py` -- sha256 `73fce1038e71a770de0e8e4a6796cb9564ecc6742d79a93073fe2aa386e4b2a6`
- `proposal/molecular_scattered_sources_reduction.py` -- sha256 `13c23364255e84413c605fe202a06be9258259a5b4d88ed605edd79e7aba743c`
- `proposal/neutral_total_collision_frequency.py` -- sha256 `b0e51a91145b1998439c7c65d0a1275ad63ec6bde4061c2eb6a4d3c1611ce09a`
- `proposal/scirel.kinetic.atomic-scattered-sources-reduction.json` -- sha256 `4d34b840d371d0b36dfddd831228535c217c327a10015c536a7e11b2f9b0c23e`
- `proposal/scirel.kinetic.axisymmetric-neutral-moments.json` -- sha256 `db431b3617f7be4f637465236736d89124bc6efba827e4aa0eb5b73e790b7e6a`
- `proposal/scirel.kinetic.elastic-frequency-channels.json` -- sha256 `bb6333ab3700616b15eb247eae9b61bc85b2f38878474810570dc34e1a64bd9c`
- `proposal/scirel.kinetic.elastic-regeneration-aggregation.json` -- sha256 `44ec9f41b265e8be59e7f6829153239719a24073003628807661bcfd74acb740`
- `proposal/scirel.kinetic.generation-density-reduction.json` -- sha256 `5edad4b0b7721ccff7e2820753b005c8c476c992527c5cedd6504e012f47f274`
- `proposal/scirel.kinetic.incoming-boundary-flux-normalization.json` -- sha256 `1b727f713145f3f2f9f63b68ec985ff5d52486e294a3591c3eb7f0506e7cd49e`
- `proposal/scirel.kinetic.molecular-scattered-sources-reduction.json` -- sha256 `e3c1bb54b7ee750f6a73d50f491911d8b2dd207a494359aaaf98e022a9a6b718`
- `proposal/scirel.kinetic.neutral-total-collision-frequency.json` -- sha256 `1f29492c0c9ede847472a604d736beb2f9a0581ad15fc24a1a5b39312ac3c1f1`
- `proposal/scirel.kinetic.simple-charge-exchange-source.json` -- sha256 `13ce29d5f2119ff1ffa6a6f209a8670b5c8ada51366236626961e03e42a6586f`
- `proposal/scirel.kinetic.spatial-source-shape-normalization.json` -- sha256 `9fe8459b7142eaf3c87a8e4b60f28c42928bc67cd54959e6820b8ec5a5568685`
- `proposal/scirel.kinetic.thermal-speed-scale.json` -- sha256 `ef86322b69c297274ca78629c3930ff5599430b5f69e93c441f1dcf56d749e85`
- `proposal/simple_charge_exchange_source.py` -- sha256 `a51293ec7a3afbc209224cb3fd889474c2c343a72d17f3e1680280432efbca0d`
- `proposal/spatial_source_shape_normalization.py` -- sha256 `6b82a4168acebce2331a72ba5f03d694c91b576245089fe39e4336299e73d71d`
- `proposal/test_axisymmetric_neutral_moments.py` -- sha256 `3c3e1cdb3a69c58e0a22e97c88a8cdd380299a8660b5450ffc8028b7bb11ab39`
- `proposal/test_neutral_moments_family_l1.py` -- sha256 `494420128c6ef183016e245965d0d330961d28e843ffdfec512a013717fb9397`
- `proposal/test_neutral_transport_reductions.py` -- sha256 `555b9f074ae535556bc14d7c753c9993c88bb9bc5480f70312b96774031791d2`
- `proposal/test_scattered_source_reductions.py` -- sha256 `cd0547e65dfbde6bdcdf18c880f32d8e3faff281a74fff2030afe6bae02831a9`
- `proposal/test_thermal_speed_and_density_reduction.py` -- sha256 `efb41729b09e29851979202f0327f900d1720ae95564b893f1f7a0fe78a0321f`
- `proposal/thermal_speed_scale.py` -- sha256 `dbcf1e96e5437fd080b9b2be229c76a7a4cc51515dfe074307b92f174b312f0c`

## Batch r59: Johnson-Hinnov hydrogen radiation diagnostics family (three task graphs)

Directory: `review_candidates/2026-09-25-jh-radiation/`
Successor of batch r58: binds the composition batch the r57 candidate deferred; the r57/r58 candidate files above keep their frozen bytes and digests.
- `proposal/hydrogen_jh_balmer_alpha_emission.py` -- sha256 `c3331bdf82d789c0b8975a0e9b7b129e66a196b5e58df2414be821ed0202c4ea`
- `proposal/hydrogen_jh_balmer_alpha_ground_state_inversion.py` -- sha256 `dc794ba58b6569fc4baa4023d80b5dae6b097afd2c91971952e2990c33a9b2d7`
- `proposal/hydrogen_jh_lyman_alpha_emission.py` -- sha256 `ec903fae0248898955c8b3a4fb0eaa37f266d566f920f3e6cc1f02fb5d494b2a`
- `proposal/scirel.diagnostics.hydrogen-jh-balmer-alpha-emission.json` -- sha256 `c8348645ac90a76b05988fbfdd23ee2b0cb20c00626c1912e4b95d9e8826016c`
- `proposal/scirel.diagnostics.hydrogen-jh-balmer-alpha-ground-state-inversion.json` -- sha256 `8359d66a49f6151d165c330d55d905cc1fe263527817cf23b16e5b22f1340747`
- `proposal/scirel.diagnostics.hydrogen-jh-lyman-alpha-emission.json` -- sha256 `a5a745d9b93cc4b5df7229bfcf671b3b30c10400813cd0b618c4171dc5c48268`
- `proposal/test_graph_hydrogen_jh_balmer_alpha_emission.py` -- sha256 `6d5d1b2e463b64e8a8e625176bfda817c4921ada383123abfabd2524a287d6b1`
- `proposal/test_graph_hydrogen_jh_balmer_alpha_emission_l1.py` -- sha256 `496137d2730f9d5cf222f39ca4f0b5e3fd3a421067fd184981f099e6a42f8822`
- `proposal/test_graph_hydrogen_jh_balmer_alpha_ground_state_inversion.py` -- sha256 `188b44fe013539d695ccd798e9157275babba90c192f8fc87ddde7b92f56582a`
- `proposal/test_graph_hydrogen_jh_balmer_alpha_ground_state_inversion_l1.py` -- sha256 `6cc369c7d9bc64755e17f54575f3903584fc3604ce209e94ddb717fc6366ec93`
- `proposal/test_graph_hydrogen_jh_lyman_alpha_emission.py` -- sha256 `7059e12184f0888544c858181707bfcf1b79c875fe9185fe1529b858196273f4`
- `proposal/test_graph_hydrogen_jh_lyman_alpha_emission_l1.py` -- sha256 `4b25ccea9195d4fc56cf6aac019d8f2bdfc0346b8a7d937c223b56c5cbeb6740`
- `README.md` -- sha256 `d5d3b0ed656c9a17ed707f576bfa79fa8cca093f4c329c92ad766083cd9bf30c`
- `review.md` -- sha256 `7d2030f1646352b6f33bb3e238efb92c2d2cd234e68d4b8c9ad8cd6836d2eb8a`

## Batch r58: Johnson-Hinnov degree-convention correction (description only)

Directory: `review_candidates/2026-09-25-jh-degree-correction/`
Successor of batch r57: the r57 candidate files above keep their frozen r57 bytes and digests; this batch binds the corrected bytes.
- `README.md` -- sha256 `56769da43f3ccf7b69dfdcd93e0dfeffe2356bdd1b3a37cdfe9ab6deaa97ce7a`
- `review.md` -- sha256 `9b80e25a15ec04b3f132f37796d234ad203fc9a311c06ad3ec8ef3e46c09715a`
- `proposal/hydrogen_jh_r_coefficient.py` -- sha256 `df3cf80c947232568ccb2cdac910539fcec29ecdfc1502d202632d9e964473e1`
- `proposal/hydrogen_jh_s_coefficient.py` -- sha256 `fbb97eaa506f57ad64038d5658085c454a334af47e2ae903838faa155dd1409f`
- `proposal/hydrogen_jh_alpha_coefficient.py` -- sha256 `7e20159e5661d15de2dadedd12b706f9cd3ae0b0d93e62cfbcbcde39cbf79b05`
- `proposal/test_hydrogen_jh_r_coefficient.py` -- sha256 `bb45953147507fe20aba13db9289ceae016fc04050e347aa8206772d40ebf449`
- `proposal/test_hydrogen_jh_r_coefficient_l1.py` -- sha256 `c624e7223ae66cf94e16d86e33fe263e30cf34a2a2571b8d6189099dbd800ab4`
- `proposal/test_hydrogen_jh_s_coefficient.py` -- sha256 `bb6dd5bad0ec640d1bccf57fcc9ac1d0e5425b2567e958e796bd979705f66bbc`
- `proposal/test_hydrogen_jh_s_coefficient_l1.py` -- sha256 `ead02ceeb9c513b19c8ba9280ff11fa73e1f6827cf61f76ecadeb0d516125fca`
- `proposal/test_hydrogen_jh_alpha_coefficient.py` -- sha256 `ad8980e3b4ffe84dcdce56bfafd4731f7b74a178c0e991dc2a38ab51388e6cf6`
- `proposal/test_hydrogen_jh_alpha_coefficient_l1.py` -- sha256 `a7b45647f1d0e572c7bef10e95fd90add90e96b2299468ad73bc26ab0e2065e9`
- `proposal/scirel.collisions.hydrogen-jh-r-coefficient.json` -- sha256 `464d3b89ea203fa9c2f59039953108865f2e63e54d80bbc513b341392a43dfcf`
- `proposal/scirel.collisions.hydrogen-jh-s-coefficient.json` -- sha256 `9031868241a3007d729ec6ad39d3b038653c760829f875adff424750b11ccc5a`
- `proposal/scirel.collisions.hydrogen-jh-alpha-coefficient.json` -- sha256 `6442a1e4021c0d2a7aaa2a729b3d58a20f627a5fcfbe8ae3e7f1e35966de3a90`

## Batch r57: Johnson-Hinnov coefficient B-spline family

Directory: `review_candidates/2026-09-25-jh-coefficients/`
- `README.md` -- sha256 `7f52df8bd4c59c0add0e96e7448a489071fc610267aa2d56ba0995d33fc45166`
- `review.md` -- sha256 `6bb47dbadef808fae8c758ed4f5a79257af6153d10d2a7e27840b2d0f2a9fc51`
- `proposal/hydrogen_jh_r_coefficient.py` -- sha256 `718a6c2d444d3b8c40c582d4f23e78c0e2eb247c4869c4a32b7da9815b07dcce`
- `proposal/hydrogen_jh_s_coefficient.py` -- sha256 `94a527b59f441c857bd7bd0a474b7b95c770a2e7878c6e976a16073c33ca6dda`
- `proposal/hydrogen_jh_alpha_coefficient.py` -- sha256 `9494a98ef4e7cd9e020c4580d084d1118a8a73b7b47d1dc7dddc1e9137abee58`
- `proposal/test_hydrogen_jh_r_coefficient.py` -- sha256 `963994b9f7ec9f9f5a501ff2b5bf60180b925e584c7bc72504d3912c5fa97065`
- `proposal/test_hydrogen_jh_r_coefficient_l1.py` -- sha256 `c624e7223ae66cf94e16d86e33fe263e30cf34a2a2571b8d6189099dbd800ab4`
- `proposal/test_hydrogen_jh_s_coefficient.py` -- sha256 `52585f19a3b6ba2dd148ae8c4580faaa8acac15392731aae57ac5c9ac3154c7b`
- `proposal/test_hydrogen_jh_s_coefficient_l1.py` -- sha256 `ead02ceeb9c513b19c8ba9280ff11fa73e1f6827cf61f76ecadeb0d516125fca`
- `proposal/test_hydrogen_jh_alpha_coefficient.py` -- sha256 `fda8f860f201d647669350896b7a10aeea263b833ed2e49458a18f3359bf0155`
- `proposal/test_hydrogen_jh_alpha_coefficient_l1.py` -- sha256 `a7b45647f1d0e572c7bef10e95fd90add90e96b2299468ad73bc26ab0e2065e9`
- `proposal/scirel.collisions.hydrogen-jh-r-coefficient.json` -- sha256 `dce4a2b12f50aa191cfffd7f18e6b659098ab50230de25559b6f41b03056698c`
- `proposal/scirel.collisions.hydrogen-jh-s-coefficient.json` -- sha256 `347ccdf5cf9b6a425410a49d40ffc55909f266b817cff669e12129640766fbd9`
- `proposal/scirel.collisions.hydrogen-jh-alpha-coefficient.json` -- sha256 `15162445872716e5c0c261db633e384d2edc1f7f438c4be81c08ae05ff24d5f7`

## Batch r56: atomic-hydrogen population family

Directory: `review_candidates/2026-09-25-population-family/`
- `README.md` -- sha256 `6e8ae4adee489719daab164be1a72415cfbcc9b2a8c02f4bc7f7711585492886`
- `review.md` -- sha256 `ea8bdd82afb3f92f2b9b6e12e40b73b864b043f86bc6ef06464a218a6032695c`
- `proposal/janev_electron_impact_ionization_rate.py` -- sha256 `966ef3bdf8218a09ec6d593166bb80bdfb4b45f6b9b4ce8b95a71c4a97080f64`
- `proposal/atomic_hydrogen_1s_radiative_recombination_rate.py` -- sha256 `0371ee015d6f58ceeaa3859fbd8ff97188e32eb78b18ce20e024589fd482c21b`
- `proposal/hydrogen_saha_equilibrium_population.py` -- sha256 `36e4a5cb0b00b17b105c3e93e303dd80b39621ecd50d206457f79c7109aacde5`
- `proposal/test_janev_electron_impact_ionization_rate.py` -- sha256 `4a31746087cc24264467eea0bb960a44e386e7aa508df26a3757521ebc1e8454`
- `proposal/test_janev_electron_impact_ionization_rate_l1.py` -- sha256 `d02b01e329809a882d4c45935c0735326a0e34e28b8b324e9c1855fb39a02730`
- `proposal/test_atomic_hydrogen_1s_radiative_recombination_rate.py` -- sha256 `139ede9ea708163f4ecfe4c268df85a48880faa642bd004cd76961865c7ffd51`
- `proposal/test_atomic_hydrogen_1s_radiative_recombination_rate_l1.py` -- sha256 `17325ee5a54cf057538042af481008836e4036f4a54157dce06c2b751c522a42`
- `proposal/test_hydrogen_saha_equilibrium_population.py` -- sha256 `bbb18aa309db4348e3b947ab4bdb10c4a589aceee530e37e33a8fc0ab9cd2c34`
- `proposal/test_hydrogen_saha_equilibrium_population_l1.py` -- sha256 `36e42427837b5cf6a88aa62eb4924bb863298faf1409e9bce86fd2a234bfad97`
- `proposal/scirel.collisions.janev-electron-impact-ionization-rate-coefficient.json` -- sha256 `5213faffb85e44bae32fc49d347db7de9cc8d7d87f3fa0093777829a4b4d584b`
- `proposal/scirel.collisions.atomic-hydrogen-1s-radiative-recombination-rate-coefficient.json` -- sha256 `9c263010a156fa8d116128fc3d117ecb98661b09be9faf9d027bf2ced660e157`
- `proposal/scirel.kinetic.hydrogen-saha-equilibrium-population.json` -- sha256 `207f61417c045a609eed351c34dda02103193dabb5bacf058ef71700c0928824`

## Batch r54: dissociation-rate family

Directory: `review_candidates/2026-09-25-dissociation-rates/`
- `README.md` -- sha256 `7b44443ed2aee47106ef657ec95f213df844a6c95b9df0fc6835506cdc0af990`
- `review.md` -- sha256 `315527b430a85d4573d295ddd587f985f127f0977abe34c333b99545c463a543`
- `proposal/tmp_gen_diss_tests.py` -- sha256 `5b525325d789629bd750879c0fda23e2b91dcf883f675569df83c1e37f985bd1`
- `proposal/tmp_regen_diss_tests.py` -- sha256 `0b073ba0ee9e94fb6505424e44c4a34f5f2ebdd0a61382a7afe2cf9cc1c2351f`
- `proposal/tmp_gen_diss_modules.py` -- sha256 `c90eff26379313e12cae42f077960f57e7c62ff5b7c1e999ec753dd9c80f8dc8`
- `proposal/tmp_gen_diss_docs.py` -- sha256 `0a5a371bc6a98bbb21f7012af3f6fb6864e609cab07933ec6b101685cde1bc6e`
- `proposal/hydrogen2_h1s_h1s_dissociation_rate.py` -- sha256 `66440c460b20d25964efc7a756a5fc42c37cf25b5374bb305d723b3f190c7d4b`
- `proposal/test_hydrogen2_h1s_h1s_dissociation_rate.py` -- sha256 `98671172c303c7aa8ef40e051a7453bf6169b3c318df0ec1264ea09c2100db8b`
- `proposal/test_hydrogen2_h1s_h1s_dissociation_rate_l1.py` -- sha256 `a5767d3ad0492b3629023c28807825f8cdc8d665a6ea7c8677746dee88b09180`
- `proposal/hydrogen2_h1s_h2s_dissociation_rate.py` -- sha256 `5a09104c860f7567ef2815a1fbb94eefa37b8a256fdcf89d6b89ad04f197b577`
- `proposal/test_hydrogen2_h1s_h2s_dissociation_rate.py` -- sha256 `23e914de448b5c4eeb6834e52ae32930440187349c8b82538b6350fbdc551303`
- `proposal/test_hydrogen2_h1s_h2s_dissociation_rate_l1.py` -- sha256 `ab9c6bac7a2e4786773e2ee755f532d0bba03ef28834d4ea42dc90816009471c`
- `proposal/hydrogen2_h1s_hn3_dissociation_rate.py` -- sha256 `5bf4aa209d2ddf2f07791dbf7deee264bc8955531869f1273359fa0b23b26f73`
- `proposal/test_hydrogen2_h1s_hn3_dissociation_rate.py` -- sha256 `8ebb64392390f9579a05cf50571d5e823558a3c6601f82fbe1d70088abe912af`
- `proposal/test_hydrogen2_h1s_hn3_dissociation_rate_l1.py` -- sha256 `3182efed90a1d394c69c95745ba81f424bfa2ee79aa3902198935a95b69dddd9`
- `proposal/hydrogen2_h2p_h2s_dissociation_rate.py` -- sha256 `21058caba6b856a9ece2e5db6eecee0b5448d6f173ca515ba4911d8f18ce1e6d`
- `proposal/test_hydrogen2_h2p_h2s_dissociation_rate.py` -- sha256 `28d5d0db3bff2c63a2fe4c347af9fcc90897ea67d5f5f2d1729562aaca8ee6f6`
- `proposal/test_hydrogen2_h2p_h2s_dissociation_rate_l1.py` -- sha256 `b7085aa8c2f07cfd961ea5c76ee504a6b90d1382917ba68d92e5af07ed879f4f`
- `proposal/hydrogen2_p_h1s_dissociation_rate.py` -- sha256 `b3420dfa0ae90cf37e761bb5598dd8d736aca355c40ca2154161ac6f72fb5223`
- `proposal/test_hydrogen2_p_h1s_dissociation_rate.py` -- sha256 `72271c60f0f995f33a5b3d4d9cfe1c41080eee48c6007f31ac616cd259603234`
- `proposal/test_hydrogen2_p_h1s_dissociation_rate_l1.py` -- sha256 `d7826cdbfd8f79a80b863fb9f11b2914bb1cc19a67c620e02abe7bd0268eef8c`
- `proposal/h2_plus_two_proton_dissociation_rate.py` -- sha256 `d8192dca1b597b4e09d79bacce46db5b7dfec411f3c4d0ce9c121fac83d511dc`
- `proposal/test_h2_plus_two_proton_dissociation_rate.py` -- sha256 `9d8e38ca07d155f77b41488cbb4c86e5080f1a6d1ded45ed4fdc302f5f44242f`
- `proposal/test_h2_plus_two_proton_dissociation_rate_l1.py` -- sha256 `5206867ceebb7564d580b811c0d45d54a085dcea56fd8490572b56109477102a`
- `proposal/h2_plus_p_h1s_dissociation_rate.py` -- sha256 `6b53dce8e6c447bf078455a1dd43b07f85808ed243c4c4df4140f36d00732b24`
- `proposal/test_h2_plus_p_h1s_dissociation_rate.py` -- sha256 `ab344ec9d9966550a42af17485ed70eeedce810d988d6877e9887223dc722ab2`
- `proposal/test_h2_plus_p_h1s_dissociation_rate_l1.py` -- sha256 `255d7f03f48ca952042e6a29ef3f345873b5b44cc430e4ad05f88589ae606b27`
- `proposal/h2_plus_p_hn2_dissociation_rate.py` -- sha256 `c7b8fad4654578e68a6cfa8928f2d94dbcda83f0da9626d88af414510b882c16`
- `proposal/test_h2_plus_p_hn2_dissociation_rate.py` -- sha256 `21dc189cdcecc2771dd21eb374571fc2c404a40a170ef0c350c02bb1078367ef`
- `proposal/test_h2_plus_p_hn2_dissociation_rate_l1.py` -- sha256 `60a043e1e15cb791e5b768687d7c6fe8567e4f0a852a717b3bcd215e233cf0c5`
- `proposal/h2_plus_h1s_hn_dissociative_recombination_rate.py` -- sha256 `7d219e5fc9b7a8ceffd615513db82dfacc0b0fdba9de272463a88cc04cd6b47b`
- `proposal/test_h2_plus_h1s_hn_dissociative_recombination_rate.py` -- sha256 `b6fb9f8b70e3e72e44162803d02fb77379fc4710d6518de867a7bb6511f4f9fa`
- `proposal/test_h2_plus_h1s_hn_dissociative_recombination_rate_l1.py` -- sha256 `dbc27a65fab0feef5288fe227f8db7aeb2c14496818795a701c89633091ed707`
- `proposal/scirel.collisions.h2-dissociation-h1s-h1s-rate-coefficient.json` -- sha256 `1b642ff96af1bdb61dfcb66c69dc055c46da9709310b98f4b79a85fb3cecb254`
- `proposal/scirel.collisions.h2-dissociation-h1s-h2s-rate-coefficient.json` -- sha256 `f47ac52746cf7dfbc83d99883fe85ab5e79f86ba4b34aafa3b37fba7bc387168`
- `proposal/scirel.collisions.h2-dissociation-h1s-hn3-rate-coefficient.json` -- sha256 `843b5c2ef58bc380eaceda8ccfb8b0ea26c905036a5e4fdbf2134ed7c288ebf1`
- `proposal/scirel.collisions.h2-dissociation-h2p-h2s-rate-coefficient.json` -- sha256 `5140f2c397be5e72af28e6c040a4246d1d021dc7bc989ba4ab8b013e1cb12c9f`
- `proposal/scirel.collisions.h2-dissociation-p-h1s-rate-coefficient.json` -- sha256 `fae02ca4ff650d569c68abc3fdc0519a961b0209b35016eb010884cd04fa3287`
- `proposal/scirel.collisions.h2-plus-two-proton-dissociation-rate-coefficient.json` -- sha256 `dd0c704cf3e8611dda6c21a879c5364360082b85cd701a2836fdd7545a68286e`
- `proposal/scirel.collisions.h2-plus-p-h1s-dissociation-rate-coefficient.json` -- sha256 `bf1ea0cfbdb50e3daa396c89e7f63d5bcdd943e22722aa5fc2cb171d307f85dd`
- `proposal/scirel.collisions.h2-plus-p-hn2-dissociation-rate-coefficient.json` -- sha256 `660b7f89807cbad87d08494415034e09ecf5801960c8cfddb5bfbe10ba31d816`
- `proposal/scirel.collisions.h2-plus-h1s-hn-dissociative-recombination-rate-coefficient.json` -- sha256 `534d4cfd7dbb700abf50ae0c7572921a7e26e6f976ef11f7337c986f745beef0`

## Batch r53: elastic momentum-transfer cross-section family

Directory: `review_candidates/2026-09-25-elastic-cross-sections/`
- `README.md` -- sha256 `fde7106f56bb5c34d92ef74642e14350c6835913b395e20d2b1ce7591cde8bd3`
- `review.md` -- sha256 `2fd0a2d4086e38c103b82d0d1a6b0f89f3aeb8688eb6e86525aff056b55be956`
- `proposal/atomic_hydrogen_elastic_cross_section.py` -- sha256 `ef69d8da1c9fc90cf47f10ca43af92f825293a29eaf5b071ac9711a82ced3a41`
- `proposal/hydrogen_proton_elastic_cross_section.py` -- sha256 `ac1a84c818c7c92d45941343027886b20f807a367f52cdcfef9dcd886434fac5`
- `proposal/hydrogen_h2_elastic_cross_section.py` -- sha256 `447db0a50324359dc3e8ba74e8226826e402ccb52f50521c4b75e6c94e9830a5`
- `proposal/hydrogen2_hydrogen2_elastic_cross_section.py` -- sha256 `efb0793d9865349478adcf051922b64e06bb6d9200bcfa1be41de7f6eaa26986`
- `proposal/hydrogen2_proton_elastic_cross_section.py` -- sha256 `aa0c7304b6beff6714d3ebb46903ddbe2a599472b92d384fc6fe8a15deeacfab`
- `proposal/test_atomic_hydrogen_elastic_cross_section.py` -- sha256 `db22c5ae09029e2b2d0444add735814748c26a86902b6a9a8ed266d00208855f`
- `proposal/test_atomic_hydrogen_elastic_cross_section_l1.py` -- sha256 `4789ca1c715b9693f8faee996abaaab83f08f17473b1fa4a7b2eef1d2909af6f`
- `proposal/test_hydrogen_proton_elastic_cross_section.py` -- sha256 `98c5492a1bdc3af085edbb1ac7bf85130ae1eddfa3ec5fd6ac7630a7d551085f`
- `proposal/test_hydrogen_proton_elastic_cross_section_l1.py` -- sha256 `9ef2ef3f037c27d0ca970d3c0a1cd0423e0c7acd8ab9794e042aa1c358fa7f5e`
- `proposal/test_hydrogen_h2_elastic_cross_section.py` -- sha256 `e44f5494d57e95e31f2872bf57239eca6142e71a60504c842521fe447751abb6`
- `proposal/test_hydrogen_h2_elastic_cross_section_l1.py` -- sha256 `378d367cb06f863d160b0a19f7b11629ae31d88722e2c63e263e7b2103bf7f16`
- `proposal/test_hydrogen2_hydrogen2_elastic_cross_section.py` -- sha256 `e30f0bca01dd9976a8e13fd18a85c59e1204cdec0058c4916459acc8fdfab67e`
- `proposal/test_hydrogen2_hydrogen2_elastic_cross_section_l1.py` -- sha256 `11e6711ed118865ab61a42aaa9caf00c9ea4d5733fa81d2e9c6db5615e681523`
- `proposal/test_hydrogen2_proton_elastic_cross_section.py` -- sha256 `5570a02961a68ddfb2e2c44bf23b5672f153ba9cedc49951778642da297cfefe`
- `proposal/test_hydrogen2_proton_elastic_cross_section_l1.py` -- sha256 `92c14faaa5255d821582d525a54665c9e7f5a22cc3a3e459c312381a6969760c`
- `proposal/scirel.collisions.atomic-hydrogen-elastic-cross-section.json` -- sha256 `9fce51a740dab5b0cb8f617d5161cb5e346d3fd3b8abfc766d6f961a108a560e`
- `proposal/scirel.collisions.proton-atomic-hydrogen-elastic-cross-section.json` -- sha256 `44f667b3540b23a8e6212e0b003eda58a07ff78fea9ef31afaba96185b90f7d1`
- `proposal/scirel.collisions.atomic-molecular-hydrogen-elastic-cross-section.json` -- sha256 `4d876b5c9c58a44ad56f8161fee49c599e4f3b3db1e427c7fd9b296fb5af7141`
- `proposal/scirel.collisions.molecular-hydrogen-elastic-cross-section.json` -- sha256 `d69dfb91137ed6bf1f4135181856082d87fd987b3636ab45eb678e856670d979`
- `proposal/scirel.collisions.proton-molecular-hydrogen-elastic-cross-section.json` -- sha256 `8d601366a977a2e5f821bd8309aad965c247cc7bca9819c06e6bf52ac2a003be`

## Batch r51: molecular-hydrogen charge-exchange pair

Directory: `review_candidates/2026-09-25-h2-collision-data/`
- `README.md` -- sha256 `fc151546f10155bf54945e1165f855df7dff641e0ad9b3da86d55778f86ec2d2`
- `review.md` -- sha256 `aee8a652fa76462342c2fe2da7aa304b6196cdf0a96f439a8812a5c3eae8f8c2`
- `proposal/molecular_hydrogen_charge_exchange_cross_section.py` -- sha256 `eba61c74eb751a6e216d6a9fe2b6f4d84710cfedb15c74b0c7ecdfc735b7611a`
- `proposal/hydrogen2_charge_exchange_rate.py` -- sha256 `9c64675a6b1339dff5947eb3e1dfc7d4d23a88a74b6dc54de4eedb9f51be473a`
- `proposal/test_molecular_hydrogen_charge_exchange_cross_section.py` -- sha256 `60f8412ab14f586dcff17601d64564d0d2d7f21746662a6716f465c143d1bbff`
- `proposal/test_molecular_hydrogen_charge_exchange_cross_section_l1.py` -- sha256 `ad75f177d6ca7fc49dd522877d534cd18cf5e5db9657b9de32e84d1377bddbe5`
- `proposal/test_hydrogen2_charge_exchange_rate.py` -- sha256 `5338c3b7aac87f8ba13ab9ccccae14d0d760cb1ffdc019cb6e3c61472358ebd5`
- `proposal/test_hydrogen2_charge_exchange_rate_l1.py` -- sha256 `467d7a8de564c48877214860a2a7fb120e6776bb38f768000c56355d18855aeb`
- `proposal/scirel.collisions.molecular-hydrogen-charge-exchange-cross-section.json` -- sha256 `1de70b23d336d4f52a35d176abb3047688e96ee99e912527b2139127d8e6608c`
- `proposal/scirel.collisions.molecular-hydrogen-charge-exchange-rate-coefficient.json` -- sha256 `3b2d78d073b539c431029a25077ce9438f74a9923c6306d055a115d9e4e0e576`

## Batch r49: atomic-hydrogen collision data family

Directory: `review_candidates/2026-09-25-atomic-h-collision-data/`
- `README.md` -- sha256 `6ab4f48ad6325b3a669d08d0e00666fd594bb1fdd27e83cd80e2317186372e80`
- `review.md` -- sha256 `40813fb1d4695d72a887b13f80bae998af825486594f7c9d7e183da44c27a758`
- `proposal/atomic_hydrogen_charge_exchange_cross_section.py` -- sha256 `b8591faf6ad1cdffac06126677feb2673d1bffc73e0e802775a56681c7487880`
- `proposal/atomic_hydrogen_charge_exchange_rate.py` -- sha256 `7f24e33b6d2ff14e0666aee3325cb5e1c19092d8c50b3a3bfc496bcfab160c74`
- `proposal/collrad_h0_ionization_rate.py` -- sha256 `fb86d8f188f5cc2502b05c1867e5e8ed8d0ec9eb0d195764be5c5e655302fc21`
- `proposal/test_atomic_hydrogen_charge_exchange_cross_section.py` -- sha256 `4ff941de37900fe6b83ee8f1a42753a9a36e12d4b78f0dc21e6a93ab7b409c0b`
- `proposal/test_atomic_hydrogen_charge_exchange_cross_section_l1.py` -- sha256 `4d050c56ccad906fd261dc5bd22c6b51a00e529c30dc80a43ffd55c774e3e382`
- `proposal/test_atomic_hydrogen_charge_exchange_rate.py` -- sha256 `42a90284c139eafc2e5341e773c00e811d7e0e1adad5b06b0032f36cda56b0bc`
- `proposal/test_atomic_hydrogen_charge_exchange_rate_l1.py` -- sha256 `48980ec21226dfb56cc364638985efa14b4598e04460521f78d0326b8b0e8db3`
- `proposal/test_collrad_h0_ionization_rate.py` -- sha256 `8c26fd210c2012b6b5f238078890af188003c20b998396223cb8ffe1d1bc2b7f`
- `proposal/test_collrad_h0_ionization_rate_l1.py` -- sha256 `53dd5bc06d5e5fd9be78cdccd046bcf7c89e6066a8b72c3b4f55077caf007f6a`
- `proposal/scirel.collisions.atomic-hydrogen-charge-exchange-cross-section.json` -- sha256 `edcf777e4e382b6efed66f47ff9b99ab1ac52a8a61cd841e213ab4046d36db70`
- `proposal/scirel.collisions.atomic-hydrogen-charge-exchange-rate-coefficient.json` -- sha256 `9ab3d19b022bfc5b5ba41392be280279c555470ab2ccd9f16afb2b8485600f2c`
- `proposal/scirel.collisions.collrad-h0-ionization-rate.json` -- sha256 `f29a72098299e43920a16c5a8f06ec5401bd3653244cac69335de2f4afff0b8c`

The proposal files are byte-identical to the integrated files under `src/`,
`tests/` and `catalog/examples/` at the same commit. Coverage boundary: the
r49-r55 manifests named only docs materials; the candidate bytes were in the
frozen trees but not named by any manifest. This index closes that gap from
r53 onward.
