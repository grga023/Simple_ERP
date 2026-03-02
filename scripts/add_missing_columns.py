#!/usr/bin/env python3
"""
add_missing_columns.py - Add missing database columns to existing tables.

This script safely adds any missing columns to the database schema.
Run this when the model definitions are updated but the database hasn't been migrated.
"""

import sqlite3
import os
import sys
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] - [%(name)s] - %(message)s'
)
logger = logging.getLogger(__name__)

# Ensure we can import from the project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

BASE_DIR = PROJECT_ROOT
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'erp.db')


def column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table."""
    logger.debug(f"Checking if column {column_name} exists in table {table_name}")
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    exists = column_name in columns
    logger.debug(f"Column {column_name} in {table_name}: {'exists' if exists else 'not found'}")
    return exists


def add_missing_columns():
    """Add any missing columns to the database."""
    if not os.path.exists(DB_PATH):
        logger.error(f"Database not found at {DB_PATH}")
        print(f"Database not found at {DB_PATH}")
        return

    logger.info(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    changes_made = False

    # Add lager_id to orders table if missing
    logger.info("Checking for missing 'lager_id' column in 'orders' table...")
    if not column_exists(cursor, 'orders', 'lager_id'):
        logger.info("Adding 'lager_id' column to 'orders' table...")
        print("Adding 'lager_id' column to 'orders' table...")
        try:
            cursor.execute("ALTER TABLE orders ADD COLUMN lager_id INTEGER")
            changes_made = True
            logger.info("'lager_id' column added successfully")
            print("✓ Added 'lager_id' column")
        except Exception as e:
            logger.error(f"Failed to add 'lager_id' column: {e}", exc_info=True)
            raise
    else:
        logger.debug("'lager_id' column already exists in 'orders' table")
        print("'lager_id' column already exists in 'orders' table")

    # Add any other missing columns here as needed
    # Example:
    # if not column_exists(cursor, 'table_name', 'column_name'):
    #     cursor.execute("ALTER TABLE table_name ADD COLUMN column_name TYPE DEFAULT VALUE")
    #     changes_made = True

    if changes_made:
        conn.commit()
        logger.info("Database schema updated successfully")
        print("\n✓ Database schema updated successfully!")
    else:
        logger.info("Database schema is up to date")
        print("\n✓ Database schema is up to date")

    conn.close()
    logger.info("Database connection closed")


if __name__ == '__main__':
    print("=" * 60)
    print("Adding missing database columns...")
    print("=" * 60)
    add_missing_columns()
