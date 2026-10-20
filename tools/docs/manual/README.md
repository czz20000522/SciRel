# 手写教程章节规范

用户指南只接受 `tools/docs/manual/<chapter-id>.rst` 的手写教程；没有手写稿的章节在 HTML 中保持空白。
合同（`catalog/examples/*.json`）只提供 API 参考、签名、失败行为和可验证事实，不再被拼成教程正文。

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
