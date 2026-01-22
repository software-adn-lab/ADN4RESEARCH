#!/bin/sh
set -e

APP_USER="app"
APP_GROUP="app"

PAPERS_DIR="${PAPERS_STORAGE_DIR:-media/papers}"
if [ "${PAPERS_DIR#/}" = "$PAPERS_DIR" ]; then
  PAPERS_DIR="/app/${PAPERS_DIR}"
fi

if [ "$(id -u)" = "0" ]; then
  mkdir -p /app/media /app/staticfiles "$PAPERS_DIR"
  chown -R "$APP_USER:$APP_GROUP" /app/media /app/staticfiles "$PAPERS_DIR"
fi

if [ -n "${DB_HOST:-}" ]; then
  echo "Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT:-5432}..."
  until pg_isready -h "$DB_HOST" -p "${DB_PORT:-5432}" -U "${DB_USER:-postgres}" >/dev/null 2>&1; do
    sleep 1
  done
fi

run_as_app() {
  if [ "$(id -u)" = "0" ]; then
    gosu "$APP_USER:$APP_GROUP" "$@"
  else
    "$@"
  fi
}

if [ "${DJANGO_MIGRATE:-1}" = "1" ]; then
  run_as_app python manage.py migrate --noinput
fi

if [ "${DJANGO_COLLECTSTATIC:-0}" = "1" ]; then
  run_as_app python manage.py collectstatic --noinput
fi

if [ "$(id -u)" = "0" ]; then
  exec gosu "$APP_USER:$APP_GROUP" "$@"
fi

exec "$@"
