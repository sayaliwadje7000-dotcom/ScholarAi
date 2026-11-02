import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing from .env")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

try:
    with engine.connect() as connection:
        result = connection.execute(
            text("""
                SELECT
                    current_database(),
                    current_user,
                    version()
            """)
        )

        database, user, version = result.fetchone()

        print("DATABASE CONNECTION SUCCESSFUL")
        print("--------------------------------")
        print("Database:", database)
        print("User:", user)
        print("PostgreSQL:", version)

except Exception as error:
    print("DATABASE CONNECTION FAILED")
    print(type(error).__name__ + ":", error)

    raise

finally:
    engine.dispose()
    