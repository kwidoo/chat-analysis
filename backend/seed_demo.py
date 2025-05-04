from app import db
from models.user import User  # Adjust import based on your actual model structure
import hashlib

def seed():
    """Create a demo user for testing purposes."""
    # Check if demo user already exists
    if not User.query.filter_by(email="demo@example.com").first():
        # Create password hash - in a real app use werkzeug.security or similar
        password_hash = hashlib.sha256("demo123".encode()).hexdigest()

        # Create user - adjust fields based on your User model
        user = User(
            email="demo@example.com",
            password_hash=password_hash,
            name="Demo User",
            role="user"
        )

        db.session.add(user)
        db.session.commit()
        print("Demo user created successfully.")
    else:
        print("Demo user already exists.")

if __name__ == "__main__":
    seed()
