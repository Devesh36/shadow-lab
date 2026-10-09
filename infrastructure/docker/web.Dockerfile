FROM node:22-bookworm-slim AS build
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /web
COPY apps/web/package*.json ./
RUN --mount=type=secret,id=custom-ca,required=false \
    if [ -f /run/secrets/custom-ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/custom-ca; fi; \
    npm ci --strict-ssl=true --no-audit --no-fund
COPY apps/web/ ./
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build -- --webpack
FROM node:22-bookworm-slim
WORKDIR /web
COPY --from=build --chown=node:node /web/.next/standalone ./
COPY --from=build --chown=node:node /web/.next/static ./.next/static
USER node
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
ENV HOSTNAME=0.0.0.0 PORT=3000
CMD ["node", "server.js"]
