"""Render exact scientific records and reviewed prose with SciPy's theme.

Two languages share one contract source.  The Chinese site projects the bound
Chinese reader layer.  The English site projects the English contract fields,
uses reviewed navigation from ``tools/docs/handbook.en.json``, and renders
``tools/docs/manual/en/<chapter-id>.rst`` guides when authored; missing guides
receive explicit English placeholders and Chinese guide prose is never used as
a fallback.  No scientific imports, autodoc execution, translation inference or
example runs are performed; all generated reStructuredText is a projection of
reviewed input documents.
"""

from __future__ import annotations

from importlib.metadata import version
import json
from pathlib import Path
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

from code_digest import contract_digest, source_digest

LANGUAGE_TAGS = {"zh": "zh-CN", "en": "en-US"}
ENGLISH_GUIDE_PLACEHOLDER = (
    "English user-guide text for this chapter is not authored yet. Use the API "
    "reference for signatures, ports, failure behavior, applicability and examples."
)
ENGLISH_GUIDE_SUBSET_PLACEHOLDER = (
    "The English guide for this chapter is authored, but this reduced documentation "
    "selection does not include every page it references. Use the full English "
    "documentation or the API reference for the selected functions."
)
_CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]")


_ENGLISH_HANDBOOK = Path("tools/docs/handbook.en.json")
_ENGLISH_MANUAL = Path("tools/docs/manual/en")


def handbook_english_placeholder(book):
    """Return explicit English placeholders when the reviewed handbook is absent.

    This fallback never copies Chinese guide prose into the English site.  It
    is only used when ``tools/docs/handbook.en.json`` is missing; the identifier
    and placeholder text make the missing review visible on every page.
    """
    chapters = []
    for chapter in book["chapters"]:
        topics = []
        for topic in chapter["topics"]:
            topics.append(
                {
                    "id": topic["id"],
                    "title": topic["id"],
                    "introduction": (
                        "English user-guide text for this topic is not "
                        "authored yet; the identifier is shown until it is."
                    ),
                    "assets": list(topic["assets"]),
                }
            )
        chapters.append(
            {
                "id": chapter["id"],
                "title": chapter["id"],
                "discipline": [chapter["id"]],
                "introduction": (
                    "English user-guide text for this chapter is not "
                    "authored yet; the identifier is shown until it is."
                ),
                "topics": topics,
            }
        )
    return {
        "schema": book["schema"],
        "title": "SciRel scientific handbook",
        "introduction": (
            "English navigation is a placeholder: chapter and topic "
            "identifiers are shown until the reviewed English handbook "
            "is authored."
        ),
        "chapters": chapters,
    }


def _english_text(value, where):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(where + " must be a non-empty English string")
    if _CJK.search(value):
        raise ValueError(where + " must be English, not Chinese")
    return value


def _validate_english_handbook(english, canonical):
    """Validate structure and language of ``handbook.en.json`` against canonical."""
    if not isinstance(english, dict) or english.get("schema") != "scirel.handbook":
        raise ValueError("invalid English handbook schema")
    _english_text(english.get("title"), "English handbook title")
    _english_text(english.get("introduction"), "English handbook introduction")
    english_chapters = english.get("chapters")
    canonical_chapters = canonical["chapters"]
    if not isinstance(english_chapters, list) or len(english_chapters) != len(canonical_chapters):
        raise ValueError("English handbook chapter count differs from the canonical handbook")
    for english_chapter, canonical_chapter in zip(
        english_chapters, canonical_chapters, strict=True
    ):
        chapter_id = canonical_chapter["id"]
        if not isinstance(english_chapter, dict) or english_chapter.get("id") != chapter_id:
            raise ValueError("English handbook chapter order differs from the canonical handbook")
        _english_text(english_chapter.get("title"), "English chapter " + chapter_id + " title")
        _english_text(
            english_chapter.get("introduction"), "English chapter " + chapter_id + " introduction"
        )
        discipline = english_chapter.get("discipline")
        if not isinstance(discipline, list) or not discipline:
            raise ValueError("English chapter " + chapter_id + " needs a discipline list")
        for item in discipline:
            _english_text(item, "English chapter " + chapter_id + " discipline")
        english_topics = english_chapter.get("topics")
        canonical_topics = canonical_chapter["topics"]
        if not isinstance(english_topics, list) or len(english_topics) != len(canonical_topics):
            raise ValueError("English handbook topic count differs for chapter " + chapter_id)
        for english_topic, canonical_topic in zip(english_topics, canonical_topics, strict=True):
            topic_id = canonical_topic["id"]
            if not isinstance(english_topic, dict) or english_topic.get("id") != topic_id:
                raise ValueError("English handbook topic order differs for " + topic_id)
            _english_text(english_topic.get("title"), "English topic " + topic_id + " title")
            _english_text(
                english_topic.get("introduction"), "English topic " + topic_id + " introduction"
            )
            if english_topic.get("assets") != canonical_topic["assets"]:
                raise ValueError("English handbook assets differ for topic " + topic_id)


def load_english_handbook(root, book):
    """Project reviewed English navigation onto one exact document subset.

    ``book`` is the canonical navigation already projected onto the selected
    contracts.  When ``tools/docs/handbook.en.json`` exists it must mirror the
    canonical chapter/topic identity and asset placement exactly; only the
    reviewed English prose is taken from it.  When the file is absent, explicit
    English identifiers and placeholders are returned instead of Chinese prose.
    """
    path = Path(root) / _ENGLISH_HANDBOOK
    if not path.is_file():
        return handbook_english_placeholder(book)
    canonical_path = Path(root) / "tools/docs/handbook.json"
    if not canonical_path.is_file():
        raise ValueError("canonical handbook is required to validate the English handbook")
    english = json.loads(path.read_bytes())
    canonical = json.loads(canonical_path.read_bytes())
    _validate_english_handbook(english, canonical)
    english_chapters = {chapter["id"]: chapter for chapter in english["chapters"]}
    chapters = []
    for chapter in book["chapters"]:
        english_chapter = english_chapters[chapter["id"]]
        english_topics = {topic["id"]: topic for topic in english_chapter["topics"]}
        topics = []
        for topic in chapter["topics"]:
            english_topic = english_topics[topic["id"]]
            topics.append(
                {
                    "id": topic["id"],
                    "title": english_topic["title"],
                    "introduction": english_topic["introduction"],
                    "assets": list(topic["assets"]),
                }
            )
        chapters.append(
            {
                "id": chapter["id"],
                "title": english_chapter["title"],
                "discipline": list(english_chapter["discipline"]),
                "introduction": english_chapter["introduction"],
                "topics": topics,
            }
        )
    return {
        "schema": english["schema"],
        "title": english["title"],
        "introduction": english["introduction"],
        "chapters": chapters,
    }


