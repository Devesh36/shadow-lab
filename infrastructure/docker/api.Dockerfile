FROM node:22-bookworm-slim AS node
FROM python:3.12-slim-bookworm
WORKDIR /app
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
COPY --chown=10001:10001 . .
# Keep the large runtime/dependencies in one layer: vfs otherwise copies gigabytes per step.
# The optional managed-cloud public CA preserves verification for package downloads.
RUN --mount=type=secret,id=custom-ca,required=false \
    apt-get update && apt-get install -y --no-install-recommends git libstdc++6 chromium && \
    rm -rf /var/lib/apt/lists/* && \
    if [ -f /run/secrets/custom-ca ]; then cp /run/secrets/custom-ca /usr/local/share/ca-certificates/custom-ca.crt && update-ca-certificates; fi && \
    ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm && \
    pip install --no-cache-dir uv==0.12.19 && UV_SYSTEM_CERTS=true uv sync --locked --no-dev --no-cache && \
    NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt npm --prefix examples/vulnerable-nextjs ci --no-audit --no-fund --cache /tmp/npm-cache && \
    rm -rf /tmp/npm-cache && \
    useradd --uid 10001 --create-home shadowlab && mkdir /data && chown shadowlab:shadowlab /data
USER shadowlab
ENV SHADOWLAB_DATA_DIR=/data SHADOWLAB_REPOSITORY_ROOT=/app SHADOWLAB_LLM_API_KEY="" NEXT_TELEMETRY_DISABLED=1 PATH="/app/.venv/bin:$PATH"
CMD ["sh", "-c", "alembic upgrade head && uvicorn apps.api.main:app --host 0.0.0.0 --port 8000"]
