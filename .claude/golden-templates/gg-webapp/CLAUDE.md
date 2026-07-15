# gg-webapp — 프로젝트 레일 (Track A)

- 런타임 Python 3.12 / PostgreSQL 16 고정. 승인 패키지(package-catalog)만.
- 비밀값 `.env`/환경변수만, 리터럴 금지. `.env.example`만 커밋.
- DB는 SQLAlchemy 파라미터 바인딩만. 문자열 조립 쿼리·`os.system` 금지.
- 개인정보 평문 저장 금지, 더미 데이터. XSS: 템플릿 이스케이프 유지, `debug=True` 금지.
- 외부통신(CDN·외부API·LLM) 금지. 정적자산 self-host. 필요 시 예외신청.
- 인증 직접 구현 금지 — Keycloak(OIDC). `/health`·보안헤더·base_path 제거 금지.
- 보안 검사는 여기서 안 함 — 게이트(security-reviewer/gvskb).