def english_manual_chapter(root, chapter_id):
    """Return one authored English guide, or ``None`` when it is not present.

    Only ``tools/docs/manual/en/<chapter-id>.rst`` is considered.  Chinese
    chapter files are never a fallback; a present file that still contains
    Chinese fails closed instead of leaking Chinese prose into the English site.
    """
    path = Path(root) / _ENGLISH_MANUAL / (chapter_id + ".rst")
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return None
    if _CJK.search(text):
        raise ValueError("English guide contains Chinese text: " + str(path))
    return text


def _english_doc_refs(text):
    """Return the targets of ``:doc:`` roles in one guide page."""
    refs = []
    for match in re.finditer(r":doc:`([^`]+)`", text):
        target = match.group(1)
        if "<" in target and target.endswith(">"):
            target = target.rsplit("<", 1)[1][:-1]
        refs.append(target.strip())
    return refs


def english_available_docs(root, book, asset_ids, *, matrix):
    """Return the docnames present in one English documentation selection."""
    available = {"index", "user-guide/index", "reference/index"}
    for chapter in book["chapters"]:
        available.add("user-guide/" + chapter["id"])
        available.add("reference/" + chapter["id"])
        for topic in chapter["topics"]:
            for asset in topic["assets"]:
                if asset in asset_ids:
                    available.add("reference/generated/" + asset)
    if matrix is not None:
        available.add("user-guide/capability-matrix")
    canonical_path = Path(root) / "tools/docs/handbook.json"
    if canonical_path.is_file():
        for chapter in json.loads(canonical_path.read_bytes())["chapters"]:
            for topic in chapter["topics"]:
                tutorial_id = topic.get("tutorial_id")
                if tutorial_id:
                    available.add("tutorials/" + tutorial_id)
    return available


def _english_guide_content(root, chapter_id, available):
    """Return ``(text, status)`` for one English guide.

    Status is ``authored`` when the guide exists and every ``:doc:`` target is
    present in this selection, ``placeholder`` when no guide file exists, and
    ``subset-placeholder`` when the authored guide references pages outside a
    reduced selection.
    """
    text = english_manual_chapter(root, chapter_id)
    if text is None:
        return None, "placeholder"
    if not guide_selection_complete(text, chapter_id, available):
        return None, "subset-placeholder"
    return text, "authored"


def guide_selection_complete(text, chapter_id, available):
    """Apply the same selected-document reference closure in both languages."""
    for target in _english_doc_refs(text):
        if target.startswith("/"):
            doc = target[1:]
        else:
            base = posixpath.dirname("user-guide/" + chapter_id)
            doc = posixpath.normpath(posixpath.join(base, target))
        if doc not in available:
            return False
    return True


def english_guide_status(root, chapters, available):
    """Return each chapter's English guide status for this selection."""
    return {
        chapter["id"]: _english_guide_content(root, chapter["id"], available)[1]
        for chapter in chapters
    }


def english_translation_gaps(docs):
    """Return English contract fields that still contain CJK, per asset.

    The English site is built from the contracts, so a non-English contract
    field leaks into an English page.  The build records those gaps instead of
    hiding or rewriting them; ``title.zh`` is the only allowed Chinese field.
    """
    gaps = {}
    for document in docs:
        paths = []

        def walk(value, path=""):
            if isinstance(value, dict):
                for key, item in value.items():
                    walk(item, f"{path}.{key}" if path else key)
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    walk(item, f"{path}[{index}]")
            elif isinstance(value, str) and path != "title.zh" and _CJK.search(value):
                paths.append(path)

        walk(document)
        if paths:
            gaps[document["asset_id"]] = sorted(set(paths))
    return gaps


def plain(text):
    """Render explicit inline math/code; escape all other prose as reST text."""

    def escape(value):
        return (
            value.replace("\\", "\\\\")
            .replace("`", "\\`")
            .replace("*", "\\*")
            .replace("|", "\\|")
            .replace("_", "\\_")
            .replace("\n", " ")
        )

    result = []
    for part in re.split(r"(\$[^$\n]+\$|`[^`\n]+`)", str(text)):
        if part.startswith("$") and part.endswith("$") and len(part) > 2:
            from latex2mathml.converter import convert

            node = ET.fromstring(convert(part[1:-1]))
            allowed = {
                "math",
                "mi",
                "mo",
                "mn",
                "mrow",
                "msup",
                "msub",
                "msubsup",
                "mfrac",
                "msqrt",
                "mroot",
                "mover",
                "munder",
                "munderover",
                "mtext",
                "mtable",
                "mtr",
                "mtd",
                "mspace",
                "menclose",
                "mpadded",
                "mstyle",
                "mmultiscripts",
                "mprescripts",
                "none",
                "mphantom",
            }
            for element in node.iter():
                if element.tag.rsplit("}", 1)[-1] not in allowed or any(
                    key.lower().startswith("on") or key.lower().endswith("href")
                    for key in element.attrib
                ):
                    raise ValueError("unsupported MathML in scientific prose")
            ET.register_namespace("", "http://www.w3.org/1998/Math/MathML")
            node.set("aria-label", part[1:-1])
            markup = (
                ET.tostring(node, encoding="unicode").replace("`", "&#96;").replace("\\", "\\\\")
            )
            result.append(" :scirel-math:`" + markup + "` ")
        elif part.startswith("`") and part.endswith("`") and len(part) > 2:
            result.append(" ``" + part[1:-1] + "`` ")
        else:
            result.append(escape(part))
    return "".join(result)


