#!/bin/bash
# Inicializa la base de datos de SAAC: aplica las migraciones y semillas y crea los
# usuarios de conexión de la aplicación. La imagen oficial de PostgreSQL lo ejecuta
# automáticamente la primera vez que se crea el volumen (docker-entrypoint-initdb.d).
set -euo pipefail

DIR_MIGRACIONES="${SAAC_DIR_MIGRACIONES:-/migraciones}"
DIR_SEMILLAS="${SAAC_DIR_SEMILLAS:-/semillas}"
PSQL=(psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB")

for archivo in "$DIR_MIGRACIONES"/*.sql "$DIR_SEMILLAS"/*.sql; do
    echo "SAAC: aplicando $(basename "$archivo")"
    "${PSQL[@]}" -q -f "$archivo"
done

# Las contraseñas se pasan como variables de psql (:'variable' las cita de forma segura)
"${PSQL[@]}" -v clave_academico="$SAAC_BD_CLAVE_ACADEMICO" -v clave_nucleo="$SAAC_BD_CLAVE_NUCLEO" <<'EOSQL'
CREATE USER saac_app_academico WITH PASSWORD :'clave_academico' IN ROLE rol_academico;
CREATE USER saac_app_nucleo    WITH PASSWORD :'clave_nucleo'    IN ROLE rol_nucleo;
EOSQL

echo "SAAC: base de datos inicializada."
