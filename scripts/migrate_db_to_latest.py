#!/usr/bin/env python3
"""
Comprehensive Database Migration Script
Migrates database from commit 585d193 (Serbian fields) to latest version (English fields)
"""

import sqlite3
import os
import sys
import shutil
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] - [%(name)s] - %(message)s'
)
logger = logging.getLogger(__name__)

# Get database path (check production location first)
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
    backup_file = os.path.join(BACKUP_DIR, f'erp_backup_migration_{timestamp}.db')
    try:
        shutil.copy2(DB_FILE, backup_file)
        logger.debug(f"Backup created successfully: {backup_file}")
        print(f"✓ Backup created: {backup_file}")
        return backup_file
    except Exception as e:
        logger.error(f"Failed to create backup: {e}", exc_info=True)
        raise


def column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def migrate_users_table(conn):
    """Add password_change_required field to users table if missing"""
    logger.debug("Migrating 'users' table...")
    print("\n▶ Migrating 'users' table...")
    cursor = conn.cursor()
    
    try:
        if not column_exists(cursor, 'users', 'password_change_required'):
            logger.debug("Adding 'password_change_required' column...")
            print("  → Adding 'password_change_required' column...")
            cursor.execute("ALTER TABLE users ADD COLUMN password_change_required BOOLEAN DEFAULT 0")
            conn.commit()
            logger.debug("'password_change_required' column added successfully")
            print("  ✓ Added 'password_change_required' column")
        else:
            logger.debug("Users table already up to date")
            print("  ✓ Users table already up to date")
            
    except Exception as e:
        conn.rollback()
        logger.error(f"Error migrating users table: {e}", exc_info=True)
        print(f"  ✗ Error migrating users table: {e}")
        raise