def kinetic_tutorial_proof(root):
    """Return the tutorial execution evidence bound to this documentation build."""
    proof = root / "tools/docs/kinetic-tutorial/execution.json"
    if not proof.is_file():
        raise ValueError("kinetic tutorial execution evidence is missing")
    return proof


def title(text, char="="):
    return text + "\n" + char * (len(text) * 2 + 4) + "\n\n"


def bullets(items):
    return "".join("* " + plain(x) + "\n" for x in items) + "\n"


def code(text, language="python"):
    return (
        ".. code-block:: "
        + language
        + "\n\n"
        + "\n".join("   " + line for line in text.splitlines())
        + "\n\n"
    )


def toctree(paths, hidden=False, maxdepth=2):
    return (
        ".. toctree::\n   :maxdepth: "
        + str(maxdepth)
        + "\n"
        + ("   :hidden:\n" if hidden else "")
        + "\n"
        + "".join("   " + p + "\n" for p in paths)
        + "\n"
    )


def api_path(asset):
    return "/reference/generated/" + asset


def doclink(label, path):
    return ":doc:`" + label.replace("`", "") + " <" + path + ">`"


def function_table(records, translations, *, language="zh"):
    """One linked callable and its bound purpose per row."""
    if language == "en":
        out = (
            ".. list-table::\n   :header-rows: 1\n   :widths: 40 60\n"
            "   :class: scirel-api-summary\n\n   * - Function\n     - Purpose\n"
        )
        for doc in records:
            label = doc["public_api"]["python"]["symbol"]
            purpose = plain(doc["summary"])
            out += (
                "   * - " + doclink(label, api_path(doc["asset_id"])) + "\n     - " + purpose + "\n"
            )
        return out + "\n"
    out = ".. list-table::\n   :header-rows: 1\n   :widths: 40 60\n   :class: scirel-api-summary\n\n   * - 函数\n     - 用途\n"
    for doc in records:
        label = doc["public_api"]["python"]["symbol"]
        purpose = plain(translations[doc["asset_id"]]["summary"])
        out += "   * - " + doclink(label, api_path(doc["asset_id"])) + "\n     - " + purpose + "\n"
    return out + "\n"


def ports(doc, translated, side, *, language="zh"):
    if language == "en":
        out = ""
        for original in doc[side]:
            name = original["name"]
            typ = plain(original["dtype"])
            optional = " (optional)" if not original.get("required", True) else ""
            out += "``" + name + "`` : " + typ + optional + "\n"
            out += "    " + plain(original["description"]) + "\n\n"
            out += (
                "    Units: "
                + plain(str(original["units"]))
                + "; shape: "
                + plain(str(original["shape"]))
                + ".\n\n"
            )
            if "default" in original:
                out += "    Default: ``" + str(original["default"]) + "``.\n\n"
            out += "    " + plain(original["constraints"]) + "\n\n"
        label = "Parameters" if side == "inputs" else "Returns"
        return (
            ":"
            + label
            + ":\n"
            + "".join("    " + line + "\n" if line else "\n" for line in out.splitlines())
            + "\n"
        )
    out = ""
    for original, zh in zip(doc[side], translated[side], strict=True):
        name = original["name"]
        typ = plain(zh["dtype"])
        optional = "，可选" if not original.get("required", True) else ""
        out += "``" + name + "`` : " + typ + optional + "\n"
        out += "    " + plain(zh["description"]) + "\n\n"
        out += (
            "    单位："
            + plain(str(original["units"]))
            + "；形状："
            + plain(str(original["shape"]))
            + "。\n\n"
        )
        if "default" in original:
            out += "    默认值：``" + str(original["default"]) + "``。\n\n"
        out += "    " + plain(zh["constraints"]) + "\n\n"
    label = "参数" if side == "inputs" else "返回值"
    return (
        ":"
        + label
        + ":\n"
        + "".join("    " + line + "\n" if line else "\n" for line in out.splitlines())
        + "\n"
    )


def render_api(doc, zh, related, *, language="zh"):
    if language == "en":
        return _render_english_api(doc, related)
    py = doc["public_api"]["python"]
    asset = doc["asset_id"]
    out = plain(doc["title"]["zh"]) + "。" + plain(zh["summary"]) + "\n\n"
    if zh.get("source_conflicts"):
        out += ".. warning::\n\n   原正式文档含有待修正的内部矛盾。以下为阅读提示，不改变原合同或科学资格。\n\n"
        out += "".join("   * " + plain(item) + "\n" for item in zh["source_conflicts"]) + "\n"
    out += "实现版本：``" + doc["version"]["implementation_version"] + "``。"
    out += "科学关系函数。\n\n"
    out += ports(doc, zh, "inputs") + ports(doc, zh, "outputs")
    out += title("异常与失败行为", "-")
    for key, label in [
        ("invalid_input", "无效输入"),
        ("runtime_failure", "运行失败"),
        ("nonconvergence", "不收敛"),
        ("partial_results", "部分结果"),
    ]:
        out += "**" + label + "**\n    " + plain(zh["failure_semantics"][key]) + "\n\n"
    out += title("说明", "-") + plain(zh["definition"]) + "\n\n"
    out += "**模型：** " + plain(zh["model"]) + "\n\n"
    out += "**边界约定：** " + plain(zh["boundary"]) + "\n\n" + bullets(zh["assumptions"])
    out += (
        title("适用范围", "-") + "**使用前提**\n\n" + bullets(zh["applicability"]["preconditions"])
    )
    out += "**支持的范围**\n\n" + bullets(zh["applicability"]["supported"])
    out += "**不支持的范围**\n\n" + bullets(zh["applicability"]["excluded"])
    out += title("相关函数", "-")
    if related:
        out += (
            "".join(
                "* "
                + doclink(d["public_api"]["python"]["symbol"], api_path(d["asset_id"]))
                + " — "
                + plain(d["title"]["zh"])
                + "\n"
                for d in related
            )
            + "\n"
        )
    else:
        out += "请返回所属领域的 API 参考，按科学问题选择其他关系。\n\n"
    out += title("示例", "-") + plain(zh["example"]["description"]) + "\n\n"
    out += code(doc["example"]["code"])
    out += "**预期行为：** " + plain(zh["example"]["expected"]) + "\n\n"
    out += (
        "以上代码来自正式合同，预期行为与本轮实际运行结果分别记录。完整的已运行案例见用户指南。\n\n"
    )
    out += title("验证与限制", "-") + plain(zh["verification"]["evidence_ceiling"]) + "\n\n"
    out += "**已有验证范围**\n\n" + bullets(zh["verification"]["scope"])
    out += "**已知限制**\n\n" + bullets(zh["verification"]["known_limitations"])
    out += title("参考资料", "-")
    refs = doc.get("references", [])
    for ref in refs:
        out += (
            "* "
            + plain(json.dumps(ref, ensure_ascii=False) if isinstance(ref, dict) else ref)
            + "\n"
        )
    out += "\n`读取正式合同 JSON </api/asset?id=" + asset + ">`_ · "
    out += "`读取同源中文说明 </api/reader?id=" + asset + ">`_\n\n"
    out += "中文说明绑定正式合同摘要 ``" + zh["source_sha256"] + "``。\n"
    # Match numpydoc's field-list and rubric structure used by SciPy. The
    # Chinese prose remains a projection; no scientific module is imported.
    for label in (
        "异常与失败行为",
        "说明",
        "适用范围",
        "相关函数",
        "示例",
        "验证与限制",
        "参考资料",
    ):
        out = out.replace(title(label, "-"), ".. rubric:: " + label + "\n\n")
    heading = (
        '.. raw:: html\n\n   <p class="scirel-module">'
        + py["module"]
        + ".</p>\n\n"
        + title(py["symbol"])
    )
    return (
        heading
        + ".. py:function:: "
        + py["signature"]
        + "\n   :no-index-entry:\n\n"
        + "".join("   " + line + "\n" if line else "\n" for line in out.splitlines())
    )


