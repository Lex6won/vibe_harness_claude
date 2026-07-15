# gg-webapp (Track A · 기본)

Python 3.12 + FastAPI + Jinja2 내부 업무 웹앱 표준 템플릿. **이 구조 안에서만** 기능을 확장한다.

## 내장 레일
런타임 고정(3.12/PG16) · `/health` · base_path 주입 · 보안헤더(CSP·HSTS) · 비밀값 `.env`만 ·
SQLAlchemy 파라미터 바인딩(SQLi 예방) · Keycloak OIDC(직접 구현 금지) · 외부 CDN 금지(self-host) · 승인 패키지만.

## 실행 (L1)
```
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload   # /health , /
```

## 확장
새 화면 = `app/main.py`에 라우터 함수 + `app/templates/`에 템플릿. DB는 파라미터 바인딩만.
표준을 벗어나야 하면 solution-architect에 설계 조정 요청.
