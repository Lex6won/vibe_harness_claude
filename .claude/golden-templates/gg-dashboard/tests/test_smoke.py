"""smoke: app.py 구문·의존성 파싱 확인(실행은 qa가 /_stcore/health로)."""
from pathlib import Path


def test_compile():
    path = Path(__file__).resolve().parent.parent / "app.py"
    with open(path, encoding="utf-8") as f:
        compile(f.read(), str(path), "exec")
