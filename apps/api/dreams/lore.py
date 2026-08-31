"""解梦口径来源：读取仓库内荣格取向解梦 skill 的 references。

skills/dream-interpretation 是解梦能力的口径源（source of truth）；
本模块把其中与方法、象征直接相关的参考裁剪后注入 system prompt，
不再使用任何本地古籍语料或向量检索。
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_API_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = _API_DIR.parents[1]
SKILL_REFS_DIR = PROJECT_ROOT / "skills" / "dream-interpretation" / "references"

# 注入 prompt 的每份参考上限（字符），与 skill 参考文件实际大小对齐（全量注入）
_MAX_CHARS = {
    "dream-interpretation.md": 22000,
    "symbol-dictionary.md": 14000,
    "psyche-structure.md": 33000,
}

_WORK_TITLES = {
    "dream-interpretation.md": "荣格解梦方法论",
    "symbol-dictionary.md": "荣格象征词典",
    "psyche-structure.md": "荣格心灵结构",
}


@lru_cache(maxsize=8)
def load_reference(filename: str) -> str:
    """读取一份 skill 参考；文件缺失时返回空串，不阻断解梦。"""
    limit = _MAX_CHARS.get(filename, 6000)
    path = SKILL_REFS_DIR / filename
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    return text[:limit]


def skill_profile() -> str:
    """拼接注入 system prompt 的口径材料。"""
    parts: list[str] = []
    for filename in ("dream-interpretation.md", "psyche-structure.md", "symbol-dictionary.md"):
        body = load_reference(filename)
        if body:
            title = _WORK_TITLES.get(filename, filename)
            parts.append(f"《{title}》（节选）：\n{body}")
    return "\n\n".join(parts)
