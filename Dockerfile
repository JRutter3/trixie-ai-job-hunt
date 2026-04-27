# Dockerfile for the trixie-ai-job-hunt

# Start with the python-slim environment:
FROM python:3.13-slim

# Copy uv binarieas from their distro
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1
ENV PATH="/app/.venv/bin:${PATH}"
ENV PYTHONPATH="/app/src"

# Copy our sourcecode over.
COPY ./src /app/src
COPY ./pyproject.toml /app/pyproject.toml
COPY ./uv.lock /app/uv.lock
# NOTE - there might be some config also, but we will handle that later.
COPY ./cfg /app/cfg

ENV sys_prompt_path="/app/cfg/recruiter_prompt.txt"

WORKDIR /app
RUN uv sync --frozen --no-dev
CMD ["uv", "run", "--no-dev", "python", "/app/src/main.py"]