#!/bin/bash
# Fix Supabase role passwords — runs as a one-shot container after DB is healthy
set -e

PGPASSWORD="${POSTGRES_PASSWORD:-postgres}"
export PGPASSWORD

echo "Waiting for database to be ready..."
until psql -h "$DB_HOST" -U supabase_admin -d postgres -c "SELECT 1" > /dev/null 2>&1; do
  sleep 1
done

echo "Setting role passwords..."
psql -h "$DB_HOST" -U supabase_admin -d postgres <<-EOSQL
  ALTER ROLE supabase_auth_admin WITH PASSWORD '${POSTGRES_PASSWORD:-postgres}';
  ALTER ROLE supabase_storage_admin WITH PASSWORD '${POSTGRES_PASSWORD:-postgres}';
  ALTER ROLE authenticator WITH PASSWORD '${POSTGRES_PASSWORD:-postgres}';
EOSQL

echo "Role passwords set successfully."