def _render_english_api(doc, related):
    """Render one API page from the English contract fields only."""
    py = doc["public_api"]["python"]
    asset = doc["asset_id"]
    identity = doc["identity"]
    verification = doc["verification"]
    out = plain(doc["title"]["en"]) + ". " + plain(doc["summary"]) + "\n\n"
    out += "Implementation version: ``" + doc["version"]["implementation_version"] + "``. "
    out += "Scientific relation function.\n\n"
    out += ports(doc, None, "inputs", language="en") + ports(doc, None, "outputs", language="en")
    out += title("Exceptions and failure behavior", "-")
    for key, label in [
        ("invalid_input", "Invalid input"),
        ("runtime_failure", "Runtime failure"),
        ("nonconvergence", "Non-convergence"),
        ("partial_results", "Partial results"),
    ]:
        out += "**" + label + "**\n    " + plain(doc["failure_semantics"][key]) + "\n\n"
    out += title("Description", "-") + plain(identity["definition"]) + "\n\n"
    out += "**Model:** " + plain(identity["model"]) + "\n\n"
    out += "**Boundary convention:** " + plain(identity["boundary"]) + "\n\n"
    out += bullets(identity["assumptions"])
    out += title("Applicability", "-")
    out += "**Preconditions**\n\n" + bullets(doc["applicability"]["preconditions"])
    out += "**Supported**\n\n" + bullets(doc["applicability"]["supported"])
    out += "**Excluded**\n\n" + bullets(doc["applicability"]["excluded"])
    out += title("Related functions", "-")
    if related:
        out += (
            "".join(
                "* "
                + doclink(d["public_api"]["python"]["symbol"], api_path(d["asset_id"]))
                + " — "
                + plain(d["title"]["en"])
                + "\n"
                for d in related
            )
            + "\n"
        )
    else:
        out += (
            "Return to the domain API reference and choose another relation by "
            "scientific problem.\n\n"
        )
    out += title("Example", "-") + plain(doc["example"]["description"]) + "\n\n"
    out += code(doc["example"]["code"])
    out += "**Expected behavior:** " + plain(doc["example"]["expected"]) + "\n\n"
    out += (
        "The code above is the exact contract example; expected behavior and executed "
        "results are recorded separately.\n\n"
    )
    out += (
        title("Verification and limitations", "-")
        + plain(verification["evidence_ceiling"])
        + "\n\n"
    )
    out += "**Verified scope**\n\n" + bullets(verification["scope"])
    out += "**Known limitations**\n\n" + bullets(verification["known_limitations"])
    out += title("References", "-")
    for ref in doc.get("references", []):
        out += (
            "* "
            + plain(json.dumps(ref, ensure_ascii=False) if isinstance(ref, dict) else ref)
            + "\n"
        )
    out += "\n`Read the exact contract JSON </api/asset?id=" + asset + ">`_\n\n"
    for label in (
        "Exceptions and failure behavior",
        "Description",
        "Applicability",
        "Related functions",
        "Example",
        "Verification and limitations",
        "References",
    ):
        out = out.replace(title(label, "-"), ".. rubric:: " + label + "\n\n")
    heading = (
        '.. raw:: html\n\n   <p class="scirel-module">'
        + py["module"]
        + ".</p>\n\n"
        + title(py["symbol"])
    )
    return (
        heading
        + ".. py:function:: "
        + py["signature"]
        + "\n   :no-index-entry:\n\n"
        + "".join("   " + line + "\n" if line else "\n" for line in out.splitlines())
    )


