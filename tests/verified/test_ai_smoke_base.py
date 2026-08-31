from pathlib import Path


SMOKE = Path(__file__).resolve().parents[1] / "e2e" / "ai_smoke_live.py"
BANNED = "sol-d2ga5fpq8bcf67f5a.service.tcloudbase.com"


def test_ai_smoke_live_does_not_hardcode_production_base() -> None:
    text = SMOKE.read_text(encoding="utf-8")
    assert BANNED not in text
    assert "127.0.0.1" in text or "localhost" in text
