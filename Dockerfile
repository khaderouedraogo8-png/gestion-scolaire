# Image unique Railway : frontend (Nginx) + API (Gunicorn) — même origine /api
# Build context = racine du dépôt

FROM node:20-alpine AS frontend-build

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
ENV VITE_API_URL=/api
RUN npm run build

FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    curl \
    gettext-base \
    postgresql-client \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 \
    libffi-dev shared-mime-info libcairo2 \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/nginx/sites-enabled/default

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY database/schema_v2_mono_etablissement.sql /app/database/schema_v2_mono_etablissement.sql
COPY --from=frontend-build /app/dist /usr/share/nginx/html
COPY deploy/nginx.railway.conf.template /etc/nginx/templates/default.conf.template
COPY deploy/railway-entrypoint.sh /railway-entrypoint.sh

RUN chmod +x /railway-entrypoint.sh \
    && mkdir -p /app/uploads /var/log/nginx /var/cache/nginx /run/nginx \
    && chown -R www-data:www-data /var/log/nginx /var/cache/nginx /run/nginx || true

ENV FLASK_APP=run.py \
    FLASK_ENV=production \
    PORT=8080 \
    GUNICORN_WORKERS=2 \
    GUNICORN_TIMEOUT=120 \
    RUN_SEED=true \
    UPLOAD_FOLDER=/app/uploads

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --retries=5 --start-period=90s \
  CMD curl -f http://127.0.0.1:8080/api/health || exit 1

CMD ["/railway-entrypoint.sh"]
