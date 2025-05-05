# Database Authentication System

## Overview

This document describes the database integration for the authentication system. The system now uses SQLAlchemy to store user data and authentication tokens in a relational database, which enhances security, reliability and scalability.

## Features

- **Database Backend**: All user authentication data is now stored in a persistent database
- **Multiple DB Support**: Compatible with both SQLite (development/testing) and MySQL (production)
- **Migration System**: Alembic-based migration framework for database schema changes
- **CLI Tools**: Command-line interface for database operations
- **Role-Based Access Control**: User roles stored in database for fine-grained permissions
- **Token Management**: Secure JWT token handling with refresh token rotation
- **Multi-Factor Authentication**: Support for MFA using time-based one-time passwords

## Configuration

Database settings are configured through environment variables or the `.env` file. The following settings can be configured:

- `DB_TYPE`: Database type (`sqlite` or `mysql`)
- `DB_PATH`: Path for SQLite database file (used when `DB_TYPE=sqlite`)
- `DB_HOST`: Database host (for MySQL)
- `DB_PORT`: Database port (for MySQL)
- `DB_USERNAME`: Database username (for MySQL)
- `DB_PASSWORD`: Database password (for MySQL)
- `DB_DATABASE`: Database name (for MySQL)
- `DB_POOL_SIZE`: Connection pool size (for MySQL)
- `DB_MAX_OVERFLOW`: Max overflow connections (for MySQL)
- `DB_POOL_RECYCLE`: Connection recycle time in seconds (for MySQL)

Example `.env` configuration:

```env
# SQLite configuration
DB_TYPE=sqlite
DB_PATH=./backend/db/auth.db

# MySQL configuration
# DB_TYPE=mysql
# DB_HOST=db
# DB_PORT=3306
# DB_DATABASE=ai3_auth
# DB_USERNAME=ai3user
# DB_PASSWORD=ai3password
```

## Database Schema

The authentication system uses the following database tables:

### Users

Stores user account information:

- `id`: Unique identifier (UUID)
- `email`: Email address (username)
- `hashed_password`: Securely hashed password
- `active`: Account status
- `created_at`: Account creation timestamp
- `last_login`: Last successful login timestamp
- `mfa_secret`: Multi-factor authentication secret key
- `mfa_enabled`: MFA status
- `metadata`: Additional user metadata (JSON)

### Roles

Stores role definitions for RBAC:

- `id`: Unique identifier (UUID)
- `name`: Role name
- `description`: Role description

### User Roles

Junction table linking users to roles:

- `user_id`: User ID (foreign key)
- `role_id`: Role ID (foreign key)

### Refresh Tokens

Stores refresh tokens for JWT authentication:

- `id`: Token ID
- `user_id`: User ID (foreign key)
- `expires_at`: Token expiration timestamp
- `revoked`: Token revocation status
- `created_at`: Token creation timestamp

## CLI Commands

The application provides several CLI commands for database operations:

### Initialize Database

```bash
# Create all database tables (for development)
flask db_commands init
```

### Run Migrations

```bash
# Upgrade to the latest migration
flask db_commands upgrade

# Downgrade to a specific revision
flask db_commands downgrade --revision <revision_id>
```

### Create Migrations

```bash
# Create a new migration
flask db_commands migrate -m "description of the changes"
```

### Manage Users and Roles

```bash
# Create default roles
flask db_commands create-roles

# Create admin user
flask db_commands create-admin --username admin --password adminpassword
```

## Docker Integration

When running with Docker, the database settings can be configured using environment variables in your docker-compose file:

```yaml
services:
  backend:
    environment:
      - DB_TYPE=mysql
      - DB_HOST=db
      - DB_PORT=3306
      - DB_DATABASE=ai3_auth
      - DB_USERNAME=ai3user
      - DB_PASSWORD=ai3password
```

For MySQL in production, a dedicated database service is provided:

```yaml
services:
  db:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=rootpassword
      - MYSQL_DATABASE=ai3_auth
      - MYSQL_USER=ai3user
      - MYSQL_PASSWORD=ai3password
    volumes:
      - db_data:/var/lib/mysql
```

## Production Deployment

For production deployment, it's recommended to use MySQL instead of SQLite:

1. Start the MySQL service:

```bash
docker-compose --profile mysql up -d
```

2. Configure the backend to use MySQL:

```bash
export DB_TYPE=mysql
export DB_HOST=db
export DB_DATABASE=ai3_auth
export DB_USERNAME=ai3user
export DB_PASSWORD=ai3password
```

3. Run the migrations:

```bash
docker-compose exec backend flask db_commands upgrade
```

## Backup and Recovery

Regular database backups are recommended. For MySQL:

```bash
# Backup
docker-compose exec db mysqldump -u root -p ai3_auth > backup.sql

# Restore
cat backup.sql | docker-compose exec -T db mysql -u root -p ai3_auth
```

For SQLite:

```bash
# Backup
cp backend/db/auth.db backend/db/auth.db.backup

# Restore
cp backend/db/auth.db.backup backend/db/auth.db
```
