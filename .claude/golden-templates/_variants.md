# 골든 템플릿 변형 가이드

핵심 2종(`gg-webapp` Track A, `gg-dashboard` Track S)은 실코드로 제공한다.
아래 4종은 **핵심 2종의 레일을 상속해 파생**한다(같은 레일을 반드시 유지). solution-architect가 Track을 정하면 메인 루프가 이 가이드대로 확장한다.

## 공통 레일 (모든 변형 필수)
런타임 고정 · `/health` · 보안헤더 · 비밀값 `.env`만 · 파라미터 바인딩(SQLi 예방) · 외부 CDN/외부통신 금지(행정망) · 승인 패키지(package-catalog)만 · 인증 위임(Keycloak/OIDC) · 내부 Harbor 베이스+HEALTHCHECK · 프로젝트 CLAUDE.md.

## gg-upload (Track A · 파일 업로드)
- 베이스: `gg-webapp` 상속.
- 추가 레일: **확장자 화이트리스트 · 용량 한도 · 안전한 파일명(경로조작 차단, 무작위 접두) · 웹서빙과 분리된 UPLOAD_DIR 저장(실행 위치 금지)**.
- 변환은 pandas/openpyxl(승인) 로컬 처리.

## gg-rag (Track A · 폐쇄망 문서검색)
- 베이스: `gg-webapp` 상속.
- **외부 LLM 없는 로컬 텍스트 검색만.** LLM 승격 시: 행정망은 망연계/내부 sLLM만, 프롬프트 인젝션 방어(시스템/사용자 입력 신뢰경계 분리), 출처 표시, 입력 개인정보 마스킹, 대화 미저장.

## gg-spa (Track B · React 정적 SPA)
- 프런트: React(Vite)+TS 정적 빌드(내부 `gg-node:20` 빌드), 호스트 nginx가 `/apps/<project>/` 서빙(보안헤더는 nginx).
- 백엔드: `gg-webapp`(FastAPI) API.
- 레일: **데이터 호출은 `src/lib/api.js` 한 곳으로만**(컴포넌트 직접 fetch·외부 BaaS 금지) · base_path는 vite base(VITE_BASE) 주입 · `npm ci --ignore-scripts`+lockfile.

## gg-node-api (Track N · Express)
- 베이스: 내부 `gg-node-web:20`.
- 레일: helmet(보안헤더) · express-rate-limit(호출률) · pg 파라미터 바인딩($1) · zod 입력검증 · pino 로그 · 인증은 openid-client/jose(Keycloak) · `npm ci --ignore-scripts`+lockfile.
- 사용자가 정당 사유(기존 TS 재사용) 언급 시만 선택.

## 미승인 스택 (Next.js SSR·Spring·Django·PHP·supabase-js 직접 등)
거절 아니라 "가까운 승인 Track + 선회"로 안내(approved-tracks.yaml).
