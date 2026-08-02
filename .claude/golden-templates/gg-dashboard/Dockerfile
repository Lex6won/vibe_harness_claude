# 표준 베이스만 (기관 내부 레지스트리). 공개 베이스 금지.
# 구현 시 아래 플레이스홀더를 org-environment.yaml container.base_images.python_web 값으로 치환한다.
FROM {ORG_BASE_IMAGE_PYTHON_WEB}
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health').status==200 else 1)"
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
