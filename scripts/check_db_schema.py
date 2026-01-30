
from sqlalchemy import create_engine, inspect
import os
from app.core.config import settings

def check_schema():
    # Force sync driver
    db_url = settings.SQLALCHEMY_DATABASE_URI.replace("postgresql+asyncpg", "postgresql")
    engine = create_engine(db_url)
    inspector = inspect(engine)
    
    columns = inspector.get_columns('user_profiles')
    print("Columns in 'user_profiles':")
    for col in columns:
        print(f"- {col['name']} ({col['type']})")

if __name__ == "__main__":
    check_schema()
