#!/usr/bin/env python3
"""
Migration script: Convert database schema from Serbian field names to English
This script safely migrates all existing data while preserving integrity.
"""

import sqlite3
import os
import sys
import shutil
import logging
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] - [%(name)s] - %(message)s'
)

# Get database path (production location)
if os.path.exists('/usb/ERP_data/data/erp.db'):
    DB_FILE = '/usb/ERP_data/data/erp.db'
    BACKUP_DIR = '/usb/ERP_data/data/backups'
else:
    # Fallback to workspace
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    DB_FILE = os.path.join(DATA_DIR, 'erp.db')
    BACKUP_DIR = os.path.join(DATA_DIR, 'backups')

os.makedirs(BACKUP_DIR, exist_ok=True)

def backup_database():
    """Create backup before migration"""
    logger.debug("Creating database backup...")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(BACKUP_DIR, f'erp_backup_{timestamp}.db')
    try:
        shutil.copy2(DB_FILE, backup_file)
        print(f"✓ Backup created: {backup_file}")
        logger.debug(f"Backup created successfully: {backup_file}")
        return backup_file
    except Exception as e:
        logger.error(f"Failed to create backup: {e}", exc_info=True)
        raise

def migrate_orders_table(conn):
    """Migrate orders table: Serbian → English fields"""
    logger.debug("Starting orders table migration...")
    print("\n▶ Migrating 'orders' table...")
    cursor = conn.cursor()
    
    try:
        # Check if old columns exist
        cursor.execute("PRAGMA table_info(orders)")
        columns = [row[1] for row in cursor.fetchall()]
        logger.debug(f"Orders table columns: {columns}")
        
        if 'naziv' not in columns:
            print("  ⚠ Orders table already migrated (old columns missing)")
            logger.warning("Orders table already migrated, skipping")
            return
        
        # Create new table with English column names
        cursor.execute("""
            CREATE TABLE orders_new (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                price REAL NOT NULL DEFAULT 0,
                paid BOOLEAN DEFAULT 0,
                customer TEXT NOT NULL,
                date TEXT DEFAULT '',
                quantity INTEGER DEFAULT 1,
                color TEXT DEFAULT '',
                description TEXT DEFAULT '',
                image TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'new',
                lager_id INTEGER
            )
        """)
        
        # Copy data from old table to new
        cursor.execute("""
            INSERT INTO orders_new 
            (id, name, price, paid, customer, date, quantity, color, description, image, status, lager_id)
            SELECT id, naziv, cena, placeno, kupac, datum, kolicina, boja, opis, slika, status, lager_id
            FROM orders
        """)
        
        # Drop old table and rename new one
        cursor.execute("DROP TABLE orders")
        cursor.execute("ALTER TABLE orders_new RENAME TO orders")
        
        conn.commit()
        print("  ✓ Orders table migrated successfully")
        logger.debug("Orders table migrated successfully")
        
    except Exception as e:
        conn.rollback()
        print(f"  ✗ Error migrating orders table: {e}")
        logger.error(f"Error migrating orders table: {e}", exc_info=True)
        raise

def migrate_lager_table(conn):
    """Migrate lager table: Serbian → English fields"""
    logger.debug("Starting lager table migration...")
    print("\n▶ Migrating 'lager' table...")
    cursor = conn.cursor()
    
    try:
        # Check if old columns exist
        cursor.execute("PRAGMA table_info(lager)")
        columns = [row[1] for row in cursor.fetchall()]
        logger.debug(f"Lager table columns: {columns}")
        
        if 'naziv' not in columns:
            print("  ⚠ Lager table already migrated (old columns missing)")
            logger.warning("Lager table already migrated, skipping")
            return
        
        # Create new table with English column names
        cursor.execute("""
            CREATE TABLE lager_new (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                price REAL DEFAULT 0,
                color TEXT DEFAULT '',
                quantity INTEGER DEFAULT 0,
                location TEXT DEFAULT 'House',
                image TEXT DEFAULT ''
            )
        """)
        
        # Copy data from old table to new
        cursor.execute("""
            INSERT INTO lager_new 
            (id, name, price, color, quantity, location, image)
            SELECT id, naziv, cena, boja, kolicina, lokacija, slika
            FROM lager
        """)
        
        # Drop old table and rename new one
        cursor.execute("DROP TABLE lager")
        cursor.execute("ALTER TABLE lager_new RENAME TO lager")
        
        conn.commit()
        print("  ✓ Lager table migrated successfully")
        logger.debug("Lager table migrated successfully")
        
    except Exception as e:
        conn.rollback()
        print(f"  ✗ Error migrating lager table: {e}")
        logger.error(f"Error migrating lager table: {e}", exc_info=True)
        raise

def migrate_email_config_table(conn):
    """Migrate email_config table (no changes needed, already English)"""
    print("\n▶ Checking 'email_config' table...")
    cursor = conn.cursor()
    
    try:
        cursor.execute("PRAGMA table_info(email_config)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # This table is already in English, just verify
        if 'sender_email' in columns:
            print("  ✓ Email config table already in English")
        
    except Exception as e:
        print(f"  ⚠ Email config table check skipped: {e}")

def main():
    logger.info("Starting Serbian to English database migration")
    print("=" * 60)
    print("ERP Database Migration: Serbian → English")
    print("=" * 60)
    
    if not os.path.exists(DB_FILE):
        print(f"\n✗ Database not found: {DB_FILE}")
        logger.error(f"Database file not found: {DB_FILE}")
        sys.exit(1)
    
    logger.info(f"Using database: {DB_FILE}")
    
    # Backup first
    print("\n[1/4] Creating backup...")
    backup_database()
    
    # Connect to database
    print("\n[2/4] Connecting to database...")
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.execute("PRAGMA journal_mode=WAL")
        print("  ✓ Connected")
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}", exc_info=True)
        print(f"\n✗ Connection failed: {e}")
        sys.exit(1)
    
    # Migrate tables
    print("\n[3/4] Migrating tables...")
    logger.info("Beginning table migrations...")
    try:
        migrate_orders_table(conn)
        migrate_lager_table(conn)
        migrate_email_config_table(conn)
        logger.info("All table migrations completed")
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        logger.error(f"Migration failed: {e}", exc_info=True)
        conn.close()
        sys.exit(1)
    
    # Verify
    print("\n[4/4] Verifying migration...")
    logger.debug("Starting migration verification...")
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT COUNT(*) FROM orders")
        order_count = cursor.fetchone()[0]
        print(f"  ✓ Orders: {order_count} records")
        logger.debug(f"Orders table verified: {order_count} records")
        
        cursor.execute("SELECT COUNT(*) FROM lager")
        lager_count = cursor.fetchone()[0]
        print(f"  ✓ Lager: {lager_count} records")
        logger.debug(f"Lager table verified: {lager_count} records")
        
        conn.close()
        print("\n" + "=" * 60)
        print("✅ Migration completed successfully!")
        print("=" * 60)
        logger.debug("Migration completed successfully")
        
    except Exception as e:
        print(f"\n✗ Verification failed: {e}")
        logger.error(f"Verification failed: {e}", exc_info=True)
        conn.close()
        sys.exit(1)

if __name__ == '__main__':
    main()
