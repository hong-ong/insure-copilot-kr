# AI 백엔드 컨테이너 — Hugging Face Spaces(Docker, 무료 CPU) 배포용. 포트 7860은 Spaces 기본값.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /usr/local/bin/uv

# Spaces는 uid 1000 사용자로 실행한다
RUN useradd -m -u 1000 app
WORKDIR /home/app/code

COPY --chown=app pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY --chown=app src ./src
COPY --chown=app data/samples ./data/samples
RUN uv sync --frozen --no-dev && mkdir -p data/processed && chown -R app data

USER app
ENV PATH="/home/app/code/.venv/bin:$PATH" MART_PATH=/home/app/code/data/processed/mart.duckdb
# 가상 데이터 마트는 이미지 빌드 시 미리 만들어 둔다 (시드 고정이라 항상 같은 숫자)
RUN python -m insure_copilot.genbi.mart

EXPOSE 7860
CMD ["uvicorn", "insure_copilot.api.main:app", "--host", "0.0.0.0", "--port", "7860"]
