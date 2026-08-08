from app.database import init_db, get_db_context
from app.seed import seed_database

def initialize():
    """Initialize database and seed with sample data"""
    print("Creating database tables...")
    init_db()
    print("Seeding database with sample data...")
    seed_database()
    print("Database initialization complete!")

if __name__ == "__main__":
    initialize()