def migrate_orders_table(conn):
    """Migrate orders table: Serbian → English field names"""
    logger.debug("Migrating 'orders' table...")
    print("\n▶ Migrating 'orders' table...")
    cursor = conn.cursor()
    
    try:
        # Check if old columns exist
        cursor.execute("PRAGMA table_info(orders)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'naziv' not in columns:
            logger.debug("Orders table already migrated (English columns detected)")
            print("  ✓ Orders table already migrated (English columns detected)")
            return
        
        logger.debug("Converting Serbian to English columns...")
        print("  → Converting Serbian to English columns...")
        
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
                lager_id INTEGER,
                FOREIGN KEY (lager_id) REFERENCES lager (id)
            )
        """)
        
        # Copy data from old table to new
        cursor.execute("""
            INSERT INTO orders_new 
            (id, name, price, paid, customer, date, quantity, color, description, image, status, lager_id)
            SELECT id, naziv, cena, placeno, kupac, datum, kolicina, boja, opis, slika, status, lager_id
            FROM orders
        """)
        
        row_count = cursor.rowcount
        
        # Drop old table and rename new one
        logger.debug("Dropping old orders table and renaming new one...")
        cursor.execute("DROP TABLE orders")
        cursor.execute("ALTER TABLE orders_new RENAME TO orders")
        
        conn.commit()
        logger.debug(f"Orders table migrated successfully: {row_count} records")
        print(f"  ✓ Orders table migrated successfully ({row_count} records)")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error migrating orders table: {e}", exc_info=True)
        print(f"  ✗ Error migrating orders table: {e}")
        raise


def migrate_lager_table(conn):
    """Migrate lager table: Serbian → English field names"""
    logger.debug("Migrating 'lager' table...")
    print("\n▶ Migrating 'lager' table...")
    cursor = conn.cursor()
    
    try:
        # Check if old columns exist
        cursor.execute("PRAGMA table_info(lager)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'naziv' not in columns:
            logger.debug("Lager table already migrated (English columns detected)")
            print("  ✓ Lager table already migrated (English columns detected)")
            return
        
        logger.debug("Converting Serbian to English columns...")
        print("  → Converting Serbian to English columns...")
        
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
        
        row_count = cursor.rowcount
        
        # Drop old table and rename new one
        logger.debug("Dropping old lager table and renaming new one...")
        cursor.execute("DROP TABLE lager")
        cursor.execute("ALTER TABLE lager_new RENAME TO lager")
        
        conn.commit()
        logger.debug(f"Lager table migrated successfully: {row_count} records")
        print(f"  ✓ Lager table migrated successfully ({row_count} records)")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error migrating lager table: {e}", exc_info=True)
        print(f"  ✗ Error migrating lager table: {e}")
        raise


def verify_migration(conn):
    """Verify that migration was successful"""
    logger.debug("Verifying migration...")
    print("\n▶ Verifying migration...")
    cursor = conn.cursor()
    
    tables = {
        'users': ['id', 'username', 'email', 'password_hash', 'is_admin', 'password_change_required', 'created_at'],
        'orders': ['id', 'name', 'price', 'paid', 'customer', 'date', 'quantity', 'color', 'description', 'image', 'status', 'lager_id'],
        'lager': ['id', 'name', 'price', 'color', 'quantity', 'location', 'image'],
        'email_config': ['id', 'enabled', 'sender_email', 'app_password', 'receiver_email', 'days_before'],
        'notification_log': ['id', 'notify_key']
    }
    
    all_good = True
    
    for table_name, expected_columns in tables.items():
        try:
            cursor.execute(f"PRAGMA table_info({table_name})")
            actual_columns = [row[1] for row in cursor.fetchall()]
            
            missing = set(expected_columns) - set(actual_columns)
            if missing:
                logger.error(f"Table '{table_name}' missing columns: {missing}")
                print(f"  ✗ Table '{table_name}' missing columns: {missing}")
                all_good = False
            else:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                logger.debug(f"Table '{table_name}' verified: {count} records, all columns present")
                print(f"  ✓ Table '{table_name}': {count} records, all columns present")
                
        except Exception as e:
            logger.warning(f"Could not verify table '{table_name}': {e}")
            print(f"  ⚠ Could not verify table '{table_name}': {e}")
    
    logger.debug(f"Migration verification {'passed' if all_good else 'failed'}")
    return all_good


def main():
    logger.info("Starting database migration...")
    print("=" * 70)
    print("ERP DATABASE MIGRATION: Commit 585d193 → Latest")
    print("Serbian field names → English field names + New features")
    print("=" * 70)
    
    if not os.path.exists(DB_FILE):
        logger.error(f"Database not found: {DB_FILE}")
        print(f"\n✗ Database not found: {DB_FILE}")
        print("   Please ensure the database exists before running migration.")
        sys.exit(1)
    
    logger.info(f"Database file: {DB_FILE}")
    print(f"\n📁 Database file: {DB_FILE}")
    
    # Show file size
    db_size = os.path.getsize(DB_FILE)
    logger.debug(f"Database size: {db_size} bytes")
    print(f"📊 Database size: {db_size:,} bytes ({db_size / 1024:.2f} KB)")
    
    # Confirm before proceeding
    print("\n⚠️  This script will:")
    print("   1. Create a backup of your database")
    print("   2. Add new 'password_change_required' column to users table")
    print("   3. Rename Serbian columns to English in orders table")
    print("   4. Rename Serbian columns to English in lager table")
    print("   5. Verify all data integrity")
    
    response = input("\n❓ Continue with migration? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        logger.info("Migration cancelled by user")
        print("Migration cancelled.")
        sys.exit(0)
    
    logger.info("User confirmed migration, proceeding...")
    
    # Step 1: Backup
    print("\n" + "─" * 70)
    print("[1/4] Creating backup...")
    backup_file = backup_database()
    
    # Step 2: Connect
    print("\n" + "─" * 70)
    print("[2/4] Connecting to database...")
    logger.info(f"Connecting to database: {DB_FILE}")
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode=WAL")
    logger.info("Database connection established with WAL mode")
    print("  ✓ Connected successfully")
    
    # Step 3: Migrate
    print("\n" + "─" * 70)
    print("[3/4] Running migrations...")
    logger.info("Starting migration process...")
    
    try:
        migrate_users_table(conn)
        migrate_orders_table(conn)
        migrate_lager_table(conn)
        logger.info("All migrations completed successfully")
    except Exception as e:
        logger.error(f"MIGRATION FAILED: {e}", exc_info=True)
        print(f"\n✗✗✗ MIGRATION FAILED: {e}")
        print(f"    Your data is safe in the backup: {backup_file}")
        conn.close()
        sys.exit(1)
    
    # Step 4: Verify
    print("\n" + "─" * 70)
    print("[4/4] Verifying migration...")
    
    if verify_migration(conn):
        conn.close()
        logger.info("Migration completed successfully")
        print("\n" + "=" * 70)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print(f"\n✓ Backup saved: {backup_file}")
        print("✓ Database migrated to latest schema")
        print("✓ All data preserved and verified")
        print("\n👉 You can now restart your ERP application.")
    else:
        conn.close()
        logger.warning("Migration completed with warnings")
        print("\n" + "=" * 70)
        print("⚠️  MIGRATION COMPLETED WITH WARNINGS")
        print("=" * 70)
        print(f"✓ Backup saved: {backup_file}")
        print("Some verification checks failed. Please review the output above.")
        sys.exit(1)


if __name__ == '__main__':
    main()
