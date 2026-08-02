"""gvskb_gate — 하네스 집행 게이트 (Python).

`하네스_집행계약.md` §1의 요지: gvskb는 판정(verdict)만 내리고, gg-trusted-registry는
그 판정을 저장할 뿐이다. **실제로 pip/npm install을 실행하는 것은 하네스뿐**이므로,
그 판정을 무시하면 두 시스템이 만든 결과는 전부 무의미해진다. 이 파일이 그 "무시하지
않는" 지점이다.

패키지를 새로 설치할 때는 `pip install X` 를 직접 쓰지 말고 항상 이 스크립트를 거친다:

    python .claude/enforcement/gvskb_gate.py install <패키지명> [--version V] [--ecosystem pypi|npm]
    python .claude/enforcement/gvskb_gate.py check   <패키지명> [--json]
    python .claude/enforcement/gvskb_gate.py verify-manifest <requirements.txt 경로>

이 파일은 gvskb(vibecode-checker)가 로컬에 설치되어 있어야 동작한다:
    pip install git+https://github.com/Lex6won/vibecode-checker.git

설계상 결정(근거는 `docs/하네스_집행계약_반영및회신.md` 참고):
- verdict→조치 매핑, env_grade 자동결정, 카탈로그 우선순위, REJECTED 만료 처리는
  전부 이 파일 하나에 모아둔다. Node(.js) 쪽은 이 파일을 그대로 호출하는 얇은
  래퍼일 뿐, 판정 로직을 따로 구현하지 않는다(같은 보안 판단이 두 언어에서
  따로 구현되면 반드시 벌어지는 드리프트를 피하기 위함).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

try:
    import yaml
except ImportError:  # pragma: no cover - gvskb가 설치돼 있으면 PyYAML도 함께 온다
    yaml = None  # type: ignore[assignment]

Mode = Literal["MONITOR", "WARN", "ENFORCE"]
Action = Literal["pass", "warn", "block"]

EXIT_PASS = 0
EXIT_WARN = 1
EXIT_BLOCK = 2
EXIT_USAGE = 64
# 일반 사용법 오류(64)와 구분한다 — 메인 루프가 "사용자에게 설치를 물어봐야 하는
# 상황"인지 "명령을 잘못 쓴 상황"인지 종료코드만으로 구분할 수 있어야 stderr 문자열
# 파싱에 의존하지 않고 이 케이스를 안정적으로 처리할 수 있다.
EXIT_NOT_INSTALLED = 65

_MODE_RANK: dict[Action, int] = {"pass": 0, "warn": 1, "block": 2}
_VALID_MODES = ("MONITOR", "WARN", "ENFORCE")

# gvskb verdict 중 모드와 무관하게 항상 차단하는 것 (하네스_집행계약.md §3).
# in_kev·mismatch는 verdict가 아니라 별도 필드라 여기 넣지 않고 _absolute_block에서 본다.
_ABSOLUTE_BLOCK_VERDICTS = frozenset({"malicious", "registry_rejected", "not_found"})


# ---------------------------------------------------------------------------
# 설정 로딩 — org-environment.yaml(모드 기본값) · org-packages.yaml(로컬 카탈로그)
# ---------------------------------------------------------------------------


def _default_harness_root() -> Path:
    """이 파일은 <하네스>/.claude/enforcement/ 아래에 있다 — 그 부모가 .claude/."""
    return Path(__file__).resolve().parent.parent


def _load_yaml(path: Path) -> dict:
    if yaml is None or not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001 — 설정 파싱 실패가 게이트를 막으면 안 된다(보수적 기본값으로 계속)
        print(f"[gvskb_gate] ⚠ 설정 파일을 읽지 못했습니다({path}) — 기본값으로 진행합니다.", file=sys.stderr)
        return {}


def _resolve_mode(explicit: str | None, harness_root: Path) -> Mode:
    if explicit:
        m = explicit.upper()
        if m in _VALID_MODES:
            return m  # type: ignore[return-value]
    env = os.environ.get("GVSKB_GATE_MODE", "").upper()
    if env in _VALID_MODES:
        return env  # type: ignore[return-value]
    cfg = _load_yaml(harness_root / "references" / "org-environment.yaml")
    configured = str((cfg.get("enforcement") or {}).get("mode") or "").upper()
    if configured in _VALID_MODES:
        return configured  # type: ignore[return-value]
    # 기본값은 MONITOR다 — 레지스트리 데이터가 충분히 쌓이기 전에 ENFORCE로 시작하면
    # 개발이 통째로 막힌다(협의요청 §11: 지금은 데모 데이터 수준).
    return "MONITOR"


def _resolve_env_grade(explicit: str | None) -> str:
    """실행환경 등급(E0~E2) — 개발자가 고르지 않는다(협의요청 §5-2(a)).

    기본은 E1(개인 PC 세션). CI·빌드 파이프라인 신호가 보이면 E2로 올린다(더 엄격한
    쪽으로 자동 상향은 자유). E0나 E2→E1 하향은 반드시 명시적 override로만 가능하다 —
    그래야 "귀찮으면 항상 가장 느슨한 값을 고른다"는 도덕적 해이가 기본 경로에서
    발생하지 않는다.
    """
    if explicit in ("E0", "E1", "E2"):
        return explicit
    override = os.environ.get("GVSKB_GATE_ENV_GRADE", "")
    if override in ("E0", "E1", "E2"):
        return override
    ci_markers = ("CI", "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_URL", "BUILDKITE")
    if any(os.environ.get(m) for m in ci_markers):
        return "E2"
    return "E1"


def _load_catalog(harness_root: Path) -> dict:
    return _load_yaml(harness_root / "references" / "org-packages.yaml")


def _load_exception_codes(harness_root: Path) -> dict[str, str]:
    """org-environment.yaml enforcement.exception_codes — {코드: 설명}.

    사전 승인된 코드만 허용한다(자유문장 사유 금지 — 집계 불가·개인정보 유입 위험,
    레지스트리팀 회신 21번 §7 결정 반영). 절대차단·카탈로그 차단은 이 코드로도
    우회 못 한다 — evaluate_package의 exception_eligible 판단이 그걸 강제한다.
    """
    cfg = _load_yaml(harness_root / "references" / "org-environment.yaml")
    codes = (cfg.get("enforcement") or {}).get("exception_codes") or {}
    return {str(k): str(v) for k, v in codes.items()}


def _catalog_status(name: str, ecosystem: str, catalog: dict) -> str | None:
    """'denied' | 'pending_review' | 'approved' | None(카탈로그에 없음 — 판정 없음).

    org-packages.yaml은 gg-trusted-registry와 별개인 하네스 로컬 카탈로그다
    (하네스_집행계약.md §6). "카탈로그에 없음"은 거부도 승인도 아니다 — gvskb
    판정(및 그 안의 gg-trusted-registry 조회)으로 넘어간다.
    """
    name_l = name.lower()

    denied = catalog.get("denied") or {}
    if any(name_l == str(p).lower() for p in (denied.get("packages") or [])):
        return "denied"
    for p in denied.get("pending_review") or []:
        p_name = p if isinstance(p, str) else (p or {}).get("name", "")
        if str(p_name).lower() == name_l:
            return "pending_review"

    approved = catalog.get("approved") or {}
    pools: list[list[str]] = []
    if ecosystem == "pypi":
        pools.append(approved.get("python") or [])
    else:
        pools.append(approved.get("npm_frontend") or [])
        pools.append(approved.get("npm_backend") or [])
    for pool in pools:
        if any(name_l == str(p).lower() for p in pool):
            return "approved"
    return None


# ---------------------------------------------------------------------------
# verdict → 조치 매핑 (하네스_집행계약.md §4 표를 그대로 코드화)
# ---------------------------------------------------------------------------


def _absolute_block(result: dict) -> str | None:
    """모드와 무관하게 항상 차단해야 하는 신호. 있으면 사유 문자열, 없으면 None."""
    verdict = result.get("verdict")
    if verdict in _ABSOLUTE_BLOCK_VERDICTS:
        return result.get("note") or f"절대 차단 판정: {verdict}"
    if result.get("in_kev"):
        return "CISA KEV(실제 공격에 악용 중인 취약점) 대상입니다 — 예외 없이 차단합니다."
    # gvskb가 현재 mismatch 필드를 내지 않지만(회신 문서 결정 6 참고), 추후 추가되면
    # 코드 변경 없이 즉시 반영되도록 방어적으로 확인해 둔다.
    if result.get("mismatch"):
        return "해시/이름 불일치(MISMATCH) — 등록된 것과 다른 파일이 배포되고 있을 수 있습니다."
    return None


def _verdict_row(result: dict, mode: Mode) -> tuple[Action, str]:
    verdict = result.get("verdict")
    max_cve = result.get("max_cve", "NONE")

    if verdict == "vulnerable":
        # version_exact=False면 매니페스트 제약(예: requests>=2.28)의 경계값을 본 것이지
        # 실제 설치 버전을 관측한 게 아니다 — 가정만으로는 차단까지 가지 않는다
        # (변경통지 2026-08-03 §3-1). pip/npm이 실제로는 최신을 설치하므로 경고가
        # 실제로 맞을 일이 드물고, 차단하면 §4-2가 경고한 "멍청한 걸 막는다" 인상이 된다.
        version_exact = result.get("version_exact", True)
        if max_cve in ("CRITICAL", "HIGH"):
            action = {"MONITOR": "warn", "WARN": "block", "ENFORCE": "block"}[mode]
            if not version_exact:
                action = "warn" if _MODE_RANK[action] > _MODE_RANK["warn"] else action
            return action, f"취약점 심각도 {max_cve} — 조치된 버전이 있으면 그 버전으로 지정하세요."
        if max_cve == "UNKNOWN":
            action = {"MONITOR": "warn", "WARN": "warn", "ENFORCE": "block"}[mode]
            if not version_exact:
                action = "warn" if _MODE_RANK[action] > _MODE_RANK["warn"] else action
            return action, "취약점은 있으나 심각도가 미상입니다 — '안전'으로 확정할 수 없습니다."
        action = {"MONITOR": "pass", "WARN": "warn", "ENFORCE": "block"}[mode]
        if not version_exact:
            action = "warn" if _MODE_RANK[action] > _MODE_RANK["warn"] else action
        return action, f"취약점 심각도 {max_cve}."

    if verdict == "cooldown_hold":
        cd = result.get("cooldown") or {}
        action = {"MONITOR": "pass", "WARN": "warn", "ENFORCE": "block"}[mode]
        return action, (
            f"버전 발행 후 {cd.get('version_age_days')}일 — 기준 {cd.get('cooldown_days')}일"
            f"(등급 {cd.get('env_grade')}) 대기가 필요합니다(VCPS C1)."
        )

    if verdict == "checked_stale":
        action = {"MONITOR": "pass", "WARN": "warn", "ENFORCE": "warn"}[mode]
        return action, "위협 인텔 캐시가 낡았습니다 — `gvskb update-intel` 로 갱신하세요."

    if verdict in ("unknown", "error"):
        # 집행계약 §4-0: unknown 차단은 "사람이 직접 고른" 의존성(single·manifest)에만
        # 적용한다. 락파일·설치본에서 딸려온 전이 의존성까지 막으면 ENFORCE에 영원히
        # 도달할 수 없다(락파일 하나가 수백~수천 건). source_scope가 없으면(직접 단건
        # 조회) single과 동일하게 취급 — 그것도 사람이 직접 고른 것이기 때문이다.
        scope = result.get("source_scope") or "single"
        action = {"MONITOR": "pass", "WARN": "warn", "ENFORCE": "block"}[mode]
        if scope in ("lockfile", "installed") and action == "block":
            action = "warn"
        return action, "판정 불가 상태입니다 — '안전'을 의미하지 않습니다."

    if verdict == "registry_approved":
        if result.get("checked"):
            return "pass", "기관 레지스트리 승인 + 로컬 위협정보 대조 완료."
        action = {"MONITOR": "pass", "WARN": "warn", "ENFORCE": "warn"}[mode]
        return action, "기관 레지스트리 승인이지만 이번엔 로컬 위협정보 대조를 하지 못했습니다."

    if verdict == "checked_clean":
        return "pass", "이상 없음."

    # 알 수 없는 verdict(향후 gvskb가 새 값을 추가한 경우) — 안전 쪽으로 보수적으로.
    action = {"MONITOR": "pass", "WARN": "warn", "ENFORCE": "block"}[mode]
    return action, f"알 수 없는 판정값('{verdict}')입니다 — 보수적으로 처리합니다."


def _typosquat_row(result: dict, mode: Mode) -> tuple[Action, str] | None:
    warning = (result.get("heuristics") or {}).get("typosquat_warning")
    if not warning:
        return None
    action = {"MONITOR": "warn", "WARN": "warn", "ENFORCE": "block"}[mode]
    return action, warning


def _kev_unchecked_row(result: dict, mode: Mode) -> tuple[Action, str] | None:
    """kev_checked=False면 in_kev=False는 '악용 없음'이 아니라 '대조 못 함'이다.

    변경통지 2026-08-03 §2에서 정정된 필드다: 이전에는 cache_sources_used가
    비었는지로 추론했는데, 악성 피드만 있고 KEV 캐시가 없는 경우를 놓쳤다
    (그 상태에서는 목록이 비어있지 않은데 KEV 대조는 안 된 것). in_kev=True면
    이미 _absolute_block이 잡으므로 여기 안 옴 — kev_checked를 신경 쓸 필요가
    없다(실제 일치는 대조 상태와 무관하게 절대차단).
    """
    if result.get("in_kev") or result.get("kev_checked", False):
        return None
    action = {"MONITOR": "pass", "WARN": "warn", "ENFORCE": "block"}[mode]
    return action, "실제 공격 악용 여부(KEV)를 대조하지 못했습니다 — '악용 없음'이 아니라 '확인 못 함'입니다."


# ---------------------------------------------------------------------------
# 감사 기록 — gvskb 자체 감사로그(GVSKB_AUDIT_DIR opt-in)를 그대로 재사용한다.
# 개인 식별자는 절대 넣지 않는다(하네스_집행계약.md §7).
# ---------------------------------------------------------------------------


def _record_audit(results: list[dict], tool: str, scope: str = "single") -> None:
    try:
        from gvskb.audit import record_package_check
    except ImportError:
        return
    try:
        record_package_check(results, tool=tool, caller="harness:auto", scope=scope)
    except Exception:  # noqa: BLE001 — 감사 기록 실패가 게이트 판정을 막으면 안 된다
        pass


def _record_exception_usage(package: str, ecosystem: str, code: str, blocked_reason: str) -> None:
    """예외 코드 사용 이력 — 월별 건수 보고가 가능해야 한다(레지스트리팀 회신 21번 §7).

    gvskb의 감사로그와 같은 opt-in 규약(GVSKB_AUDIT_DIR)을 그대로 따른다. 개인
    식별자는 담지 않는다 — caller는 항상 'harness:auto'다.
    """
    audit_dir = os.environ.get("GVSKB_AUDIT_DIR", "").strip()
    if not audit_dir:
        return
    from datetime import datetime, timezone

    path = Path(audit_dir) / f"gate-exceptions-{datetime.now(timezone.utc):%Y%m}.jsonl"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "caller": "harness:auto",
                "package": f"pkg:{ecosystem}/{package}",
                "exception_code": code,
                "blocked_reason": blocked_reason,
            }, ensure_ascii=False) + "\n")
    except OSError as exc:
        print(f"[gvskb_gate] ⚠ 예외 사용 기록 실패: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# 판정 결과
# ---------------------------------------------------------------------------


@dataclass
class GateDecision:
    action: Action
    reasons: list[str] = field(default_factory=list)
    catalog_status: str | None = None
    mode: Mode = "MONITOR"
    env_grade: str = "E1"
    result: dict | None = None
    package: str = ""
    ecosystem: str = ""
    exception_eligible: bool = False   # 이 차단이 예외 코드로 우회 가능한 종류인가
    exception_applied: bool = False    # 실제로 우회됐는가
    # 시스템 문제(레지스트리 도달 실패 등) — 사용자에게 개별 차단처럼 보이면 안 된다.
    # 담당자 경로로만 전달한다(변경통지 2026-08-03 §1).
    admin_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "reasons": self.reasons,
            "catalog_status": self.catalog_status,
            "mode": self.mode,
            "env_grade": self.env_grade,
            "package": self.package,
            "ecosystem": self.ecosystem,
            "verdict": (self.result or {}).get("verdict"),
            "exception_applied": self.exception_applied,
            "admin_notes": self.admin_notes,
        }


def _next_steps(decision: GateDecision) -> list[str]:
    """차단·경고 시 "그럼 이제 뭐 하지"를 항상 함께 준다(하네스_집행계약.md §8-5)."""
    verdict = (decision.result or {}).get("verdict")
    steps: list[str] = []
    if decision.catalog_status == "denied":
        steps.append("org-packages.yaml의 approved 목록에서 대체 패키지를 먼저 찾아보세요.")
        steps.append("정말 필요하면 05_예외신청서로 예외를 신청하세요.")
    elif decision.catalog_status == "pending_review":
        steps.append("자동판정 검토 대기 중입니다 — 담당자 확정을 기다리거나 승인 상태를 문의하세요.")
    elif verdict == "not_found":
        steps.append("공식 저장소(pypi.org / npmjs.com)에서 정확한 패키지명을 확인하세요.")
        steps.append("AI가 이름을 지어냈을 가능성(슬롭스쿼팅)을 의심하세요.")
    elif verdict in ("malicious", "registry_rejected"):
        steps.append("이 패키지는 사용하지 마세요 — 대체 패키지를 org-packages.yaml에서 찾으세요.")
    elif verdict == "cooldown_hold":
        cd = (decision.result or {}).get("cooldown") or {}
        steps.append(f"기준 {cd.get('cooldown_days')}일이 지난 뒤 재시도하세요.")
        steps.append("보안 패치라 긴급히 필요하면 사유를 남기고 예외 승인을 요청하세요.")
    elif verdict in ("unknown", "error"):
        steps.append("네트워크 연결을 확인하거나 `gvskb update-intel` 실행 후 재시도하세요.")
    elif verdict == "vulnerable":
        steps.append("조치된(패치된) 상위 버전이 있는지 확인해 그 버전으로 지정하세요.")
    if not steps:
        steps.append("경고 내용을 확인한 뒤 필요하면 보안 담당자에게 문의하세요.")
    return steps


# ---------------------------------------------------------------------------
# 핵심 평가 함수
# ---------------------------------------------------------------------------


def _apply_exception(
    decision: GateDecision, exception_code: str | None, harness_root: Path,
) -> GateDecision:
    """차단 우회 — 사전 승인 코드가 있고, 그 차단이 우회 가능한 종류일 때만 적용한다.

    절대차단(§_absolute_block)과 카탈로그 denied/pending_review는 exception_eligible이
    애초에 False라 여기서 걸러도 소용없다 — 우회 판단은 evaluate_package가 그 종류를
    이미 알고 있을 때 미리 정해 둔다(레지스트리팀 회신 21번 §7 결정).
    """
    if decision.action != "block" or not exception_code:
        return decision
    if not decision.exception_eligible:
        decision.reasons.append(
            "이 차단은 예외 코드로 우회할 수 없습니다"
            + (" — 카탈로그 차단은 05_예외신청서 정식 절차만 가능합니다." if decision.catalog_status
               else " — 절대차단 판정(악성·기관차단·미존재·KEV)입니다.")
        )
        return decision
    codes = _load_exception_codes(harness_root)
    if exception_code not in codes:
        decision.reasons.append(
            f"'{exception_code}'는 등록되지 않은 예외 코드입니다. 사용 가능: {', '.join(sorted(codes)) or '(없음)'}"
        )
        return decision
    _record_exception_usage(decision.package, decision.ecosystem, exception_code, "; ".join(decision.reasons))
    decision.action = "warn"
    decision.exception_applied = True
    decision.reasons.append(f"예외 코드 '{exception_code}'({codes[exception_code]})로 진행합니다 — 이력이 기록됩니다.")
    return decision


def _synthetic_manifest(name: str, ecosystem: str, version: str | None) -> str:
    """단일 패키지를 audit_manifest가 읽는 매니페스트 텍스트로 감싼다.

    check_package_impl을 직접 쓰지 않는 이유: 그 함수는 gg-trusted-registry를
    조회하지 않는다 — 레지스트리 연동은 audit_manifest 안에만 있다(check_package.py
    확인). 그래서 예전 구현(check_package_impl 직접 호출)은 실시간 설치 게이트가
    기관 레지스트리 승인·차단을 전혀 못 보는 구조적 공백이었다. audit_manifest를
    1건짜리 매니페스트로 부르면 source_scope("manifest")·kev_checked·version_exact도
    다른 경로와 동일하게 붙는다.
    """
    if ecosystem == "npm":
        return json.dumps({"dependencies": {name: version or "*"}})
    return f"{name}=={version}" if version else name


_ADMIN_REGISTRY_NOTES = {
    "unreachable": "기관 레지스트리에 연결하지 못했습니다 — 기관 차단 목록이 이번 판정에 반영되지 않았습니다.",
    "unauthorized": "기관 레지스트리 인증에 실패했습니다(토큰 만료 가능) — GVSKB_REGISTRY_TOKEN을 확인하세요.",
    "rejected": "기관 레지스트리가 요청 형식을 거부했습니다 — 하네스·레지스트리 버전이 어긋났을 수 있습니다.",
}


async def evaluate_package(
    name: str,
    ecosystem: str = "pypi",
    version: str | None = None,
    mode: str | None = None,
    env_grade: str | None = None,
    harness_root: Path | None = None,
    exception_code: str | None = None,
) -> GateDecision:
    from gvskb.tools.check_package import audit_manifest

    root = harness_root or _default_harness_root()
    resolved_mode = _resolve_mode(mode, root)
    resolved_env = _resolve_env_grade(env_grade)

    catalog = _load_catalog(root)
    cat_status = _catalog_status(name, ecosystem, catalog)

    # 하네스_집행계약.md §6-3 우선순위 ①②: 차단 두 개를 허용보다 먼저 본다.
    # 카탈로그 차단은 exception_eligible=False — 정식 예외신청 절차(exception-policy.md)만.
    if cat_status == "denied":
        decision = GateDecision(
            action="block",
            reasons=[f"'{name}'은(는) 기관 카탈로그(org-packages.yaml)의 차단 목록에 있습니다."],
            catalog_status=cat_status, mode=resolved_mode, env_grade=resolved_env,
            package=name, ecosystem=ecosystem, exception_eligible=False,
        )
        return _apply_exception(decision, exception_code, root)
    if cat_status == "pending_review":
        decision = GateDecision(
            action="block",
            reasons=[f"'{name}'은(는) 자동판정 검토 대기(pending_review) 상태입니다 — 아직 승인이 아닙니다."],
            catalog_status=cat_status, mode=resolved_mode, env_grade=resolved_env,
            package=name, ecosystem=ecosystem, exception_eligible=False,
        )
        return _apply_exception(decision, exception_code, root)

    audit = await audit_manifest(
        _synthetic_manifest(name, ecosystem, version), ecosystem=ecosystem, env_grade=resolved_env,
    )
    checks = audit.get("checks") or []
    result = checks[0] if checks else {
        "name": name, "ecosystem": ecosystem, "version": version,
        "verdict": "error", "checked": False, "note": "패키지 판정을 생성하지 못했습니다.",
    }
    _record_audit([result], tool="harness_gate", scope="single")

    admin_notes: list[str] = []
    note = _ADMIN_REGISTRY_NOTES.get(str(audit.get("registry_status") or ""))
    if note:
        admin_notes.append(note)

    # 절대차단도 exception_eligible=False — 예외 코드로도 못 뚫는다(회신 21번 §7).
    abs_reason = _absolute_block(result)
    if abs_reason:
        decision = GateDecision(
            action="block", reasons=[abs_reason], catalog_status=cat_status,
            mode=resolved_mode, env_grade=resolved_env, result=result,
            package=name, ecosystem=ecosystem, exception_eligible=False, admin_notes=admin_notes,
        )
        return _apply_exception(decision, exception_code, root)

    action, reason = _verdict_row(result, resolved_mode)
    reasons = [reason]
    for row_fn in (_typosquat_row, _kev_unchecked_row):
        row = row_fn(result, resolved_mode)
        if row:
            row_action, row_reason = row
            if _MODE_RANK[row_action] > _MODE_RANK[action]:
                # 이 레이어가 최종 action을 만들었으니 표시용 1순위 사유가 된다 —
                # 안 그러면 "타이포스쿼트라 차단"인데 화면엔 "이상 없음"이 뜬다.
                action = row_action
                reasons.insert(0, row_reason)
            else:
                reasons.append(row_reason)

    # 여기 도달한 block은 모드표에서 나온 것(vulnerable/cooldown_hold/unknown/error/
    # typosquat/kev미확인 등)이라 우회 가능하다 — 절대차단·카탈로그차단이 아니기 때문.
    decision = GateDecision(
        action=action, reasons=reasons, catalog_status=cat_status,
        mode=resolved_mode, env_grade=resolved_env, result=result,
        package=name, ecosystem=ecosystem, exception_eligible=(action == "block"), admin_notes=admin_notes,
    )
    return _apply_exception(decision, exception_code, root)


@dataclass
class ManifestDecision:
    action: Action
    reasons: list[str] = field(default_factory=list)
    mode: Mode = "MONITOR"
    env_grade: str = "E1"
    audit: dict | None = None
    admin_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "reasons": self.reasons,
            "mode": self.mode,
            "env_grade": self.env_grade,
            "verdict": (self.audit or {}).get("verdict"),
            "parsed_count": (self.audit or {}).get("parsed_count"),
            "truncated_count": (self.audit or {}).get("truncated_count"),
            "admin_notes": self.admin_notes,
        }


async def evaluate_manifest(
    manifest_path: Path,
    ecosystem: str = "pypi",
    mode: str | None = None,
    env_grade: str | None = None,
    harness_root: Path | None = None,
) -> ManifestDecision:
    """requirements.txt·package.json·락파일 전체를 한 번에 평가한다(검증/배포 게이트용).

    개별 check와 같은 verdict 규칙을 재사용하되, 매니페스트 단위 신호
    (intel_cache.state·truncated_count·registry_status)도 함께 본다
    (하네스_집행계약.md §5).
    """
    from gvskb.tools.check_package import audit_manifest

    root = harness_root or _default_harness_root()
    resolved_mode = _resolve_mode(mode, root)
    resolved_env = _resolve_env_grade(env_grade)

    text = manifest_path.read_text(encoding="utf-8-sig")
    audit = await audit_manifest(text, ecosystem=ecosystem, env_grade=resolved_env, filename=manifest_path.name)
    _record_audit(audit.get("checks") or [], tool="harness_gate_manifest", scope="manifest")

    action: Action = "pass"
    reasons: list[str] = []
    admin_notes: list[str] = []

    def escalate(a: Action, why: str) -> None:
        nonlocal action
        if _MODE_RANK[a] > _MODE_RANK[action]:
            action = a
        reasons.append(why)

    ic = audit.get("intel_cache") or {}
    if ic.get("state") == "missing":
        # 로컬 대조 자체를 한 번도 못 한 상태 — ENFORCE에서는 설치를 통째로 막는다
        # (하네스_집행계약.md §5-1: 이 상태에서 통과시키면 캐시 0·검증 0인 채로 승인된다).
        escalate("block" if resolved_mode == "ENFORCE" else "warn",
                  "로컬 위협정보 캐시가 없어 대조 자체를 못 했습니다 — `gvskb update-intel` 이 필요합니다.")
    elif ic.get("state") == "stale":
        escalate("warn", "로컬 위협정보 캐시가 낡았습니다 — 갱신을 권장합니다.")

    truncated = audit.get("truncated_count") or 0
    if truncated > 0:
        escalate("block" if resolved_mode == "ENFORCE" else "warn",
                  f"{truncated}개 패키지가 검사 범위(limit) 밖이라 검사되지 않았습니다 — '전부 통과'가 아닙니다.")

    # 레지스트리 도달 문제는 개별 패키지의 문제가 아니라 시스템 문제다 — 조치 단위가
    # 다르므로(레지스트리 복구 1건) action에 반영하지 않고 담당자 채널로만 보낸다
    # (변경통지 2026-08-03 §1, gvskb registry_client.annotate_status와 동일 원칙).
    note = _ADMIN_REGISTRY_NOTES.get(str(audit.get("registry_status") or ""))
    if note:
        admin_notes.append(note)

    for c in audit.get("checks") or []:
        abs_reason = _absolute_block(c)
        if abs_reason:
            escalate("block", f"{c.get('name')}: {abs_reason}")
            continue
        a, why = _verdict_row(c, resolved_mode)
        for row_fn in (_typosquat_row, _kev_unchecked_row):
            row = row_fn(c, resolved_mode)
            if row and _MODE_RANK[row[0]] > _MODE_RANK[a]:
                a, why = row  # 이 레이어가 최종 action을 만들었으니 사유도 이걸로 바꾼다
        if a != "pass":
            escalate(a, f"{c.get('name')}: {why}")

    if not reasons:
        reasons.append("전체 매니페스트에서 이상 없음.")

    return ManifestDecision(
        action=action, reasons=reasons, mode=resolved_mode, env_grade=resolved_env, audit=audit,
        admin_notes=admin_notes,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _print_decision(decision: GateDecision, *, json_mode: bool) -> None:
    """통과는 침묵, 차단·경고는 한 줄만 낸다(변경통지 2026-08-03 §1).

    판정 근거·필드명·캐시 상태를 사용자 화면에 늘어놓지 않는다 — 그게 필요한
    사람은 --json으로 본다. 시스템 문제(admin_notes)는 stderr의 별도 접두사로만
    나가 사용자 판단거리로 섞이지 않는다.
    """
    for note in decision.admin_notes:
        print(f"[gvskb_gate][관리자용] {note}", file=sys.stderr)
    if json_mode:
        sys.stdout.write(json.dumps(decision.to_dict(), ensure_ascii=False, indent=2) + "\n")
        return
    if decision.action == "pass":
        return
    label = "[경고]" if decision.action == "warn" else "[차단]"
    reason = decision.reasons[0] if decision.reasons else ""
    steps = _next_steps(decision)
    line = f"{label} {decision.ecosystem}:{decision.package} — {reason}"
    if steps:
        line += f" → {steps[0]}"
    print(line)


def _cli_check(args: argparse.Namespace) -> int:
    decision = asyncio.run(evaluate_package(
        args.name, args.ecosystem, version=args.version, mode=args.mode, env_grade=args.env,
        exception_code=args.exception_code,
    ))
    _print_decision(decision, json_mode=args.json)
    return {"pass": EXIT_PASS, "warn": EXIT_WARN, "block": EXIT_BLOCK}[decision.action]


def _cli_install(args: argparse.Namespace) -> int:
    decision = asyncio.run(evaluate_package(
        args.name, args.ecosystem, version=args.version, mode=args.mode, env_grade=args.env,
        exception_code=args.exception_code,
    ))
    _print_decision(decision, json_mode=False)

    if decision.action == "block":
        print("[gvskb_gate] 설치를 진행하지 않았습니다.", file=sys.stderr)
        return EXIT_BLOCK

    if args.ecosystem != "pypi":
        print(
            "[gvskb_gate] ecosystem=npm 설치는 gvskb_gate.js install 을 쓰세요 "
            "(이 명령은 pip 전용입니다).",
            file=sys.stderr,
        )
        return EXIT_USAGE

    spec = args.name if not args.version else f"{args.name}=={args.version}"
    pip_cmd = [sys.executable, "-m", "pip", "install"]
    if args.wheel_only:
        # C2(설치 스크립트 차단)의 pip측 대응 — sdist/setup.py 실행을 원천 차단한다.
        # 기본 off인 이유: 일부 정당한 패키지가 wheel을 못 구할 수 있어 강제하지 않는다.
        pip_cmd.append("--only-binary=:all:")
    pip_cmd.append(spec)
    print(f"[gvskb_gate] 설치 진행: {' '.join(pip_cmd)}", file=sys.stderr)
    proc = subprocess.run(pip_cmd)
    return proc.returncode


def _cli_verify_manifest(args: argparse.Namespace) -> int:
    path = Path(args.manifest)
    if not path.exists():
        print(f"[gvskb_gate] 파일을 찾을 수 없습니다: {path}", file=sys.stderr)
        return EXIT_USAGE
    decision = asyncio.run(evaluate_manifest(path, args.ecosystem, mode=args.mode, env_grade=args.env))
    for note in decision.admin_notes:
        print(f"[gvskb_gate][관리자용] {note}", file=sys.stderr)
    # verify-manifest는 security-reviewer(사람 보안담당)가 배포 전에 돌리는 감사용
    # 명령이다 — check/install과 달리 여기서는 세부 사유를 그대로 보여주는 게 맞다.
    if args.json:
        sys.stdout.write(json.dumps(decision.to_dict(), ensure_ascii=False, indent=2) + "\n")
    else:
        label = {"pass": "[통과]", "warn": "[경고]", "block": "[차단]"}[decision.action]
        print(f"{label} {path} (모드={decision.mode}, 등급={decision.env_grade})")
        for r in decision.reasons:
            print(f"  - {r}")
    return {"pass": EXIT_PASS, "warn": EXIT_WARN, "block": EXIT_BLOCK}[decision.action]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gvskb_gate",
        description="하네스 집행 게이트 — gvskb 판정을 실제 설치 허용/차단으로 집행한다.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    def _add_common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--ecosystem", choices=["pypi", "npm"], default="pypi")
        sp.add_argument("--version", default=None, help="검사할 버전(권장)")
        sp.add_argument("--mode", choices=list(_VALID_MODES), default=None,
                         help="미지정 시 GVSKB_GATE_MODE → org-environment.yaml enforcement.mode → MONITOR 순")
        sp.add_argument("--env", choices=["E0", "E1", "E2"], default=None,
                         help="미지정 시 GVSKB_GATE_ENV_GRADE → CI 신호 감지(E2) → 기본 E1")
        sp.add_argument("--exception-code", default=None,
                         help="사전 승인된 예외 코드(org-environment.yaml enforcement.exception_codes). "
                              "절대차단·카탈로그차단은 이 코드로도 우회되지 않는다")
        sp.add_argument("--json", action="store_true")

    check = sub.add_parser("check", help="패키지 1건을 확인만 한다(설치 안 함)")
    check.add_argument("name")
    _add_common(check)
    check.set_defaults(func=_cli_check)

    install = sub.add_parser("install", help="확인 후 통과하면 실제로 pip install 한다(pypi 전용)")
    install.add_argument("name")
    install.add_argument("--wheel-only", action="store_true",
                          help="sdist/setup.py 실행을 막고 wheel 설치만 허용(C2 강화, 기본 off)")
    _add_common(install)
    install.set_defaults(func=_cli_install)

    verify = sub.add_parser("verify-manifest", help="requirements.txt/package.json/락파일 전체 검증")
    verify.add_argument("manifest")
    _add_common(verify)
    verify.set_defaults(func=_cli_verify_manifest)

    return p


def _force_utf8_streams() -> None:
    """Windows cp949 콘솔에서도 한글·em-dash가 깨지거나 죽지 않게 한다(gvskb cli.py와 동일 처리)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass


def main(argv: list[str] | None = None) -> int:
    _force_utf8_streams()
    try:
        import gvskb  # noqa: F401
    except ImportError:
        # 여기서 자동 설치하지 않는다 — 이 게이트를 부르는 쪽(메인 루프)이 사용자
        # 동의를 받고 나서 설치 명령을 실행하는 게 원칙이다(CLAUDE.md 참고).
        # 이 스크립트는 "무엇을 실행해야 하는지"만 정확히 알려준다.
        print(
            "[gvskb_gate] gvskb(vibecode-checker)가 설치되어 있지 않습니다.\n"
            "  설치 명령: pip install git+https://github.com/Lex6won/vibecode-checker.git\n"
            "  이 메시지를 본 에이전트는 사용자에게 설치 여부를 먼저 확인해야 합니다"
            "(자동 설치 금지).",
            file=sys.stderr,
        )
        return EXIT_NOT_INSTALLED
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
