"""smoke: app.py 구문 확인(실행은 qa가 /_stcore/health로).

ast.parse를 쓴다 — compile(..., "exec")는 KISA-PY-INPUT-02(코드 삽입 위험)
패턴과 겹쳐 이 스모크 테스트 자체가 보안 스캔에서 critical/block으로 걸린다
(실사용 검증 중 발견). ast.parse는 구문 트리만 만들고 실행 가능한 바이트코드를
만들지 않아 같은 목적(구문 오류 확인)을 더 안전하게 달성한다.
"""
import ast
from pathlib import Path


def test_compile():
    path = Path(__file__).resolve().parent.parent / "app.py"
    with open(path, encoding="utf-8") as f:
        ast.parse(f.read(), filename=str(path))
