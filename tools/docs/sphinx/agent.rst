Agent 查询
=============

页面与只读 HTTP / CLI 接口消费同一个摘要绑定快照。Agent 可以先定位主题，再读取少量函数的完整合同，不必导入科学库或一次加载全部文档。

发现与搜索
--------------

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

查询不执行科学函数，也不修改科学资产。需要计算时，应在符合相应科学合同的安装环境中调用公开 Python 入口。当前提供 HTTP 与 CLI；尚未提供 MCP transport。
