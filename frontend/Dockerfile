# CivicPulse frontend — multi-stage build.
# Stage 1 builds the SPA; stage 2 serves it with nginx only (no node, no source).

FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY tsconfig.json vite.config.ts index.html ./
COPY src ./src
RUN npm run build

FROM nginx:1.30.5-alpine3.24

# Security: apply all available package fixes for this Alpine branch so the
# Trivy gate (HIGH/CRITICAL with a fix available) passes. Base is pinned by
# version + Alpine release, never :latest.
RUN apk upgrade --no-cache

# Non-root compatible main config: pid + temp under /tmp, logs to stdout/stderr.
RUN sed -i \
      -e 's|/run/nginx.pid|/tmp/nginx.pid|' \
      -e 's|/var/run/nginx.pid|/tmp/nginx.pid|' \
      -e 's|/var/log/nginx/error.log|/dev/stderr|g' \
      -e 's|/var/log/nginx/access.log|/dev/stdout|g' \
      -e 's|/var/cache/nginx|/tmp/nginx-cache|g' \
      -e '/^user /d' \
      /etc/nginx/nginx.conf \
 && mkdir -p /tmp/nginx-cache \
 && chown nginx:nginx /tmp/nginx-cache \
 && rm -f /etc/nginx/conf.d/default.conf

# Site config goes through the templates/ + envsubst pattern so BACKEND_URL is
# overridable at runtime (default below keeps a single-config Docker/K8s deploy working).
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
RUN chown -R nginx:nginx /etc/nginx/conf.d /etc/nginx/templates

ENV BACKEND_URL=backend:8000

EXPOSE 8080
USER nginx

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1:8080/healthz || exit 1
