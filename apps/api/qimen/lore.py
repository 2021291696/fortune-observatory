"""奇门解读口径来源：读取仓库内奇门遁甲 skill 副本的 references。

skills/qimen-dunjia 是解读能力的口径源（仓库内副本，供线上使用）；
本模块把规则、取用神、格局与输出示例注入 system prompt。
interview.md 是 CLI 访谈话术，网页表单已替代，不注入。
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_API_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = _API_DIR.parents[1]
SKILL_REFS_DIR = PROJECT_ROOT / "skills" / "qimen-dunjia" / "references"

# 上限略高于文件实际大小（2.6K/2.0K/1.7K/6.7K），全量注入
_MAX_CHARS = {
    "ruleset-mainline.md": 4000,
    "yongshen.md": 3000,
    "geju.md": 3000,
    "examples.md": 8000,
}

_WORK_TITLES = {
    "ruleset-mainline.md": "奇门默认规则",
    "yongshen.md": "取用神顺序",
    "geju.md": "格局速览",
    "examples.md": "输出示例",
}


@lru_cache(maxsize=8)
def load_reference(filename: str) -> str:
    """读取一份 skill 参考；文件缺失时返回空串，不阻断解读。"""
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
    for filename in ("ruleset-mainline.md", "yongshen.md", "geju.md", "examples.md"):
        body = load_reference(filename)
        if body:
            title = _WORK_TITLES.get(filename, filename)
            parts.append(f"《{title}》：\n{body}")
    return "\n\n".join(parts)
