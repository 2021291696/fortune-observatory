from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TASK_LAYOUT = ROOT / "apps" / "observatory" / "src" / "task-layout.css"
STYLES = ROOT / "apps" / "observatory" / "src" / "styles.css"


def test_f005_mobile_nav_is_five_columns() -> None:
    text = TASK_LAYOUT.read_text(encoding="utf-8")
    assert "repeat(5" in text
    assert "repeat(4, 1fr)" not in text


def test_f008_styles_do_not_hide_third_and_fourth_nav() -> None:
    text = STYLES.read_text(encoding="utf-8")
    assert "nth-child(3)" not in text or "display: none" not in text.split("nth-child(3)", 1)[-1][:80]
    assert ".site-header nav a:nth-child(3)" not in text
