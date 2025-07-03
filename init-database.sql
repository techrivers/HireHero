-- Database initialization script
-- This creates the database if it doesn't exist

-- Create the database
SELECT 'CREATE DATABASE cvmatcher_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'cvmatcher_db');

-- Create user if doesn't exist  
DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE  rolname = 'cvmatcher') THEN

      CREATE ROLE cvmatcher LOGIN PASSWORD 'securepassword';
   END IF;
END
$do$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE cvmatcher_db TO cvmatcher;