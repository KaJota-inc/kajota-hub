# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir hatchling \
    && pip install --no-cache-dir \
        "fastapi>=0.118.0" \
        "uvicorn[standard]>=0.30.0" \
        "web3>=7.4.0" \
        "pydantic>=2.9.0" \
        "pydantic-settings>=2.4.0"

COPY kajota_mesh_skill ./kajota_mesh_skill
COPY abis ./abis

ENV PORT=8081
EXPOSE 8081

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:${PORT}/healthz || exit 1

CMD ["python", "-m", "kajota_mesh_skill.main"]