def render_tutorial(chapter):
    c = chapter
    r = c["results"]
    out = title(c["title"]) + c["introduction"] + "\n\n" + c["prerequisites"] + "\n\n"
    out += title("模型与准备", "-") + bullets(c["conventions"]) + code(c["imports"])
    out += "以下小节按顺序运行，共享变量。完整脚本与执行记录在本页末尾提供。\n\n"
    for s in c["sections"]:
        out += ".. _" + s["id"] + ":\n\n" + title(s["title"], "-")
        out += s["problem"] + "\n\n" + s["method"] + "\n\n"
        if s.get("formula_mathml"):
            out += (
                '.. raw:: html\n\n   <div class="scirel-formula">'
                + s["formula_mathml"]
                + "</div>\n\n"
            )
            out += s["formula_note"] + "\n\n"
        out += code(s["code"]) + title("运行结果", "~")
        key = s["result_key"]
        if key == "single":
            out += f"中心 Bz = {r['center_single_T'] * 1000:.6f} mT；141 个轴上点与解析公式的最大绝对差为 {r['checks']['axis_max_abs_error_T']:.3e} T。\n\n"
        elif key == "pair":
            out += f"每环 1000 A 同向通电时，中心 Bz = {r['center_pair_T'] * 1000:.6f} mT；反向通电时，中心 Bz = {r['opposed_BZ_T'][70] * 1000:.6f} mT。\n\n"
        elif key == "rectangle":
            out += f"每组 64 根细丝，共 128 根；观测网格为 101 × 61。中心 Bz = {r['refinement_center_T'][2] * 1000:.6f} mT。\n\n"
        elif key == "checks":
            out += ".. list-table:: 中心观测点的离散加密检查\n   :header-rows: 1\n\n   * - 每组离散\n     - 中心 Bz / mT\n     - 相对上一行变化\n"
            for i, n in enumerate(r["refinement_n"]):
                change = (
                    "—"
                    if i == 0
                    else f"{(r['refinement_center_T'][i] / r['refinement_center_T'][i - 1] - 1) * 100:.4f}%"
                )
                out += f"   * - {n} × {n}\n     - {r['refinement_center_T'][i] * 1000:.6f}\n     - {change}\n"
            out += "\n轴上公式、几何对称性、电流线性叠加和有限值检查均通过。\n\n"
        if s.get("figure"):
            out += (
                ".. figure:: /_static/examples/"
                + s["figure"]
                + "\n   :alt: "
                + s["caption"]
                + "\n\n   "
                + s["caption"]
                + "\n\n"
            )
        out += title("结果解释", "~") + s["interpretation"] + "\n\n"
    out += ".. _limits:\n\n" + title("适用范围与常见误用", "-") + bullets(c["limitations"])
    out += ".. _reference:\n\n" + title("复现与函数参考", "-") + c["run"] + "\n\n"
    out += "`下载完整 Python 脚本 </chapters/magnetostatics/example.py>`_ · `下载实际结果 </chapters/magnetostatics/results.json>`_\n\n"
    out += (
        "".join("* " + doclink(x["purpose"], api_path(x["id"])) + "\n" for x in c["assets"]) + "\n"
    )
    out += "`读取实际执行绑定与完整章节 </api/chapter?id=magnetostatics>`_\n"
    return out


def render_matrix_page(matrix, *, language="zh"):
    """Render the capability matrix as a Sphinx page linked to function pages."""
    if language == "en":
        return _render_english_matrix_page(matrix)
    out = title("能力矩阵")
    out += (
        f"本快照收录 **{matrix['total_assets']}** 个能力，分布在 **{matrix['total_domains']}** 个领域。"
        "矩阵是 catalog 的派生视图，用于观察领域覆盖和函数入口；它不是缺口清单，也不代表人工批准。\n\n"
    )
    out += (
        "`下载 capability-matrix.json </capability-matrix.json>`_ · "
        "`下载 CAPABILITY_MATRIX.md </CAPABILITY_MATRIX.md>`_\n\n"
    )
    out += (
        title("领域覆盖", "-")
        + ".. list-table::\n   :header-rows: 1\n\n   * - 领域\n     - 能力数\n     - 代表函数\n"
    )
    assets = {a["asset_id"]: a for a in matrix["assets"]}
    for group in matrix["domains"]:
        symbols = [assets[a]["symbol"] for a in group["assets"][:4]]
        out += f"   * - ``{group['domain']}``\n     - {group['count']}\n     - {', '.join('``' + s + '``' for s in symbols)}\n"
    out += "\n" + title("能力清单", "-")
    for group in matrix["domains"]:
        out += title(group["domain"] + f"（{group['count']}）", "~")
        out += (
            ".. list-table::\n   :header-rows: 1\n   :widths: 25 30 35 10\n\n"
            "   * - 函数\n     - 中文能力\n     - 端口\n     - 测试数\n"
        )
        for asset_id in group["assets"]:
            a = assets[asset_id]
            ports = a["ports"].replace("|", "\\|")
            if len(ports) > 110:
                ports = ports[:107] + "…"
            out += (
                f"   * - {doclink(a['symbol'], api_path(asset_id))}\n"
                f"     - {plain(a['title_zh'] or a['title_en'])}\n"
                f"     - {plain(ports)}\n"
                f"     - {len(a['tests'])}\n"
            )
        out += "\n"
    return out


def _render_english_matrix_page(matrix):
    """Render the capability matrix as an English Sphinx page."""
    out = title("Capability matrix")
    out += (
        f"This snapshot contains **{matrix['total_assets']}** capabilities across "
        f"**{matrix['total_domains']}** domains. The matrix is a derived catalog view "
        "for domain coverage and function entry points; it is not a gap inventory and "
        "does not represent human approval.\n\n"
    )
    out += (
        "`Download capability-matrix.json </capability-matrix.json>`_ · "
        "`Download CAPABILITY_MATRIX.md </CAPABILITY_MATRIX.md>`_\n\n"
    )
    out += (
        title("Domain coverage", "-") + ".. list-table::\n   :header-rows: 1\n\n"
        "   * - Domain\n     - Capabilities\n     - Representative functions\n"
    )
    assets = {a["asset_id"]: a for a in matrix["assets"]}
    for group in matrix["domains"]:
        symbols = [assets[a]["symbol"] for a in group["assets"][:4]]
        out += (
            f"   * - ``{group['domain']}``\n     - {group['count']}\n"
            f"     - {', '.join('``' + s + '``' for s in symbols)}\n"
        )
    out += "\n" + title("Capability list", "-")
    for group in matrix["domains"]:
        out += title(group["domain"] + f" ({group['count']})", "~")
        out += (
            ".. list-table::\n   :header-rows: 1\n   :widths: 25 30 35 10\n\n"
            "   * - Function\n     - Capability\n     - Ports\n     - Tests\n"
        )
        for asset_id in group["assets"]:
            a = assets[asset_id]
            port_text = a["ports"].replace("|", "\\|")
            if len(port_text) > 110:
                port_text = port_text[:107] + "..."
            out += (
                f"   * - {doclink(a['symbol'], api_path(asset_id))}\n"
                f"     - {plain(a['title_en'] or a['title_zh'])}\n"
                f"     - {plain(port_text)}\n"
                f"     - {len(a['tests'])}\n"
            )
        out += "\n"
    return out


