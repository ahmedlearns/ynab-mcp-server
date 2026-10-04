# The read-only YNAB MCP server over HTTP, behind GitHub sign-in.
# See compose.yaml and .env.example.
FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.29 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependencies first, pinned by uv.lock, so code changes don't reinstall them
COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --locked --no-dev --no-install-project

COPY src ./src
RUN uv sync --locked --no-dev

# fastmcp keeps OAuth client registrations and tokens (encrypted) under
# FASTMCP_HOME, so a volume there keeps Claude signed in across restarts.
RUN useradd --uid 1000 --create-home app && mkdir /data && chown app /data
ENV PATH=/app/.venv/bin:$PATH \
    FASTMCP_HOME=/data
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"]
CMD ["ynab-mcp-http"]
