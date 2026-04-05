#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_HOST:?DATABASE_HOST is required}"
: "${DATABASE_PORT:?DATABASE_PORT is required}"
: "${DATABASE_NAME:?DATABASE_NAME is required}"
: "${DATABASE_USER:?DATABASE_USER is required}"
: "${DATABASE_PASSWORD:?DATABASE_PASSWORD is required}"
: "${SPACES_KEY:?SPACES_KEY is required}"
: "${SPACES_SECRET:?SPACES_SECRET is required}"
: "${SPACES_BUCKET:?SPACES_BUCKET is required}"
: "${SPACES_REGION:?SPACES_REGION is required}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="/tmp/backup_${TIMESTAMP}.sql.gz"

PGPASSWORD="$DATABASE_PASSWORD" pg_dump \
  --host="$DATABASE_HOST" \
  --port="$DATABASE_PORT" \
  --username="$DATABASE_USER" \
  --dbname="$DATABASE_NAME" \
  --no-password \
  --format=plain \
  --no-owner \
  --no-acl \
  | gzip > "$BACKUP_FILE"

s3cmd \
  --access_key="$SPACES_KEY" \
  --secret_key="$SPACES_SECRET" \
  --host="${SPACES_REGION}.digitaloceanspaces.com" \
  --host-bucket="%(bucket)s.${SPACES_REGION}.digitaloceanspaces.com" \
  put "$BACKUP_FILE" "s3://${SPACES_BUCKET}/postgres/${TIMESTAMP}.sql.gz"

rm -f "$BACKUP_FILE"

s3cmd \
  --access_key="$SPACES_KEY" \
  --secret_key="$SPACES_SECRET" \
  --host="${SPACES_REGION}.digitaloceanspaces.com" \
  --host-bucket="%(bucket)s.${SPACES_REGION}.digitaloceanspaces.com" \
  ls "s3://${SPACES_BUCKET}/postgres/" \
  | sort \
  | head -n -30 \
  | awk '{print $4}' \
  | xargs -r -I{} s3cmd \
      --access_key="$SPACES_KEY" \
      --secret_key="$SPACES_SECRET" \
      --host="${SPACES_REGION}.digitaloceanspaces.com" \
      --host-bucket="%(bucket)s.${SPACES_REGION}.digitaloceanspaces.com" \
      del {}

echo "Backup complete: ${TIMESTAMP}.sql.gz"
