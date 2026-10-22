Agent 查询
=============

正式 Agent 消费入口是只读 MCP。公开快照可由本地或平台沙盒的 stdio 进程，以及托管的 Streamable HTTP 服务读取。两种方式共用能力索引、完整合同与按需 Markdown；公网 HTML 供人浏览，不是查询前置。科学计算仍由用户的 Python 程序调用已安装的 wheel，MCP 不执行任意代码。

正式 MCP 工具
----------------

* ``scirel_describe``：快照、wheel 摘要、依赖和查询限制。
* ``scirel_browse``：分页浏览能力或教程目录。
* ``scirel_search``：少量候选、命中原因及约束冲突。
* ``scirel_get``：一个完整公共合同及对应语言的 API Markdown。
* ``scirel_get_tutorial``：按需读取手写教程与显式续读片段。

先发现，再把 ``expected_snapshot_sha256`` 与 ``expected_wheel_sha256`` 传给后续工具。游标绑定数据集与查询，不能跨批续读。数量和 JSON envelope 字节都有预算；只延期完整候选卡，不删减科学边界。当前排序是可替换的词法实现；显式筛选不静默放宽。缺失元数据保持 unknown，零命中不证明科学能力缺失，召回不证明物理适用或可组合。

私有消费包安装独立 adapter 依赖后，用 ``python tools/server.py --root /实际消费包路径 --transport stdio`` 启动本地进程；loopback HTTP 使用 ``--transport streamable-http --host 127.0.0.1 --port 8765``，客户端连接 ``http://127.0.0.1:8765/mcp``。托管上线前另行明确 TLS、认证和运维；Famou/Linux 兼容性需分别实测。pure 仍依赖 Python、NumPy、SciPy 和 mpmath。

以下 HTTP/CLI 属于开发文档维护验证入口；正式消费使用上述 MCP 工具。

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
