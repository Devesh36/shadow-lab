FROM node:22-bookworm-slim AS build
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*
RUN --mount=type=secret,id=custom-ca,required=false if [ -f /run/secrets/custom-ca ]; then cp /run/secrets/custom-ca /usr/local/share/ca-certificates/custom-ca.crt && update-ca-certificates; fi
WORKDIR /demo
COPY examples/vulnerable-nextjs/package*.json ./
RUN NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt npm ci --no-audit --no-fund
COPY examples/vulnerable-nextjs/ ./
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build -- --webpack
FROM node:22-bookworm-slim
WORKDIR /demo
COPY --from=build --chown=node:node /demo/.next/standalone ./
COPY --from=build --chown=node:node /demo/.next/static ./.next/static
USER node
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
ENV HOSTNAME=0.0.0.0 PORT=3001
CMD ["node", "server.js"]
