# evals — 회귀 테스트 / 실환경 검증 스크립트

references(신호등·Track·deploy-context)를 고칠 때마다 아래 3종을 재실행해 하네스 판단이
유지되는지 확인한다. **Python이 설치된 개발 PC**에서 gvskb와 함께 돌린다.

## 사전 준비 (개발 PC, 인터넷망)
```
pip install git+https://github.com/Lex6won/vibecode-checker.git
gvskb doctor            # 룰 수·인코딩·MCP 진단
```
Windows는 UTF-8 1회 설정(`docs/windows_utf8.md`).

## 실행 방법 2가지

### A. 하네스 전체 완주 (권장)
1. `gg-vibecode/.claude/`를 빈 테스트 프로젝트에 복사.
2. Claude Code에서 각 eval의 `input.user_request`를 입력 + `sample_code` 배치.
3. `/gg-vibecode` 완주 → `expected`·`pass_criteria`와 대조.

### B. gvskb 단독 확인 (게이트만 빠르게)
```
# 01: 개인정보 차단
gvskb scan ./test01 --profile internal-db-query --fail-on block
# 03: 외부 API (행정망)
gvskb scan ./test03 --profile internal-db-query --fail-on block
# 04: 정상 통과
gvskb scan ./test04 --profile internal-db-query
```
exit 0=통과, 1=warn, 2=block.

## 이번 실행의 핵심 확인 포인트 (설계 미검증 1건)
- `scan_path` / `scan` **반환 JSON의 실제 필드명**을 확인해,
  security-reviewer의 매핑(gvskb_verdict, 개별 findings의 rule_id·위치)과 일치시키기.
- 불일치 시 `agents/security-reviewer.md`의 절차 5~8과 `assets/manifest.schema.json`만 미세조정.

## 3종 요약
| id | 시나리오 | 기대 배포판정 |
|---|---|---|
| 01 | 개인정보 평문+SQL조립 | block |
| 03 | 행정망+외부 API | block(→예외신청 안내) |
| 04 | 표준 내부 대시보드(green) | ok |
