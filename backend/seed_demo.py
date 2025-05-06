from app import app
import logging


def seed():
    """Create demo users for testing purposes."""
    logger = logging.getLogger(__name__)

    try:
        # Create a regular user
        try:
            app.auth_service.create_user(
                username="demo@example.com", password="demo123", roles=["user"]
            )
            logger.info("Created demo user: demo@example.com")
        except ValueError as e:
            logger.info(f"Demo user may already exist: {e}")

        # Create an admin user
        try:
            app.auth_service.create_user(
                username="admin@example.com", password="admin123", roles=["admin"]
            )
            logger.info("Created admin user: admin@example.com")
        except ValueError as e:
            logger.info(f"Admin user may already exist: {e}")

        print("Seeding completed successfully!")

    except Exception as e:
        logger.error(f"Error seeding users: {e}")
        print(f"Failed to seed users: {e}")


if __name__ == "__main__":
    seed()
