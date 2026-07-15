# gg-dashboard (Track S · 내부 대시보드)

Streamlit 내부 현황·분석 대시보드. **내부 한정** — 시민(외부망)엔 Track S 금지(gg-webapp/gg-spa로).

## 내장 레일
런타임 3.12/PG16 · `/_stcore/health`(nginx가 `/health` 매핑) · **nginx 앞단 Keycloak 접근제어 + 보안헤더** ·
비밀값 `.env`만 · 파라미터 바인딩 · 외부 CDN 금지 · 실개인정보 금지(더미) · 승인 패키지만.

## 실행 (L1)
```
cp .env.example .env
pip install -r requirements.txt
streamlit run app.py
```
배포 시 `nginx.conf`(헤더+Keycloak)를 앞단에 둔다 — Streamlit 자체엔 인증·헤더 없음.
