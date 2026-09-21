"""中医问诊口径来源：读取仓库内倪海厦经方 skill（skills/nihaixia）的节选。

skills/nihaixia 是中医问诊能力的口径源（source of truth，逐字节同步自上游
nihaixia v2.3.1，与本地 ~/.agents/skills/nihaixia 实体相互独立）；本模块抽取
人格规则、蒸馏速查、常见问答与诊断公式注入 system prompt。modules/ 全库
（6.2M）不注入——线上服务没有 agentic 检索面，模型只能基于摘录与《伤寒》
《金匮》通行原文作答，摘录未覆盖的按口径明示「讲义未直接涉及」，不得编造。
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_API_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = _API_DIR.parents[1]
SKILL_DIR = PROJECT_ROOT / "skills" / "nihaixia"

# 注入 prompt 的单份材料上限（字符），防止上游 skill 增补后注入量失控。
_CAPS = {
    "persona_rules": 2600,
    "distilled": 2600,
    "faq": 1400,
    "identity": 400,
    "iron_laws": 900,
    "diagnosis": 12000,
    "expression": 6000,
}


def _slice(text: str, start_marker: str, end_marker: str | None, cap: int) -> str:
    begin = text.find(start_marker)
    if begin < 0:
        return ""
    body = text[begin:]
    if end_marker:
        end = body.find(end_marker, len(start_marker))
        if end > 0:
            body = body[:end]
    return body[:cap].strip()


@lru_cache(maxsize=1)
def _skill_text() -> str:
    try:
        return (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    except OSError:
        return ""


@lru_cache(maxsize=1)
def _expression_text() -> str:
    try:
        return (SKILL_DIR / "expression_style.md").read_text(encoding="utf-8")
    except OSError:
        return ""


def _persona_rules() -> str:
    return _slice(_skill_text(), "# 倪师表达速查卡", "# 知识库蒸馏精华速查", _CAPS["persona_rules"])


def _distilled() -> str:
    return _slice(_skill_text(), "## A. 开阖枢总图", "## F. 新增素材路径索引", _CAPS["distilled"])


def _faq() -> str:
    return _slice(_skill_text(), "## 常见问题速查", "# 倪海厦视角", _CAPS["faq"])


def _identity() -> str:
    return _slice(_skill_text(), "## 身份卡", "## 角色扮演规则", _CAPS["identity"])


def _iron_laws() -> str:
    return _slice(_skill_text(), "### 核心理论铁律", "## 回答工作流", _CAPS["iron_laws"])


def _diagnosis() -> str:
    return _slice(_skill_text(), "## 六经辨证诊断公式·临床速查", "## 深度内容模块", _CAPS["diagnosis"])


def _expression() -> str:
    return _expression_text()[: _CAPS["expression"]].strip()


def skill_profile() -> str:
    """拼接注入 system prompt 的口径材料；skill 副本缺失时返回空串，不阻断服务。"""
    parts: list[str] = []
    for name, body in (
        ("身份", _identity()),
        ("表达规则（速查卡）", _persona_rules()),
        ("表达范式（节选）", _expression()),
        ("理论铁律", _iron_laws()),
        ("知识库蒸馏速查", _distilled()),
        ("六经辨证诊断公式", _diagnosis()),
        ("常见问题速查", _faq()),
    ):
        if body:
            parts.append(f"【{name}】\n{body}")
    return "\n\n".join(parts)
