#!/bin/sh
# Sauvegarde PostgreSQL — usage : ./scripts/backup_db.sh [dossier_sortie]
# Planifier via cron : 0 2 * * * /chemin/scripts/backup_db.sh /var/backups/gestion-scolaire
set -e

OUTPUT_DIR="${1:-./backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="gestion_scolaire_${TIMESTAMP}.sql.gz"

DB_HOST="${PGHOST:-localhost}"
DB_PORT="${PGPORT:-5432}"
DB_USER="${PGUSER:-gestion}"
DB_NAME="${PGDATABASE:-gestion_scolaire}"
export PGPASSWORD="${PGPASSWORD:-gestion_dev}"

mkdir -p "$OUTPUT_DIR"

echo "Sauvegarde de ${DB_NAME} vers ${OUTPUT_DIR}/${FILENAME}..."
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
  --clean --if-exists --no-owner --no-acl | gzip > "${OUTPUT_DIR}/${FILENAME}"

echo "Rotation : suppression des sauvegardes > ${RETENTION_DAYS} jours..."
find "$OUTPUT_DIR" -name 'gestion_scolaire_*.sql.gz' -mtime +"${RETENTION_DAYS}" -delete

echo "Terminé : ${OUTPUT_DIR}/${FILENAME}"
