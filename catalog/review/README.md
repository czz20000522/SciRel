# catalog/review

评审期目录。这里的内容不进入安装包、不生成文档、不进能力索引和查询服务；
`tests/delivery/test_wheel_exposure_proof.py` 把 `catalog/review/candidates/`
下的成员判为 `candidate_paths_present`，打包直接 FAIL。

目录里现在装三样东西：

- `candidates/src/scirel/` —— 候选实现（5 个模块），还没落进 `src/scirel/`，
  因此不可公开导入。
- `examples/*.json` —— 与上面候选实现一一对应的合同（5 份）。实现落地后，
  合同才移进 `catalog/examples/`。
- `excluded_from_package.json` —— 排除清单，只有 `ids`、`purpose`、
  `revisit_when` 三个字段。它记录打包范围，不判断科学对错。

这里没有"评审状态"。树里没有 `VERDICTS.json`、`HOLD.json` 一类的状态登记表：
公开与否由实现决定——`src/scirel/` 里有实现的资产才进 `catalog/examples/`，
其余留在本目录。这是范围，不是裁决。

一个资产离开本目录只有一种方式：实现和合同同一笔落进 `src/scirel/` 与
`catalog/examples/`，同时把对应 id 从 `excluded_from_package.json` 删掉。
清单不是永久豁免，`revisit_when` 到期就要复核。
