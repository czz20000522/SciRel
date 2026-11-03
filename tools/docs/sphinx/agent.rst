Agent 查询
=============

正式 Agent 消费入口是标准库 CLI 与可选的只读 MCP；两者共用同一工具注册表、分发器、能力索引和完整原始 JSON 合同。MCP 支持本地或平台沙盒的 stdio 进程，以及同一环境中的 loopback Streamable HTTP 服务。科学计算由用户的 Python 程序调用已安装 wheel 的公开 API。

人读 API 页面、手写教程和双语 HTML 站点由独立文档管线生成；消费 runtime 不含这些 Markdown、教程索引或站点资源，查询与构建 runtime 都不需要文档快照或 HTML。

四个只读工具
----------------

* ``describe`` / ``scirel_describe``：快照、wheel 摘要、依赖和查询限制。
* ``browse`` / ``scirel_browse``：分页浏览能力卡片。
* ``search`` / ``scirel_search``：少量候选、命中原因及约束冲突。
* ``get`` / ``scirel_get``：一个完整原始公共 JSON 合同、文件路径与字节摘要。

先发现，再把 ``expected_snapshot_sha256`` 与 ``expected_wheel_sha256`` 传给后续工具。游标绑定数据集与查询，不能跨批续读。``browse`` 和 ``search`` 限制候选数量与 JSON envelope 字节；只延期完整候选卡，不删减科学边界。``get.document`` 返回整个合同，``paths.contract`` 与 ``digests`` 绑定原始文件；合同超过 65536 字节仍完整返回，不分页、截断或附带 Markdown，也没有语言选择参数。当前排序是可替换的词法实现；显式筛选不静默放宽。缺失元数据保持 unknown，零命中不证明科学能力缺失，召回不证明物理适用或可组合。

``describe.human_documentation`` 为 ``{"status":"unconfigured","locator":"asset_id"}``。资产 ID 只是人读文档的逻辑查找键；只有另行提供的实际站点、版本或已生成路径映射才可用于阅读。不得推测 URL、自动联网或把站点的“最新”视为选定 wheel 的对应版本。阅读完整合同后即可调用公开 API，人读材料可按需要补充。

.. code-block:: bash

   python /实际消费包路径/tools/query.py --root /实际消费包路径 describe
   python /实际消费包路径/tools/query.py --root /实际消费包路径 get scirel.field.circular-filament-green --expected-snapshot-sha256 <snapshot_sha256> --expected-wheel-sha256 <wheel_sha256>

私有消费包安装独立 adapter 依赖后，用 ``python tools/server.py --root /实际消费包路径 --transport stdio`` 启动本地进程；同一环境的 loopback HTTP 使用 ``--transport streamable-http --host 127.0.0.1 --port 8765``，客户端连接 ``http://127.0.0.1:8765/mcp``。Famou/Linux 兼容性需分别实测。pure 仍依赖 Python、NumPy、SciPy 和 mpmath。

以下 HTTP/CLI 属于开发文档维护验证入口；正式消费使用上述四个 CLI／MCP 工具。

开发快照发现与搜索
----------------------

.. code-block:: bash

   curl 'http://127.0.0.1:8765/api/handbook'
   curl 'http://127.0.0.1:8765/api/search?q=磁场&limit=5'
   curl 'http://127.0.0.1:8765/api/topic?id=coil-vacuum-fields'

查询结果保留快照身份、精确资产 ID 和实现版本。中文检索覆盖经过审阅的中文说明；API 名称和原合同关键词也可检索。

结构化能力查询
------------------

.. code-block:: bash

   curl 'http://127.0.0.1:8765/api/capabilities?capability=equilibrium&geometry=axisymmetric&limit=5'
   curl 'http://127.0.0.1:8765/api/capabilities?device_scope=device-parameterized&q=coil&limit=5'
   python scripts/scirel_docs.py query --snapshot /实际快照路径 --capabilities --capability equilibrium --limit 5

``capabilities`` 从合同投影出 capability、operation、model、geometry、boundary、device_scope；过滤条件是 AND，``q`` 仍做词法召回。响应区分 ``match`` / ``near_miss`` / ``gap``：零词法命中不等同于科学能力缺口。未记录 device_scope 的资产返回 ``unclassified``，不得当作 ``generic``。返回中的 contract_path/docs_path 指回同一快照的正式合同和页面。

完整合同与中文说明
----------------------

.. code-block:: bash

   curl 'http://127.0.0.1:8765/api/asset?id=scirel.field.circular-filament-green'
   curl 'http://127.0.0.1:8765/api/reader?id=scirel.field.circular-filament-green'

``asset`` 返回原正式科学合同。``reader`` 同时返回原合同与绑定其 SHA-256 的中文说明，和 API 页面展示的内容一致。中文说明不是另一份独立科学合同；原合同变化而中文尚未核对时，构建会拒绝发布。

离线 CLI
------------

.. code-block:: bash

   python scripts/scirel_docs.py query --snapshot /实际快照路径 --q 磁场 --limit 5
   python scripts/scirel_docs.py query --snapshot /实际快照路径 --reader scirel.field.circular-filament-green

查询不执行科学函数，也不修改科学资产。需要计算时，在符合相应科学合同的安装环境中调用公开 Python 入口。维护快照验证不代表 Famou 接入、公开部署或科学人工验收完成。
