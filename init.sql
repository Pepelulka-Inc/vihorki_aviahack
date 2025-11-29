-- PostgreSQL initialization script
-- This script runs once when the database container starts

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- The database and user are created automatically by POSTGRES_DB and POSTGRES_USER environment variables
-- This file can contain additional initialization SQL if needed

-- Grant permissions for the user
GRANT ALL PRIVILEGES ON DATABASE "habrdb" TO "habrpguser";
GRANT USAGE ON SCHEMA public TO "habrpguser";
GRANT CREATE ON SCHEMA public TO "habrpguser";
ALTER SCHEMA public OWNER TO "habrpguser";