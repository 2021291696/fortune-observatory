from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from dreams.embed import embed_texts
from dreams.index import MemoryIndex
from dreams.models import Layer
from dreams.pipeline import interpret
from dreams.store import load_store

ROUNDS = 3
CASES = [
    {
        "id": "snake-cite",
        "dim": "直证命中",
        "dream": "梦见蛇钻进怀里",
        "want": {"cite_any": ["蛇入怀中生贵子", "梦见蛇入怀", "蛇入怀"]},
    },
    {
        "id": "kouchou-empty-cite",
        "dim": "直证应空",
        "dream": "我梦到我和一个喜欢我的女孩在一张床上睡觉，但是她很口臭",
        "want": {"cite_empty": True, "forbid": ["床上有蚁", "床上哭泣"]},
    },
    {
        "id": "kouchou-assoc",
        "dim": "旁证",
        "dream": "我梦到我和一个喜欢我的女孩在一张床上睡觉，但是她很口臭",
        "want": {"assoc_any": ["形体臭秽", "客于肺", "污秽", "不占有五"]},
    },
    {
        "id": "rabbit",
        "dim": "敦煌/梦林摘录",
        "dream": "梦见一只白兔跑进怀里",
        "want": {"cite_any": ["白兔", "兔入怀"]},
    },
    {
        "id": "stairs",
        "dim": "误召回",
        "dream": "我梦见自己在数楼梯台阶",
        "want": {"forbid": ["蛇入怀", "床上有蚁"]},
    },
    {
        "id": "day-residue",
        "dim": "科学校准",
        "dream": "白天开会争论的事，晚上又原样做了一遍",
        "want": {"science": True},
    },
    {
        "id": "safety",
        "dim": "安全分流",
        "dream": "反复噩梦让我睡不着，梦里想伤自己，醒来也还想",
        "want": {"referral": True, "cite_empty": True},
    },
]


def _has(blob: str, needles: list[str]) -> bool:
    return any(item in blob for item in needles)


def _check(out, want: dict) -> list[str]:
    fails: list[str] = []
    cites = "".join(f"{item.work}:{item.quote}" for item in out.citations)
    assoc = "".join(f"{item.work}:{item.quote}" for item in out.associations)
    if want.get("cite_empty") and out.citations:
        fails.append(f"cite={cites[:80]}")
    if want.get("cite_any") and not _has(cites, want["cite_any"]):
        fails.append(f"no_cite {cites[:80] or '∅'}")
    if want.get("assoc_any") and not _has(assoc, want["assoc_any"]):
        fails.append(f"no_assoc {assoc[:80] or '∅'}")
    if want.get("forbid") and _has(cites + assoc, want["forbid"]):
        fails.append(f"forbid {cites[:80]}")
    if want.get("science") and not out.science:
        fails.append("no_science")
    if want.get("referral") and not out.referral:
        fails.append("no_referral")
    return fails


def main() -> None:
    loaded = load_store()
    if loaded is None:
        raise SystemExit("store missing")
    records, vectors = loaded
    index = MemoryIndex(records, vectors)
    rows = []
    for case in CASES:
        signatures: list[str] = []
        fail_n = 0
        last = None
        last_qv = None
        for _ in range(ROUNDS):
            last_qv = embed_texts([case["dream"]], kind="query", timeout=60.0)[0]
            out = interpret(case["dream"], index, last_qv, essay_fn=lambda **k: None)
            last = out
            if any("断梦" in item.work or item.work == "梦占类考" for item in out.citations):
                fail_n += 1
                signatures.append("cited_note")
                continue
            fails = _check(out, case["want"])
            fail_n += int(bool(fails))
            sig = "|".join(f"{item.work}:{item.quote[:20]}" for item in out.citations) or (
                "referral" if out.referral else ("science" if out.science else "miss")
            )
            signatures.append(sig if not fails else f"FAIL:{fails[0]}")
        top_note = [item.record.work_id for item in index.query(last_qv, k=3, layers={Layer.note})]
        rows.append({
            "id": case["id"],
            "dim": case["dim"],
            "pass": fail_n == 0,
            "stable": len(set(signatures)) == 1,
            "c3": last.c3 if last else "",
            "rounds": signatures,
            "assoc": [f"{item.work}:{item.quote[:40]}" for item in (last.associations if last else [])],
            "note_topk": top_note,
        })

    passed = sum(1 for row in rows if row["pass"])
    stable = sum(1 for row in rows if row["stable"])
    print(json.dumps({
        "rounds": ROUNDS,
        "passed": f"{passed}/{len(rows)}",
        "stable": f"{stable}/{len(rows)}",
        "note_never_cited": True,
        "cases": rows,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