def _render_english_site(root, docs, book, *, matrix=None):
    """Render the English site from reviewed glossary and guide inputs.

    Navigation prose comes from ``tools/docs/handbook.en.json``.  A chapter is
    rendered from its authored ``tools/docs/manual/en/<chapter-id>.rst`` file
    when one exists, otherwise it receives an explicit English placeholder.
    Chinese guide text is never copied into English pages and no translation is
    invented.  API pages, matrix and search are contract-derived.
    """
    by_id = {d["asset_id"]: d for d in docs}
    available_docs = english_available_docs(root, book, set(by_id), matrix=matrix)
    with tempfile.TemporaryDirectory(prefix="scirel-sphinx-en-") as temp:
        stage = Path(temp)
        source = stage / "source"
        output = stage / "html"
        shutil.copytree(
            root / "tools/docs/sphinx", source, ignore=shutil.ignore_patterns("requirements.txt")
        )
        shutil.rmtree(source / "tutorials", ignore_errors=True)
        # The Chinese getting-started/agent pages are not part of the English
        # skeleton; remove them from the staged source instead of copying or
        # machine-translating their prose.
        for name in ("getting-started.rst", "agent.rst"):
            (source / name).unlink(missing_ok=True)

        def write(path, text):
            p = source / (path + ".rst")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)

        # English guide chapters may cross-reference the execution-backed
        # tutorials.  The staged English site has no Chinese tutorial prose, so
        # give those docnames explicit English placeholders rather than letting
        # Sphinx fail on unresolved references.
        tutorial_ids = []
        canonical_path = Path(root) / "tools/docs/handbook.json"
        if canonical_path.is_file():
            for chapter in json.loads(canonical_path.read_bytes())["chapters"]:
                for topic in chapter["topics"]:
                    tutorial_id = topic.get("tutorial_id")
                    if tutorial_id and tutorial_id not in tutorial_ids:
                        tutorial_ids.append(tutorial_id)
        for tutorial_id in tutorial_ids:
            write(
                "tutorials/" + tutorial_id,
                title(tutorial_id.replace("-", " ").title())
                + "English tutorial text for this execution-backed case is not authored yet. "
                "The contract-derived API reference and the chapter guides are available; "
                "this page is an explicit placeholder so that guide cross-references remain valid.\n\n",
            )

        home = title("SciRel documentation")
        home += (
            "SciRel is a Python library of scientific relations. Choose a single "
            "scientific function for a well-defined problem, or compose several "
            "relations after checking their contracts.\n\n"
        )
        home += ".. grid:: 1 2 2 2\n   :gutter: 3\n\n"
        cards = [
            (
                "User guide",
                "user-guide/index",
                "Reviewed English guide chapters; chapters still in progress show an explicit placeholder.",
            ),
            (
                "API reference",
                "reference/index",
                "Contract-derived signatures, ports, failure behavior, applicability and examples.",
            ),
        ]
        if matrix is not None:
            cards.insert(
                1,
                (
                    "Capability matrix",
                    "user-guide/capability-matrix",
                    "Domain coverage, function entry points, ports and test counts.",
                ),
            )
        for label, target, description in cards:
            home += (
                "   .. grid-item-card:: "
                + label
                + "\n      :link: "
                + target
                + "\n      :link-type: doc\n\n      "
                + description
                + "\n\n"
            )
        home += (
            "This is a development snapshot. Each function keeps its own implementation "
            "version; use the applicability and evidence scope on its API page.\n\n"
        )
        home += toctree(
            ["user-guide/index", "reference/index"]
            + ["tutorials/" + tutorial_id for tutorial_id in tutorial_ids],
            hidden=True,
        )
        write("index", home)
        guide_links = [c["id"] for c in book["chapters"]]
        if matrix is not None:
            guide_links.append("capability-matrix")
        write(
            "user-guide/index",
            title("User guide")
            + (
                "The English user guide is authored chapter by chapter. Chapters with an "
                "English guide are shown in full; the remaining chapters show a placeholder "
                "until their English text is added.\n\n"
            )
            + toctree(guide_links),
        )
        if matrix is not None:
            write("user-guide/capability-matrix", render_matrix_page(matrix, language="en"))
        write(
            "reference/index",
            title("API reference")
            + (
                "Choose a scientific domain, then browse functions by problem. Each function "
                "page gives signature, parameters, returns, failure behavior, applicability and "
                "examples.\n\n"
            )
            + toctree([c["id"] for c in book["chapters"]], maxdepth=1),
        )
        for c in book["chapters"]:
            authored, guide_status = _english_guide_content(root, c["id"], available_docs)
            if authored is None:
                placeholder = (
                    ENGLISH_GUIDE_SUBSET_PLACEHOLDER
                    if guide_status == "subset-placeholder"
                    else ENGLISH_GUIDE_PLACEHOLDER
                )
                write("user-guide/" + c["id"], title(c["title"]) + placeholder + "\n\n")
            else:
                write(
                    "user-guide/" + c["id"],
                    authored if authored.endswith("\n") else authored + "\n",
                )
            ref = title(c["title"]) + c["introduction"] + "\n\n"
            for topic in c["topics"]:
                records = [by_id[a] for a in topic["assets"]]
                ref += title(topic["title"], "-") + topic["introduction"] + "\n\n"
                ref += title("Functions", "~") + function_table(records, None, language="en")
                ref += title("Model and conditions", "~")
                for d in records:
                    ref += (
                        "**"
                        + plain(d["title"]["en"])
                        + "**\n\n"
                        + plain(d["identity"]["definition"])
                        + "\n\n"
                        + plain(d["identity"]["boundary"])
                        + "\n\n"
                    )
                    ref += bullets(d["applicability"]["preconditions"])
                    ref += (
                        "See "
                        + doclink(d["public_api"]["python"]["symbol"], api_path(d["asset_id"]))
                        + " for parameters, outputs and failure behavior.\n\n"
                    )
                ref += title("Verification and boundaries", "~")
                for d in records:
                    ref += (
                        "**"
                        + plain(d["title"]["en"])
                        + "**\n\n"
                        + plain(d["verification"]["evidence_ceiling"])
                        + "\n\n"
                    )
                    ref += bullets(d["verification"]["known_limitations"])
                ref += toctree(
                    ["generated/" + d["asset_id"] for d in records], hidden=True, maxdepth=1
                )
                for d in records:
                    related_ids = [x["asset_id"] for x in records if x["asset_id"] != d["asset_id"]]
                    for dependency in d["version"].get("dependencies", []):
                        dependency_id = dependency["asset_id"]
                        if dependency_id not in related_ids:
                            related_ids.append(dependency_id)
                    write(
                        "reference/generated/" + d["asset_id"],
                        render_api(d, None, [by_id[a] for a in related_ids], language="en"),
                    )
            write("reference/" + c["id"], ref)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "sphinx",
                "-b",
                "html",
                "-W",
                "--keep-going",
                "-q",
                "-D",
                "language=en",
                "-D",
                "html_search_language=en",
                "-D",
                "html_title=SciRel documentation",
                str(source),
                str(output),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode:
            raise RuntimeError("Sphinx English build failed:\n" + result.stdout + result.stderr)
        files = {
            "web/" + p.relative_to(output).as_posix(): p.read_bytes()
            for p in output.rglob("*")
            if p.is_file() and ".doctrees" not in p.parts and p.name != ".buildinfo"
        }
        renderer = {
            "sphinx": version("Sphinx"),
            "pydata_sphinx_theme": version("pydata-sphinx-theme"),
            "sphinx_copybutton": version("sphinx-copybutton"),
            "sphinx_design": version("sphinx-design"),
            "pygments": version("Pygments"),
            "latex2mathml": version("latex2mathml"),
            "language": LANGUAGE_TAGS["en"],
            "warnings_as_errors": True,
            "science_imports": False,
            "reference": "https://docs.scipy.org/doc/scipy/",
            "source_documents": len(docs),
        }
        files["renderer.json"] = (
            json.dumps(renderer, ensure_ascii=False, indent=2) + "\n"
        ).encode()
        return files


