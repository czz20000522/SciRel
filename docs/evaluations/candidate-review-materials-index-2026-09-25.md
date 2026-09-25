# Candidate review-material index (r56)

The freeze script binds review materials to tracked `docs/*.md` files only,
so the expert-review entry point for each integration batch -- the candidate
document, its comparison inventory (README) and the proposal files under
`review_candidates/` -- is not listed in any snapshot manifest material list,
even though the frozen commit tree contains the bytes. This index binds those
files by exact SHA-256 at the r56 freeze commit so the manifest chain points
an expert to them. Every entry path is relative to its batch Directory and
resolvable from it (verified by script after the r55 path correction); any
drift between a digest below and the working tree means the candidate text
changed after this index was written and the batch needs a successor, not a
silent edit.

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
