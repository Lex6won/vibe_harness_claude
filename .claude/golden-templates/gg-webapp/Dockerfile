# 표준 베이스만 (내부 Harbor). 공개 베이스 금지.
FROM gg-python-web:3.12
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"
# 비root는 베이스 제공. 로그 stdout.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
