import sys

import alembic.config
import click
from db.session import db
from flask import Flask
from flask.cli import with_appcontext


def register_cli_commands(app: Flask):
    """Register CLI commands with Flask application."""

    @app.cli.group(help="Database operations")
    def db_commands():
        """Database operations commands."""
        pass

    @db_commands.command("init", help="Initialize the database and create tables")
    @with_appcontext
    def init_db():
        """Initialize the database and create tables."""
        try:
            db.create_all()
            click.echo("Database initialized and tables created.")
        except Exception as e:
            click.echo(f"Error initializing database: {str(e)}", err=True)
            sys.exit(1)

    @db_commands.command("upgrade", help="Upgrade database to the latest migration")
    @click.option("--revision", default="head", help="Revision to upgrade to (default: head)")
    @with_appcontext
    def upgrade_db(revision):
        """Upgrade the database to the latest migration."""
        try:
            # Use alembic config directly for more reliable migrations
            config = alembic.config.Config("alembic.ini")

            # Run the migration
            args = ["upgrade", revision]
            alembic.config.main(argv=args, config=config)

            click.echo(f"Successfully upgraded database to revision: {revision}")
        except Exception as e:
            click.echo(f"Error upgrading database: {str(e)}", err=True)
            sys.exit(1)

    @db_commands.command("downgrade", help="Downgrade database to a previous migration")
    @click.option("--revision", required=True, help="Revision to downgrade to")
    @with_appcontext
    def downgrade_db(revision):
        """Downgrade the database to a previous migration."""
        try:
            config = alembic.config.Config("alembic.ini")
            args = ["downgrade", revision]
            alembic.config.main(argv=args, config=config)
            click.echo(f"Successfully downgraded database to revision: {revision}")
        except Exception as e:
            click.echo(f"Error downgrading database: {str(e)}", err=True)
            sys.exit(1)

    @db_commands.command("migrate", help="Create a new migration")
    @click.option("--message", "-m", required=True, help="Migration message")
    @with_appcontext
    def create_migration(message):
        """Create a new migration based on current model changes."""
        try:
            config = alembic.config.Config("alembic.ini")
            args = ["revision", "--autogenerate", "-m", message]
            alembic.config.main(argv=args, config=config)
            click.echo(f"Migration created with message: {message}")
        except Exception as e:
            click.echo(f"Error creating migration: {str(e)}", err=True)
            sys.exit(1)

    @db_commands.command("create-roles", help="Create default roles")
    @with_appcontext
    def create_roles():
        """Create default roles in the database."""
        from app import app
        from models.user import Role

        try:
            with app.app_context():
                # Check if roles already exist
                roles = db.session.query(Role).all()
                if roles:
                    click.echo(f"Found {len(roles)} existing roles.")

                # Create default roles
                app.auth_service.create_default_roles()
                click.echo("Default roles created successfully.")
        except Exception as e:
            click.echo(f"Error creating roles: {str(e)}", err=True)
            sys.exit(1)

    @db_commands.command("create-admin", help="Create admin user")
    @click.option("--username", default=None, help="Admin username")
    @click.option("--password", default=None, help="Admin password")
    @with_appcontext
    def create_admin(username, password):
        """Create admin user in the database."""
        from app import app

        try:
            with app.app_context():
                # Use provided credentials or default from config
                admin_username = username or app.config.get("ADMIN_USERNAME", "admin")
                admin_password = password or app.config.get("ADMIN_PASSWORD", "admin")

                try:
                    app.auth_service.create_user(
                        username=admin_username,
                        password=admin_password,
                        roles=["admin"],
                    )
                    click.echo(f"Admin user '{admin_username}' created successfully.")
                except ValueError as e:
                    click.echo(f"Note: {str(e)}")
        except Exception as e:
            click.echo(f"Error creating admin user: {str(e)}", err=True)
            sys.exit(1)
