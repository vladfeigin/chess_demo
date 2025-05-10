# mcp_sse/white/Dockerfile
FROM python:3.12-slim-bookworm

# install the uv wrapper
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy project manifest for dependency installation
COPY pyproject.toml uv.lock ./

# Install all Python deps via uv (caches in /root/.cache/uv)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

# (No need for a second uv sync)

# Copy your agent script
COPY mcp_sse/white/white_agent.py ./white_agent.py

EXPOSE 8001
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen
# Serve the FastMCP SSE app named "mcp" in white_agent.py
CMD ["uv", "run", "white_agent.py", "--host", "0.0.0.0", "--port", "8001"]