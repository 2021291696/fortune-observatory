from __future__ import annotations

import re

_FURNITURE = re.compile(
    r"kodak|colorchecker|gray scale|xxrite|msccppp|内閣文库|内阁文库|内閣文庫|"
    r"番號|番号|册数|冊數|函号|函號|chec?ker",
    re.I,
)
_PAGE = re.compile(r"^##?\s*page\s+\d+", re.I)
_CJK = re.compile(r"[一-鿿]")


def clean_ocr(text: str) -> str:
    kept: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("- "):
            continue
        if _PAGE.match(line) or _FURNITURE.search(line):
            continue
        if re.fullmatch(r"[\d\s\-./]+", line):
            continue
        cjk = len(_CJK.findall(line))
        if cjk < 4 or cjk / max(len(line), 1) < 0.35:
            continue
        kept.append(line)
    return "\n".join(kept)


def unwrap_prose(text: str) -> str:
    start = text.find("*** START OF")
    if start >= 0:
        nl = text.find("\n", start)
        text = text[nl + 1:] if nl >= 0 else text
    end = text.find("*** END OF")
    if end >= 0:
        text = text[:end]
    paras: list[str] = []
    buf: list[str] = []
    for line in text.splitlines():
        piece = line.strip()
        if not piece:
            if buf:
                paras.append(" ".join(buf))
                buf = []
            continue
        buf.append(piece)
    if buf:
        paras.append(" ".join(buf))
    return "\n\n".join(paras)


def chunk_text(text: str, size: int = 800) -> list[str]:
    if size < 40:
        raise ValueError("chunk too small")
    out: list[str] = []
    buf = ""
    for para in text.split("\n"):
        piece = para.strip()
        if not piece:
            continue
        if buf and len(buf) + len(piece) + 1 > size:
            out.append(buf[:4000])
            buf = ""
        if len(piece) > size:
            if buf:
                out.append(buf[:4000])
                buf = ""
            for i in range(0, len(piece), size):
                out.append(piece[i:i + size][:4000])
            continue
        buf = f"{buf}\n{piece}".strip() if buf else piece
    if buf:
        out.append(buf[:4000])
    return [item for item in out if item]
