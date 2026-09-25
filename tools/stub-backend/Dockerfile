# Stub backend — infra bring-up only. Never shipped.
FROM python:3.12-slim
WORKDIR /app
COPY app.py .
RUN useradd -r -u 10001 stub && chown -R stub /app
USER stub
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status==200 else 1)"
CMD ["python", "app.py"]
