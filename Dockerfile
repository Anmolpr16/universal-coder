FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CODER_SANDBOX_MODE=trusted

RUN useradd --create-home --uid 10001 coder
WORKDIR /app
COPY pyproject.toml README.md SECURITY.md CHANGELOG.md ./
COPY src ./src
RUN python -m pip install --no-cache-dir --no-build-isolation .
RUN mkdir -p /workspace /data && chown -R coder:coder /workspace /data /app
USER coder
WORKDIR /workspace
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python - <<'PY'
import urllib.request
urllib.request.urlopen('http://127.0.0.1:8765/health', timeout=3)
PY
ENTRYPOINT ["coder"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8765"]
