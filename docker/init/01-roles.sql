-- Set passwords for Supabase internal roles
-- The supabase/postgres image creates these roles but with random passwords
-- GoTrue, PostgREST, and Storage need known passwords to connect

DO $$
BEGIN
  -- supabase_admin is the superuser, connect via it
  EXECUTE format('ALTER ROLE supabase_auth_admin WITH PASSWORD %L', current_setting('app.settings.jwt_secret', true));
  EXECUTE format('ALTER ROLE supabase_storage_admin WITH PASSWORD %L', current_setting('app.settings.jwt_secret', true));
  EXECUTE format('ALTER ROLE authenticator WITH PASSWORD %L', current_setting('app.settings.jwt_secret', true));
EXCEPTION WHEN OTHERS THEN
  -- Fallback: set to 'postgres' directly
  ALTER ROLE supabase_auth_admin WITH PASSWORD 'postgres';
  ALTER ROLE supabase_storage_admin WITH PASSWORD 'postgres';
  ALTER ROLE authenticator WITH PASSWORD 'postgres';
END
$$;
