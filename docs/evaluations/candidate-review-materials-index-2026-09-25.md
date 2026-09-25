# Candidate review-material index (r53)

The freeze script binds review materials to tracked `docs/*.md` files only,
so the expert-review entry point for each integration batch -- the candidate
document, its comparison inventory (README) and the proposal files under
`review_candidates/` -- is not listed in any snapshot manifest material list,
even though the frozen commit tree contains the bytes. This index binds those
files by exact SHA-256 at the r53 freeze commit so the manifest chain points
an expert to them. Any drift between a digest below and the working tree
means the candidate text changed after this index was written and the batch
needs a successor, not a silent edit.

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

Digests unchanged from the r52-era index except where the r52 count
corrections touched the candidate texts; all values below are the current
r53-commit bytes.
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
r49/r51/r52 manifests named only docs materials; the candidate bytes were in
the frozen trees but not named by any manifest. This index closes that gap
from r53 onward.
