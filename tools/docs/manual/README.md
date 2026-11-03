# 手写教程章节规范

用户指南只接受手写教程：中文为 `tools/docs/manual/<chapter-id>.rst`，英文为
`tools/docs/manual/en/<chapter-id>.rst`。没有手写稿的章节在对应语言 HTML 中保持空白或显示明确占位。
合同（`catalog/examples/*.json`）只提供 API 参考、签名、失败行为和可验证事实，不再被拼成教程正文。

英文导航的章节标题与导读来自 `tools/docs/handbook.en.json`，其章节/主题/资产结构必须与
`tools/docs/handbook.json` 一致。英文构建优先读取已存在的 `manual/en` 文件；缺失时显示英文占位，
绝不回退中文；若英文指南仍含中文则构建失败关闭。缩减文档集（只选部分资产）中，指南若引用了
集合外页面则显示英文 subset 占位，不静默改写作者正文。

## 参考样板

- `tools/docs/manual/plasma-waves.rst`
- `tools/docs/sphinx/tutorials/kinetic-initial-value.rst`

语气与结构参考 SciPy tutorial：从一个具体问题出发，而不是按函数清单罗列。

## 每章必须包含

1. 开篇：这一章要回答什么问题，读完能做什么，前置约定/归一化。
2. 主体：3–6 个连续小节，每节尽量有
   - 物理/数学背景和符号含义；
   - 一段最小可运行代码；
   - **实际运行输出**（真实执行，不编造）；
   - 对输出的解释：数字代表什么，为什么是这个量级；
   - 这一节不能推出什么结论。
3. 易错点：分支选择、单位/归一化、残差不是误差、种子依赖等。
4. 何时用哪个函数：给读者选择路径，链接到 `../reference/generated/<asset-id>`。
5. 边界：适用范围、失败模式、与合同/API 参考的关系。

## 约束

- 只写中文；不要复制合同段落或把合同字段翻译一遍。
- 只调用 `scirel` 公开函数，代码必须在当前 `.venv` 中实际跑通。
- 每个代码块尽量短；输出用 `.. code-block:: text`；数字保留合理有效位。
- 不写来源项目名、源码路径锚点、D0–D3/拆解过程。
- 不修改 `scripts/build_scirel_sphinx.py`、catalog、测试或其它章节；只写自己的章节文件。
- 不 commit，不启动长期服务；构建验证用临时目录。

## 发布与审查（2026-10-21）

- 用户指南只接受手写 `tools/docs/manual/<chapter>.rst`；没有手写稿就空白，不回退合同摘要。
- API 参考由合同生成，但生成后必须逐页人工审查；生成成功不等于正确。
- 中英文各自人工审查：英文合同字段必须英文，中文侧车必须中文；不得出现中文页夹英文整段或英文页夹中文整段。
- 每个页面/合同必须经过“实现 → 合同 → 示例 → API 页/用户指南”的同一真值检查。
- 完整 HTML 发布站点生成到仓库内 `dist/`（gitignored）；本机是唯一真源，不提交 Git，不放 E 盘。
- 可发布产物：`dist/docs-<date>/` 与 `dist/scirel-docs-<date>.tar.gz`；能力矩阵随站点发布
  （`capability-matrix.json`、`CAPABILITY_MATRIX.md`、`web/user-guide/capability-matrix.html`）。
- 修改前先读 `catalog/README.md`。
