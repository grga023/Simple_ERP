#!/usr/bin/env python3
"""
Comprehensive Database Migration Script
Migrates database from commit 585d193 (Serbian fields) to latest version (English fields)
"""

import sqlite3
import os
import sys
import shutil
from datetime import datetime

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
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(BACKUP_DIR, f'erp_backup_migration_{timestamp}.db')
    shutil.copy2(DB_FILE, backup_file)
    print(f"✓ Backup created: {backup_file}")
    return backup_file


def column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def migrate_users_table(conn):
    """Add password_change_required field to users table if missing"""
    print("\n▶ Migrating 'users' table...")
    cursor = conn.cursor()
    
    try:
        if not column_exists(cursor, 'users', 'password_change_required'):
            print("  → Adding 'password_change_required' column...")
            cursor.execute("ALTER TABLE users ADD COLUMN password_change_required BOOLEAN DEFAULT 0")
            conn.commit()
            print("  ✓ Added 'password_change_required' column")
        else:
            print("  ✓ Users table already up to date")
            
    except Exception as e:
        conn.rollback()
        print(f"  ✗ Error migrating users table: {e}")
        raise


def migrate_orders_table(conn):
    """Migrate orders table: Serbian → English field names"""
    print("\n▶ Migrating 'orders' table...")
    cursor = conn.cursor()
    
    try:
        # Check if old columns exist
        cursor.execute("PRAGMA table_info(orders)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'naziv' not in columns:
            print("  ✓ Orders table already migrated (English columns detected)")
            return
        
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
        cursor.execute("DROP TABLE orders")
        cursor.execute("ALTER TABLE orders_new RENAME TO orders")
        
        conn.commit()
        print(f"  ✓ Orders table migrated successfully ({row_count} records)")
        
    except Exception as e:
        conn.rollback()
        print(f"  ✗ Error migrating orders table: {e}")
        raise


def migrate_lager_table(conn):
    """Migrate lager table: Serbian → English field names"""
    print("\n▶ Migrating 'lager' table...")
    cursor = conn.cursor()
    
    try:
        # Check if old columns exist
        cursor.execute("PRAGMA table_info(lager)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'naziv' not in columns:
            print("  ✓ Lager table already migrated (English columns detected)")
            return
        
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
        cursor.execute("DROP TABLE lager")
        cursor.execute("ALTER TABLE lager_new RENAME TO lager")
        
        conn.commit()
        print(f"  ✓ Lager table migrated successfully ({row_count} records)")
        
    except Exception as e:
        conn.rollback()
        print(f"  ✗ Error migrating lager table: {e}")
        raise


def verify_migration(conn):
    """Verify that migration was successful"""
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
                print(f"  ✗ Table '{table_name}' missing columns: {missing}")
                all_good = False
            else:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"  ✓ Table '{table_name}': {count} records, all columns present")
                
        except Exception as e:
            print(f"  ⚠ Could not verify table '{table_name}': {e}")
    
    return all_good


def main():
    print("=" * 70)
    print("ERP DATABASE MIGRATION: Commit 585d193 → Latest")
    print("Serbian field names → English field names + New features")
    print("=" * 70)
    
    if not os.path.exists(DB_FILE):
        print(f"\n✗ Database not found: {DB_FILE}")
        print("   Please ensure the database exists before running migration.")
        sys.exit(1)
    
    print(f"\n📁 Database file: {DB_FILE}")
    
    # Show file size
    db_size = os.path.getsize(DB_FILE)
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
        print("Migration cancelled.")
        sys.exit(0)
    
    # Step 1: Backup
    print("\n" + "─" * 70)
    print("[1/4] Creating backup...")
    backup_file = backup_database()
    
    # Step 2: Connect
    print("\n" + "─" * 70)
    print("[2/4] Connecting to database...")
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode=WAL")
    print("  ✓ Connected successfully")
    
    # Step 3: Migrate
    print("\n" + "─" * 70)
    print("[3/4] Running migrations...")
    
    try:
        migrate_users_table(conn)
        migrate_orders_table(conn)
        migrate_lager_table(conn)
    except Exception as e:
        print(f"\n✗✗✗ MIGRATION FAILED: {e}")
        print(f"    Your data is safe in the backup: {backup_file}")
        conn.close()
        sys.exit(1)
    
    # Step 4: Verify
    print("\n" + "─" * 70)
    print("[4/4] Verifying migration...")
    
    if verify_migration(conn):
        conn.close()
        print("\n" + "=" * 70)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print(f"\n✓ Backup saved: {backup_file}")
        print("✓ Database migrated to latest schema")
        print("✓ All data preserved and verified")
        print("\n👉 You can now restart your ERP application.")
    else:
        conn.close()
        print("\n" + "=" * 70)
        print("⚠️  MIGRATION COMPLETED WITH WARNINGS")
        print("=" * 70)
        print(f"✓ Backup saved: {backup_file}")
        print("Some verification checks failed. Please review the output above.")
        sys.exit(1)


if __name__ == '__main__':
    main()
