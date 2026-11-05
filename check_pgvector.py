from sqlalchemy import text
from app.database.session import engine


def main():
    with engine.connect() as connection:

        print("\n--- PGVECTOR EXTENSION AVAILABILITY ---")

        extensions = connection.execute(
            text("""
                SELECT name, default_version, installed_version
                FROM pg_available_extensions
                WHERE name = 'vector'
            """)
        ).fetchall()

        print(extensions if extensions else "pgvector extension files NOT FOUND")

        print("\n--- DATABASE USER PRIVILEGES ---")

        privileges = connection.execute(
            text("""
                SELECT current_user, rolsuper, rolcreatedb
                FROM pg_roles
                WHERE rolname = current_user
            """)
        ).fetchone()

        print(privileges)

        print("\n--- DATABASE CONNECTION ---")

        database = connection.execute(
            text("SELECT current_database(), current_user")
        ).fetchone()

        print(database)


if __name__ == "__main__":
    main()
