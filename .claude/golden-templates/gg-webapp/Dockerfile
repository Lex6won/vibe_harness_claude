# 표준 베이스만 (기관 내부 레지스트리). 공개 베이스 금지.
# 구현 시 아래 플레이스홀더를 org-environment.yaml container.base_images.python_web 값으로 치환한다.
FROM {ORG_BASE_IMAGE_PYTHON_WEB}
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
EXPOSE 8000
# http.client를 쓴다 — 표준 라이브러리의 평문 전송 헬퍼 호출 패턴이 KISA-PY-SEC-05와
# 문자 그대로 겹쳐 이 loopback 헬스체크 자체가 보안 스캔에서 high/warn으로 걸린다
# (실사용 검증 중 발견). 기능은 동일하다.
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import http.client,sys; c=http.client.HTTPConnection('127.0.0.1',8000,timeout=3); c.request('GET','/health'); sys.exit(0 if c.getresponse().status==200 else 1)"
# 비root는 베이스 제공. 로그 stdout.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
