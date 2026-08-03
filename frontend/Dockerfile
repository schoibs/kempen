FROM node:22.16.0-bookworm-slim AS base

WORKDIR /app

ENV NEXT_TELEMETRY_DISABLED=1

FROM base AS dependencies

COPY package.json package-lock.json ./
RUN npm ci

FROM base AS build

COPY --from=dependencies /app/node_modules ./node_modules
COPY . .

ARG API_INTERNAL_URL=http://127.0.0.1:8000
ARG NEXT_PUBLIC_DEPLOYMENT_LABEL

ENV API_INTERNAL_URL=${API_INTERNAL_URL}
ENV NEXT_PUBLIC_DEPLOYMENT_LABEL=${NEXT_PUBLIC_DEPLOYMENT_LABEL}

RUN npm run build

FROM node:22.16.0-bookworm-slim AS runtime

WORKDIR /app

ENV HOSTNAME=0.0.0.0
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000

COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static

USER node

EXPOSE 3000

CMD ["node", "server.js"]
