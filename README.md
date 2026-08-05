# gg-vibecode

공공기관 공무원이 바이브코딩으로 업무 도구를 구상·시제품화·내부도구화하고, 정식 운영이 필요할 때 운영팀과 보안팀이 이어받을 수 있는 산출물을 남기도록 돕는 **공공 바이브코딩 실행 하네스**입니다.

이 저장소는 [`revfactory/harness-100`](https://github.com/revfactory/harness-100)의 "전문 에이전트 팀 + 오케스트레이터 스킬 + 구조화 산출물" 방식을 참고하되, 범용 하네스 모음이 아니라 **행정망/외부망, 공공 보안, 승인 패키지, 배포·이관 산출물**을 지키는 공공 특화 하네스입니다. 특히 **규칙 중심·심플·토큰 효율**을 살린 Lean 설계로 개편했습니다.

## 관련 저장소 (전부 GitHub 주소로 씁니다)

로컬 사본을 따로 만들지 말고, 항상 아래 두 저장소를 원본으로 clone·설치해서 씁니다.

| 저장소 | 역할 | 사용법 |
|---|---|---|
| 이 저장소(`vibe_harness_claude`) | Claude Code용 하네스(`.claude/`) | `git clone https://github.com/Lex6won/vibe_harness_claude.git` |
| [`vibecode-checker`](https://github.com/Lex6won/vibecode-checker) | 보안검증 엔진(gvskb) — 이 하네스가 유일하게 신뢰하는 검사 엔진 | `pip install git+https://github.com/Lex6won/vibecode-checker.git` |

## 하네스 주제

**공공 바이브코딩 실행 하네스**입니다.

공무원이 "이런 업무 도구가 필요하다"고 말하면, AI가 업무 요구를 구체화하고 공공 운영환경에 맞는 개발 방향을 잡아주며, 보안·패키지·행정망/외부망 제약을 놓치지 않도록 돕습니다.

주요 대상은 다음과 같습니다.

- 공무원이 직접 만들어보는 내부 업무 보조 도구
- 엑셀/파일 기반 집계·조회·대시보드
- 부서 단위 시제품 또는 내부도구
- 정식 개발환경으로 이관할 후보 서비스
- 보안성검토·서버 설치·배포신청 산출물이 필요한 바이브코딩 결과물

## 구성 목적

이 하네스의 목적은 공무원을 전문 개발자로 바꾸는 것이 아닙니다.

목표는 다음입니다.

1. 공무원이 업무 아이디어를 쉽게 설명하도록 돕는다.
2. AI가 화면, 입력, 처리, 출력, 저장 여부를 구체화한다.
3. 공공 운영환경에 맞는 Track, 인증, DB, 패키지, 네트워크 기준을 자동으로 적용한다.
4. 골든 템플릿 안에서만 구현해 기술스택이 임의로 흐르지 않게 한다.
5. 개발 중에는 가볍게, 배포·이관 시에는 엄격하게 산출물을 만든다.
6. 운영팀·보안팀이 이어받을 수 있도록 요구서, 설계서, 보안점검, 배포신청 산출물을 남긴다.

설계 철학은 **규칙이 지능 · 게이트가 권위 · 성숙도가 강도 · 템플릿이 레일**이며, 움직이는 부품을 최소화합니다.

## At a Glance

| 항목 | 내용 |
|---|---:|
| 전문 에이전트 | 3개 |
| 스킬 | 2개 |
| 골든 템플릿 | 2개 실코드 + 4개 가이드 |
| 성숙도 단계 | L0~L4 |
| 주요 네트워크 프로파일 | 행정망 / DMZ·외부망 |
| 검증 엔진 | [vibecode-checker(gvskb)](https://github.com/Lex6won/vibecode-checker) MCP |
| 패키지 설치 게이트 | `enforcement/gvskb_gate.py`·`.js` (실제 pip/npm install을 통과/차단) |
| 보안검사 강도 | quick(개발 중)/standard(구현 완료)/full(배포 준비) 3모드 |

## 전체 구조

```text
gg-vibecode/
├── .mcp.json                         # vibecode-checker(gvskb) MCP 연결 — 반드시 프로젝트 루트(.claude/ 밖)
├── .claude/
│   ├── CLAUDE.md                     # 지능 중심: 원칙·성숙도·흐름·질문프레임·예방레일
│   ├── agents/                       # 비대화·격리 작업 전담 (3)
│   ├── skills/                       # 진입·질문 프레임 (2)
│   ├── references/                   # 정책·운영·보안 기계규칙 (8) — gvskb 검사 프로파일은 체커 내장 사용
│   ├── enforcement/                  # gvskb_gate.py·.js — 패키지 설치 실제 집행
│   ├── golden-templates/             # 레일 내장 실행 템플릿 + 변형 가이드
│   └── assets/                       # 산출물 템플릿·코칭 메시지
└── docs/                             # 레지스트리·체커 팀과의 집행계약·결정 기록
```

**`.mcp.json`은 반드시 프로젝트 루트에 있어야 합니다.** `.claude/` 안에 두면 Claude Code가
아예 읽지 않습니다(프로젝트 범위 MCP 설정의 공식 위치는 루트뿐입니다) — 아래 "하네스 복사" 단계에서
이 파일을 `.claude/`와 별도로 루트에 복사하는 이유입니다.

핵심 진입점은 다음입니다.

```text
.claude/CLAUDE.md
.claude/skills/gg-vibecode/skill.md
```

## 작동 흐름

대화·구현은 **메인 루프**(Claude)가 직접 하고, 비대화·격리 작업만 에이전트가 맡습니다(서브에이전트는 사용자와 대화하지 못하므로).

```text
[메인 루프]  접수(누가 쓰나·성숙도) → 질문(화면·입출력·MVP) → 되짚기 → 구현(골든 템플릿) → 반복
   → solution-architect   Track·인증·DB·runtime·보안제약 결정 (비대화)
   → security-reviewer     gvskb 게이트 → 코칭 번역 (검증/배포 시)
   → deploy-packager       배포·이관 핸드오프 산출물 (L3)
```

메인 루프는 gvskb MCP 도구(scan_path 등)를 직접 호출해 즉흥적으로 보안 판단을 내리지 않습니다 — 코드 검사는 오직 security-reviewer를 통해서만 이뤄집니다(보안은 게이트지 공기가 아니다). 단 하나의 예외가 있습니다: **패키지 설치**는 메인 루프가 `.claude/enforcement/gvskb_gate.py`(pip)·`.js`(npm)라는 고정된 결정론적 스크립트를 통해 매번 gvskb를 거칩니다. 에이전트가 그때그때 판단하는 게 아니라 정해진 규칙(카탈로그 우선순위·모드별 차단기준)을 코드로 고정해 둔 것이라 "즉흥 호출"이 아닙니다.

## 사용 방법

### 1. 하네스 복사

GitHub에서 받아 새 프로젝트에 `.claude`와 `.mcp.json`을 **둘 다** 복사합니다. 로컬 사본을 만들지
말고 항상 이 저장소를 원본으로 씁니다(기관 갱신·업데이트를 그대로 따라가기 위함).

```powershell
git clone https://github.com/Lex6won/vibe_harness_claude.git
Copy-Item -Recurse vibe_harness_claude\.claude C:\path\to\your-project\.claude
Copy-Item vibe_harness_claude\.mcp.json C:\path\to\your-project\.mcp.json
```

`.mcp.json`을 빠뜨리면 `.claude/`가 다 있어도 vibecode-checker MCP가 연결되지 않습니다 — 반드시
프로젝트 **루트**에 있어야 합니다(`.claude/` 안이 아님).

### 2. AI 도구에서 시작

Claude Code에서 다음처럼 요청합니다.

```text
우리 부서에서 엑셀 민원 현황 파일을 올리면 담당자별 처리 건수와 지연 건수를 대시보드로 보고 싶어.
```

기존 코드 수정, 배포·이관 준비도 자연어로 요청합니다.

```text
지난번 만든 대시보드에 엑셀 다운로드 버튼만 추가해줘.
이제 이 프로그램을 공식 개발환경으로 넘기고 보안성검토 신청 자료를 만들고 싶어.
```

### 3. 보안검증 준비 (개발 PC, Python 3.11+)

```bash
pip install git+https://github.com/Lex6won/vibecode-checker.git
gvskb doctor
```

## 실행 예시

### 입력 프롬프트

```text
우리 부서에서 매주 받는 민원 엑셀 파일을 올리면,
담당자별 처리 건수, 지연 건수, 이번 주 증가 건수를 대시보드로 보고 싶어.
우선 우리 부서 직원만 쓰는 내부 시제품이면 돼.
```

### 하네스의 판단 (메인 루프)

```yaml
maturity_level: L1
service_exposure: internal-staff
network_profile: admin-network
data_level: yellow_candidate
track: streamlit-internal   # 내부 대시보드 → gg-dashboard
risk_flags: [file_upload, possible_personal_data]
```

### 하네스가 되묻는 방식 (되짚기)

```text
이런 걸 만들게요.

- 엑셀 파일을 업로드한다.
- 담당자별 처리 건수와 지연 건수를 보여준다.
- 이번 주 증가 건수를 대시보드로 보여준다.
- 우선 우리 부서 직원만 보는 내부 시제품으로 만든다.
- 실제 개인정보 대신 테스트 데이터 기준으로 만든다.

맞나요?
```

### 선택되는 구현 방향

```text
템플릿: golden-templates/gg-dashboard   # solution-architect가 결정
네트워크: admin-network / 외부통신: 없음 / CDN: 사용 안 함
패키지: org-packages.yaml 승인 목록(gvskb_gate 경유 설치) / 검증: quick (게이트)
```

## 결과 예시

L1 시제품 완료 시 `_workspace`에는 최소한 다음이 남습니다.

```text
_workspace/
├── 01_요구서.md                     # 화면·입력·출력·MVP·위험 플래그
├── source/                          # gg-dashboard 기반 구현 소스
└── vibecode-manifest.json           # 성숙도·존·Track·산출물 상태
```

L3 배포·이관 준비로 승격하면 다음이 추가됩니다.

```text
_workspace/
├── 02_설계서.md                       # solution-architect
├── source/.check-reports/YYYY-MM-DD_HHMM_보안점검.{md,html,json}  # security-reviewer full 모드(제출 자료 ①, gvskb가 소스 루트 옆에 자동 저장)
├── gate-verdict.json                  # gvskb_gate verify-manifest 원본(제출 자료 ②)
├── 04_배포신청서.md                    # deploy-packager, 위 2종을 첨부로 링크
└── 05_예외신청서.md                    # (해당 시)
```

예상 `vibecode-manifest.json` 일부:

```json
{
  "project_id": "civil-dashboard-demo",
  "maturity_level": "L1",
  "service_exposure": "internal-staff",
  "network_profile": "admin-network",
  "data_level": "yellow",
  "track": "streamlit-internal",
  "checks": { "gvskb_verdict": "warn", "external_network": "allow" }
}
```

## 성숙도 단계

모든 결과물을 곧바로 정식 서비스로 보지 않습니다. 현재 목표 단계를 먼저 정하고, 단계에 맞는 절차와 검증 강도를 적용합니다.

| 단계 | 이름 | 의미 | 검증 강도 |
|---|---|---|---|
| L0 | 아이디어 구체화 | 화면·기능·입력·출력을 정리 | 문서 점검 |
| L1 | 시제품 | 내부 데모, 더미 데이터, 제한 사용 | quick |
| L2 | 내부도구 | 부서/기관 내 실제 업무 보조 | standard |
| L3 | 정식 서비스 후보 | 배포·공식 개발환경 이관 준비 | full gvskb |
| L4 | 정식 운영 | 승인된 운영환경 운영 | 하네스 단독 판정 금지 |

기본값은 L1이며 문서·절차를 얇게 유지합니다. 시민 접근, 개인정보, 외부통신, 파일업로드, 지속 저장 DB가 있으면 L2/L3 흐름으로 승격합니다.

## Agent Team

대화형 단계(접수·질문·구현)는 메인 루프가 직접 수행하고, 아래 3개 에이전트는 비대화·격리 작업만 맡습니다.

| 에이전트 | 역할 |
|---|---|
| `solution-architect` | 요구서 → Track·인증·DB·runtime·보안제약 결정 (사용자에게 안 물음) |
| `security-reviewer` | vibecode-checker(gvskb) 게이트 — 하네스에서 gvskb 툴을 가진 유일한 에이전트 |
| `deploy-packager` | 배포·이관 시 manifest 근거로 신청서·핸드오프 산출물 조립 |

## Skill System

| 스킬 | 역할 |
|---|---|
| `gg-vibecode` | 진입·모드·성숙도 판별 후 CLAUDE.md 흐름으로 안내 |
| `socratic-interview` | 요구 도출 프레임 — 고정 문항이 아니라 루브릭+창의질문+되짚기, 이미 말한 건 안 물음 |

접수·요구분석·구현 로직은 별도 에이전트/스킬이 아니라 `CLAUDE.md`(메인 루프 지침)에 담겨 있습니다.

## Golden Templates

코드는 빈 폴더에서 임의로 만들지 않고, 골든 템플릿 안에서 확장하는 것을 원칙으로 합니다. 핵심 2종은 레일 내장 실코드, 나머지는 이를 상속하는 변형 가이드(`_variants.md`)입니다.

| 템플릿 | Track | 형태 |
|---|---|---|
| `gg-webapp` | A | FastAPI 내부 웹/API (실코드) |
| `gg-dashboard` | S | Streamlit 내부 대시보드 (실코드) |
| gg-upload / gg-rag / gg-spa / gg-node-api | A/B/N | `_variants.md` 파생 가이드 |

각 템플릿은 레일을 내장합니다: `/health`·보안헤더·`.env.example`·의존성 고정(승인 패키지, `gvskb_gate` 경유 설치)·기관 내부 레지스트리 베이스(`org-environment.yaml`, 기본 Harbor)+HEALTHCHECK·파라미터 바인딩·인증 위임(`org-environment.yaml`의 auth_provider, 기본 Keycloak)·외부 CDN 금지·프로젝트 `CLAUDE.md`.

## Quality Standards

- Main-loop + Agents: 대화형은 메인 루프, 비대화·격리 작업만 에이전트(3)
- Rules-first: 지능을 CLAUDE.md에 집중해 부품·토큰 최소화
- Maturity Scaling: L1 thin / L2 internal / L3 release readiness
- Structured Outputs: 요구서, 설계서, 검증보고서, 배포신청서
- Public-Sector Guardrails: 행정망/DMZ 분기, CDN·외부 API·패키지 정책, gvskb 게이트
- Golden Templates: 승인 Track 템플릿 안에서 레일 내장 구현

## Network and Security Policy

네트워크/배포 정책의 원본은 `references/deploy-context.yaml`입니다.

기본 원칙:

- 행정망은 외부통신, CDN, 외부 SaaS SDK를 기본 금지합니다.
- 대민 서비스는 DMZ/외부망 후보이며 자동 승인하지 않습니다(WAF/DAST/위원회 승인 플래그).
- 보안검사 로직은 하네스가 직접 구현하지 않고 [`vibecode-checker`](https://github.com/Lex6won/vibecode-checker) 결과를 사용합니다(3단 폴백: MCP → CLI → 수동).

## Package Policy

"넓은 승인, 강한 차단." 승인·차단을 `references/org-packages.yaml` 한 파일에서 관리합니다.

- 미승인 패키지는 즉시 차단이 아니라 승인 대체안 먼저 제시 → 불가 시 예외신청.
- 강차단: Critical CVE·타이포스쿼트·외부 BaaS 직접 의존·CDN 운영 의존·postinstall 실행·임의 코드 실행.
- **실제 집행은 `enforcement/gvskb_gate.py`·`.js`가 담당합니다** — 코딩 중 새 패키지는 이 게이트를
  거쳐야 설치되고(카탈로그 → gvskb 절대차단 → 모드별 판정 순), 배포 준비(full 모드) 시에는
  `gvskb_gate.py verify-manifest`가 락파일 트리 전체를 다시 검증해 배포 제출 자료에 남깁니다.

## 다른 시군/기관으로 이식하기

이 하네스는 "경기도"에 고정된 게 아니라, **기관마다 달라지는 값을 2개 파일에 모아두고** 그 파일만
바꾸면 되도록 설계되어 있습니다. 나머지 레퍼런스 파일(`deploy-context.yaml`, `approved-tracks.yaml`,
`data-traffic-light.yaml`, `maturity-model.md`, `closed-network.md`, `exception-policy.md`)은
"판정 로직"만 담고 있어 대부분의 기관에서 그대로 재사용할 수 있습니다.

### 1. `references/org-environment.yaml` — 개발/운영 환경

- 존(zone) 가용성: 대민(외부망/DMZ) 서비스가 없는 기관이면 `network_zones.has_external_zone: false`
- 개발서버·운영서버 언어 버전: `runtime.dev` / `runtime.prod` (Python·Node 등)
- 허용 DBMS·버전·확장: `runtime.dbms`
- 컨테이너 쿼터·베이스 이미지·레지스트리·포트대역·base_path: `container`
- 인증 제공자(Keycloak 등), 레지스트리, 패키지 미러: `network_zones.internal` / `.external`
- 예외신청 승인 주체 명칭(조직 구조가 다르면 여기만 수정): `approval_authority`

### 2. `references/org-packages.yaml` — 승인/차단 패키지·플러그인

- `approved` / `restricted` / `denied` 목록을 기관 오프라인 미러(pip/npm/RPM) 기준으로 교체
- `강차단_기준`, `unknown_처리` 같은 판정 규칙은 정책 로직이라 보통 그대로 재사용 가능

### 3. 골든 템플릿 Dockerfile의 플레이스홀더 치환

`golden-templates/*/Dockerfile`의 `FROM {ORG_BASE_IMAGE_PYTHON_WEB}` 같은 플레이스홀더는
main 루프가 구현 단계에서 `org-environment.yaml`의 `container.base_images` 값으로 치환합니다.
새 기관의 레지스트리에 해당 태그 이미지가 실제로 존재해야 동작합니다.

### 4. gvskb 검사 강도 프로파일 — 기본은 손댈 필요 없음

`internal-db-query` 등 4종 + 개발 중 경량 점검용 `dev-quick`은 vibecode-checker에 **내장**되어
있어 하네스가 별도 사본을 관리하지 않습니다(`GVSKB_POLICIES_DIR` 미설정). 기관 보안 기준이
체커 내장 프로필과 달라 `severity_min`·`category_overrides`를 자체적으로 조정해야 하면, 그때만
`references/policies/`에 YAML 사본을 두고 `.mcp.json`의 `env`에
`"GVSKB_POLICIES_DIR": "${CLAUDE_PROJECT_DIR:-.}/.claude/references/policies"`를 추가해
재도입할 수 있습니다(순수 상대경로는 MCP 서버 실행 위치에 따라 해석되지 않으니 반드시
`${CLAUDE_PROJECT_DIR:-.}` 형태로 적을 것).

### 알려진 제약 (핵심 2개 파일 교체만으로는 안 끝나는 부분)

- 골든 템플릿 폴더명(`gg-webapp` 등)과 스킬명(`gg-vibecode`)은 여전히 "gg-" 접두사가 하드코딩되어
  있습니다. 기능상 동작에는 지장이 없지만, 완전한 브랜드 교체를 원하면 별도 리네이밍이 필요합니다.
- `.mcp.json`의 `GVSKB_MODE`는 `${GVSKB_MODE:-online}`로 되어 있어 **기본값은 online**(실시간
  취약점 조회)입니다. 행정망처럼 실제로 인터넷이 막힌 폐쇄망이면 OS/셸 환경변수로
  `GVSKB_MODE=offline`을 설정해 오프라인 인텔 번들(`closed-network.md` 참고)을 쓰게 하세요 —
  `.mcp.json` 파일 자체를 고칠 필요는 없습니다. 실제로 온라인 환경인데 이 값을 안 건드리면
  기본이 offline이던 이전 설정과 달리, 이제는 자동으로 최신 취약점 조회가 됩니다.

## Validation

```bash
# 골든 템플릿 스모크 (개발 PC)
cd .claude/golden-templates/gg-webapp && pip install -r requirements.txt && pytest
# gvskb 보안검증
gvskb scan <프로젝트 경로> --profile internal-db-query --fail-on block
```

## Current Status

- 하네스 구조(메인 루프 + 에이전트 3), 성숙도 모델, 골든 템플릿 2종 실코드 + 4종 변형 가이드 완료
- v0.5 질문 프레임(루브릭+창의질문+되짚기) 적용
- **기관 이식성**: 기관마다 달라지는 값을 `org-environment.yaml`·`org-packages.yaml` 두 파일로 통합(다른 시군/기관으로 이식하기 참고)
- **패키지 설치 집행**: `enforcement/gvskb_gate.py`·`.js`가 gvskb(vibecode-checker)·gg-trusted-registry 판정을 실제 pip/npm install 허용·차단으로 집행(카탈로그 우선순위, MONITOR/WARN/ENFORCE 모드, 사전승인 코드 기반 예외)
- **3단계 보안검사**: 개발 중(quick, `dev-quick` 프로파일)/구현 완료(standard)/배포 준비(full, 제출 자료 2종 고정)를 `security-reviewer`가 모드별로 수행
- **gg-trusted-registry 연동**: gvskb가 내부적으로 레지스트리를 조회하는 구조(하네스는 직접 조회하지 않음). 결정·회신 이력은 `docs/`에 있음
- 남은 과제: 실제 MCP 세션에서 `dev-quick` 프로파일 로드 확인, golden template smoke test, L1 프로젝트 end-to-end 실행 검증

## License

기관 내부 실증·검토 단계입니다. 공개 배포 전 라이선스 정책을 확정해야 합니다.
