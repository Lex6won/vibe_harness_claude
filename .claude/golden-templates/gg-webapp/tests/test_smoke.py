"""smoke: /health 200 + 보안헤더 확인. qa 성격 최소 검증."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite://")  # 스모크는 헬스·헤더만 확인
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_security_headers():
    h = client.get("/health").headers
    assert h.get("X-Frame-Options") == "DENY"
    assert "default-src 'self'" in h.get("Content-Security-Policy", "")