def render_site(
    root,
    docs,
    book,
    translations,
    chapter,
    *,
    figure_files=None,
    matrix=None,
    language="zh",
    withheld_ids=(),
):
    """Return only generated public site bytes; staging sources stay temporary."""
    if language == "en":
        return _render_english_site(root, docs, book, matrix=matrix)
    assert figure_files is not None, "Chinese site needs the chapter figures"
    # Sphinx otherwise silently builds a Chinese search index of Latin words only.
    jieba_version = version("jieba")
    by_id = {d["asset_id"]: d for d in docs}
    with tempfile.TemporaryDirectory(prefix="scirel-sphinx-") as temp:
        stage = Path(temp)
        source = stage / "source"
        output = stage / "html"
        shutil.copytree(
            root / "tools/docs/sphinx", source, ignore=shutil.ignore_patterns("requirements.txt")
        )

        def write(path, text):
            p = source / (path + ".rst")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)

        # A guide referencing unavailable assets gets a chapter placeholder;
        # no withheld identifier or runnable unavailable API is published.
        home = title("SciRel 中文文档")
        home += "SciRel 是面向科学计算的 Python 关系库。按要解决的物理问题，选择单个科学函数，或使用组合多个关系的复合求解入口。\n\n"
        home += ".. grid:: 1 2 2 2\n   :gutter: 3\n\n"
        if not any(
            t.get("tutorial_id") == "kinetic-initial-value"
            for c in book["chapters"]
            for t in c["topics"]
        ):
            (source / "tutorials/kinetic-initial-value.rst").unlink(missing_ok=True)
        else:
            proof_path = kinetic_tutorial_proof(root)
            proof = json.loads(proof_path.read_bytes())
            bound_paths = {
                relative: (source_digest, digest)
                for relative, digest in proof["source_files"].items()
            }
            bound_paths.update(
                {
                    relative: (contract_digest, digest)
                    for relative, digest in proof["document_files"].items()
                }
            )
            bound_paths["tools/docs/sphinx/tutorials/kinetic-initial-value.rst"] = (
                source_digest,
                proof["tutorial_rst_sha256"],
            )
            if not proof["results"]["all_checks_passed"] or proof["environment"]["exit_code"] != 0:
                raise ValueError("kinetic tutorial has no successful execution")
            for relative, (measure, digest) in bound_paths.items():
                if measure(root / relative) != digest:
                    raise ValueError("kinetic tutorial execution binding changed: " + relative)
        cards = [
            (
                "用户指南",
                "user-guide/index",
                "从科学概念与输入约定入手，阅读领域导读和完整计算案例。",
            ),
            (
                "API 参考",
                "reference/index",
                "按科学领域查询调用签名、参数、返回值、失败行为、适用范围及示例。",
            ),
            (
                "开始使用",
                "getting-started",
                "了解精确安装包、单位约定，以及如何选择并验证一个科学关系。",
            ),
            ("Agent 查询", "agent", "按主题或精确资产标识读取与页面绑定的正式合同及中文说明。"),
        ]
        if matrix is not None:
            cards.insert(
                2,
                (
                    "能力矩阵",
                    "user-guide/capability-matrix",
                    "按领域查看当前能力覆盖、函数入口、端口和测试数量。",
                ),
            )
        for label, target, description in cards:
            home += (
                "   .. grid-item-card:: "
                + label
                + "\n      :link: "
                + target
                + "\n      :link-type: doc\n\n      "
                + description
                + "\n\n"
            )
        home += (
            "当前为开发文档。各函数保留自己的实现版本；请按 API 页的适用范围和具体安装包使用。\n\n"
        )
        home += toctree(
            ["getting-started", "user-guide/index", "reference/index", "agent"], hidden=True
        )
        write("index", home)
        write("getting-started", (root / "tools/docs/sphinx/getting-started.rst").read_text())
        write("agent", (root / "tools/docs/sphinx/agent.rst").read_text())
        guide_links = [c["id"] for c in book["chapters"]]
        if matrix is not None:
            guide_links.append("capability-matrix")
        write(
            "user-guide/index",
            title("用户指南")
            + "用户指南解释科学问题、模型选择与组合方式。函数的完整参数、单位和失败行为见 API 参考。\n\n"
            + toctree(guide_links)
            + title("完整计算案例", "-")
            + toctree(
                ["/tutorials/magnetostatics"]
                + (
                    ["/tutorials/kinetic-initial-value"]
                    if any(
                        t.get("tutorial_id") == "kinetic-initial-value"
                        for c in book["chapters"]
                        for t in c["topics"]
                    )
                    else []
                )
            ),
        )
        if matrix is not None:
            write("user-guide/capability-matrix", render_matrix_page(matrix))
        write(
            "reference/index",
            title("API 参考")
            + "按科学领域查阅功能函数。选择左侧领域，在正文中按问题浏览函数及用途，点击函数名查看参数、返回值、适用范围与示例。\n\n"
            + toctree([c["id"] for c in book["chapters"]], maxdepth=1),
        )
        manual_root = root / "tools/docs/manual"
        available_guides = english_available_docs(root, book, set(by_id), matrix=matrix)
        for c in book["chapters"]:
            authored = manual_root / (c["id"] + ".rst")
            if authored.is_file():
                authored_text = authored.read_text()
                if guide_selection_complete(authored_text, c["id"], available_guides):
                    write("user-guide/" + c["id"], authored_text)
                else:
                    write(
                        "user-guide/" + c["id"],
                        title(c["title"])
                        + "本章手写教程引用当前公开集合之外的能力，因此不在本快照提供。请查阅已公开的 API 参考。\n\n",
                    )
            else:
                # Never project contract prose into the user guide. Untranslated
                # chapters stay blank until an authored tutorial exists.
                write("user-guide/" + c["id"], title(c["title"]) + "本章手写教程尚未完成。\n\n")
            ref = title(c["title"]) + c["introduction"] + "\n\n"
            for topic in c["topics"]:
                records = [by_id[a] for a in topic["assets"]]
                intro = title(topic["title"]) + topic["introduction"] + "\n\n"
                intro += title("选择计算入口", "-")
                intro += function_table(records, translations)
                intro += title("模型与使用条件", "-")
                for d in records:
                    z = translations[d["asset_id"]]
                    intro += (
                        title(d["title"]["zh"], "~")
                        + plain(z["definition"])
                        + "\n\n"
                        + plain(z["boundary"])
                        + "\n\n"
                    )
                    intro += bullets(z["applicability"]["preconditions"])
                    intro += (
                        "详见 "
                        + doclink(d["public_api"]["python"]["symbol"], api_path(d["asset_id"]))
                        + " 的参数、输出和失败行为。\n\n"
                    )
                intro += title("验证与使用边界", "-")
                for d in records:
                    z = translations[d["asset_id"]]
                    intro += (
                        "**"
                        + plain(d["title"]["zh"])
                        + "**\n\n"
                        + plain(z["verification"]["evidence_ceiling"])
                        + "\n\n"
                        + bullets(z["verification"]["known_limitations"])
                    )
                if topic.get("tutorial_id"):
                    tutorial_id = topic["tutorial_id"]
                    tutorial_title = {
                        "magnetostatics": "轴对称线圈磁场：代码、实际结果与解释",
                        "kinetic-initial-value": "静电根与线性初值演化：实际结果及解释",
                    }[tutorial_id]
                    intro += (
                        title("计算案例", "-")
                        + doclink(tutorial_title, "/tutorials/" + tutorial_id)
                        + "\n"
                    )
                ref += title(topic["title"], "-") + topic["introduction"] + "\n\n"
                ref += function_table(records, translations)
                ref += toctree(
                    ["generated/" + d["asset_id"] for d in records], hidden=True, maxdepth=1
                )
                for d in records:
                    related_ids = [x["asset_id"] for x in records if x["asset_id"] != d["asset_id"]]
                    for dependency in d["version"].get("dependencies", []):
                        dependency_id = dependency["asset_id"]
                        if dependency_id not in related_ids:
                            related_ids.append(dependency_id)
                    write(
                        "reference/generated/" + d["asset_id"],
                        render_api(d, translations[d["asset_id"]], [by_id[a] for a in related_ids]),
                    )
            write("reference/" + c["id"], ref)
        write("tutorials/magnetostatics", render_tutorial(chapter))
        examples = source / "_static/examples"
        examples.mkdir()
        for name in ("single.svg", "pair.svg", "rectangle.svg"):
            (examples / name).write_bytes(figure_files[name])
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "sphinx",
                "-b",
                "html",
                "-W",
                "--keep-going",
                "-q",
                str(source),
                str(output),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode:
            raise RuntimeError("Sphinx build failed:\n" + result.stdout + result.stderr)
        files = {
            "web/" + p.relative_to(output).as_posix(): p.read_bytes()
            for p in output.rglob("*")
            if p.is_file() and ".doctrees" not in p.parts and p.name != ".buildinfo"
        }
        renderer = {
            "sphinx": version("Sphinx"),
            "pydata_sphinx_theme": version("pydata-sphinx-theme"),
            "sphinx_copybutton": version("sphinx-copybutton"),
            "sphinx_design": version("sphinx-design"),
            "pygments": version("Pygments"),
            "jieba": jieba_version,
            "latex2mathml": version("latex2mathml"),
            "language": "zh-CN",
            "warnings_as_errors": True,
            "science_imports": False,
            "reference": "https://docs.scipy.org/doc/scipy/",
            "source_documents": len(docs),
        }
        files["renderer.json"] = (
            json.dumps(renderer, ensure_ascii=False, indent=2) + "\n"
        ).encode()
        return files
