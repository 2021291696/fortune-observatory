from pathlib import Path
import sys

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def _request_guard(app):
    current = getattr(app, "middleware_stack", None)
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if type(current).__name__ == "RequestGuardMiddleware":
            return current
        current = getattr(current, "app", None)
    return None


@pytest.fixture(autouse=True)
def reset_api_rate_limits() -> None:
    api_dir = str(PROJECT_ROOT / "apps" / "api")
    if api_dir not in sys.path:
        sys.path.insert(0, api_dir)
    try:
        import app as api_module
        guard = _request_guard(api_module.app)
    except Exception:
        yield
        return
    if guard is not None:
        guard._requests.clear()
        guard._global_requests.clear()
        guard._ai_requests.clear()
        guard._ai_global_requests.clear()
    yield
