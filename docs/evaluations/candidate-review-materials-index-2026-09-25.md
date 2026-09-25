# Candidate review-material index (r52)

The freeze script binds review materials to tracked `docs/*.md` files only,
so the expert-review entry point for each integration batch -- the candidate
document, its comparison inventory (README) and the proposal files under
`review_candidates/` -- is not listed in any snapshot manifest material list,
even though the frozen commit tree contains the bytes. This index binds those
files by exact SHA-256 at the r52 freeze commit so the manifest chain points
an expert to them. Any drift between a digest below and the working tree
means the candidate text changed after this index was written and the batch
needs a successor, not a silent edit.

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
`tests/` and `catalog/examples/` at the same commit; the r52 dossier records
the earlier snapshots' coverage boundary honestly: the r49 and r51 manifests
named only docs materials, and an expert following the manifest alone would
not have been pointed at these candidate files. That is a coverage gap in
the material lists, not a claim that the bytes were missing from the frozen
trees -- they were present at commits `dbb4385`/`0035e9e`/`de0342a` as part
of the tracked tree.
