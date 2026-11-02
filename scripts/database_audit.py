from sqlalchemy import inspect
from sqlalchemy.orm import configure_mappers

import app.models

from app.database.base import Base
from app.database.session import engine


EXPECTED_TABLES = {
    "users",
    "user_preferences",
    "conversations",
    "messages",
    "documents",
    "learning_activities",
    "study_resources",
    "resource_categories",
    "study_resource_categories",
    "user_resource_interactions",
    "recommendations",
    "recommendation_feedback",
}


def audit_model_registry():
    print("\n========== MODEL REGISTRY ==========")

    actual_tables = set(Base.metadata.tables.keys())

    missing = EXPECTED_TABLES - actual_tables

    for table in sorted(actual_tables):
        print(f"[FOUND] {table}")

    assert not missing, f"Missing model tables: {missing}"

    print("All expected models registered.")


def audit_relationships():
    print("\n========== ORM RELATIONSHIPS ==========")

    configure_mappers()

    for mapper in Base.registry.mappers:
        print(f"\n{mapper.class_.__name__}")

        for relationship in mapper.relationships:
            print(
                f"  {relationship.key} -> "
                f"{relationship.mapper.class_.__name__}"
            )

    print("\nAll ORM relationships configured.")


def audit_database():
    print("\n========== DATABASE AUDIT ==========")

    inspector = inspect(engine)

    actual_tables = set(inspector.get_table_names())

    for table in sorted(EXPECTED_TABLES):
        assert table in actual_tables, (
            f"Database table missing: {table}"
        )

        print(f"\nTABLE: {table}")

        primary_key = inspector.get_pk_constraint(table)

        print("PRIMARY KEY:", primary_key)

        for foreign_key in inspector.get_foreign_keys(table):
            print(
                "FOREIGN KEY:",
                foreign_key["constrained_columns"],
                "->",
                foreign_key["referred_table"],
                foreign_key.get("options"),
            )

        for index in inspector.get_indexes(table):
            print(
                "INDEX:",
                index["name"],
                index["column_names"],
                "UNIQUE:",
                index["unique"],
            )

        for constraint in inspector.get_check_constraints(table):
            print(
                "CHECK:",
                constraint["name"],
            )

    print("\nDatabase audit completed.")


def audit_foreign_key_indexes():
    print("\n========== FOREIGN KEY INDEX COVERAGE ==========")

    inspector = inspect(engine)

    for table in sorted(EXPECTED_TABLES):
        indexes = inspector.get_indexes(table)

        indexed_columns = [
            tuple(index["column_names"])
            for index in indexes
            if index["column_names"]
        ]

        for foreign_key in inspector.get_foreign_keys(table):
            columns = tuple(foreign_key["constrained_columns"])

            covered = any(
                index_columns[:len(columns)] == columns
                for index_columns in indexed_columns
            )

            if covered:
                print(f"[COVERED] {table}: {columns}")
            else:
                print(f"[REVIEW] {table}: {columns}")


def main():
    audit_model_registry()
    audit_relationships()
    audit_database()
    audit_foreign_key_indexes()

    print("\n========== AUDIT SUCCESSFUL ==========")


if __name__ == "__main__":
    main()