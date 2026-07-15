# gg-dashboard — 프로젝트 레일 (Track S)

- 런타임 Python 3.12 / PostgreSQL 16 고정. 승인 패키지만.
- **내부 한정.** 시민 접근이면 Track S 금지 → gg-webapp/gg-spa 재설계 요청.
- 접근제어·보안헤더는 nginx 앞단(`nginx.conf`), Keycloak. Streamlit에 인증 직접 구현 금지.
- 비밀값 `.env`만. DB는 파라미터 바인딩. 개인정보 평문·실데이터 금지(더미).
- 외부통신·CDN 금지. 차트·자산 self-host. 검증은 게이트(security-reviewer/gvskb).
