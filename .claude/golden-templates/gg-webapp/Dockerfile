# 표준 베이스만 (기관 내부 레지스트리). 공개 베이스 금지.
# 구현 시 아래 플레이스홀더를 org-environment.yaml container.base_images.python_web 값으로 치환한다.
FROM {ORG_BASE_IMAGE_PYTHON_WEB}
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"
# 비root는 베이스 제공. 로그 stdout.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
