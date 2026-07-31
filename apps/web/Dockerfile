FROM node:22.22.0-alpine AS dependencies
RUN corepack enable && corepack prepare pnpm@11.9.0 --activate
WORKDIR /app
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY apps/web/package.json apps/web/package.json
RUN pnpm install --frozen-lockfile

FROM dependencies AS builder
COPY apps/web apps/web
RUN pnpm --filter @agentlens/web build

FROM node:22.22.0-alpine AS runtime
ENV NODE_ENV=production
WORKDIR /app
RUN addgroup -S agentlens && adduser -S agentlens -G agentlens
COPY --from=builder --chown=agentlens:agentlens /app/apps/web/.next/standalone ./
COPY --from=builder --chown=agentlens:agentlens /app/apps/web/.next/static ./apps/web/.next/static
USER agentlens
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
