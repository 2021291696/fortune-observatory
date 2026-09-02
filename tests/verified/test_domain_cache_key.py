from pathlib import Path


CONSOLE = (
    Path(__file__).resolve().parents[2]
    / "apps"
    / "observatory"
    / "src"
    / "components"
    / "DomainAnalysisConsole.tsx"
)


def test_f006_domain_cache_key_includes_chart_fingerprint() -> None:
    text = CONSOLE.read_text(encoding="utf-8")
    assert "cacheKey" in text
    assert "trace_id" in text or "traceId" in text
    for line in text.splitlines():
        if "cacheKey" in line and "ai-" in line:
            assert "trace" in line
