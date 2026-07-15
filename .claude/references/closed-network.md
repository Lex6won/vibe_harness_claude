# 폐쇄망 제약 및 대체재 (행정망 internal 전용)

행정망은 외부 아웃바운드가 사실상 전무하다. AI가 만든 코드가 외부 통신을 전제하면
행정망에서 **동작하지 않는다**. 개발 시점부터 아래 대체재로 회피한다(builder 수동 예방).

| 외부 의존 | 행정망 대체재 |
|---|---|
| LLM API (Claude/OpenAI) | 망연계 프록시 / DMZ 중계 / 내부 sLLM (최우선 협의 사항) |
| CDN 스크립트·웹폰트 | 템플릿에 self-host(번들 내장) |
| 아이콘·CSS 프레임워크 | self-host |
| 지도 API / 외부 Open API | 내부 GIS 연계 / 데이터 사전반입 / DMZ 경유 |
| 이메일·SMS | 내부 알림 수단 연계 |
| 외부 BaaS (Supabase·Firebase) | DB→PostgreSQL, Auth→Keycloak 치환, 호출부 api 계층 분리 |
| 패키지 설치(pypi/npm) | 오프라인 미러(pip/npm/RPM) |
| gvskb 위협 인텔 | offline 번들(`gvskb intel-bundle import`, `GVSKB_MODE=offline`) |

## 코드-현실 강제 일치
- 존이 internal이면 security-reviewer가 `internal-db-query` 프로파일로 스캔 →
  `external_surface` 스캐너·`GOV-INTERNAL-NET-001`이 외부 통신 코드를 탐지·차단.
- 즉 "행정망"이라 답하고 외부 호출을 넣으면 게이트에서 걸린다(질문↔코드 일치).

## 외부망(external)은 다름
- 통제된 아웃바운드 허용. 단 LLM은 호출률·비용 방어, 외부 API는 조건부.
- self-host는 여전히 권장.
