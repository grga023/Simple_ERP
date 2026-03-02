#!/usr/bin/env python3
"""
migrate_json.py - Migrate existing JSON data to SQLite database.

Run this ONCE after the refactor to import your existing data:
    python migrate_json.py

It will:
  1. Read all JSON files from data/ (new_ord.json, for_delivery.json, realized.json, lager.json)
  2. Read email_config.json and notified.json if they exist
  3. Insert everything into the new SQLite database (data/erp.db)
  4. Skip migration if the database already has data

The original JSON files are NOT deleted (kept as backup).
"""

import json
import os
import sys
import logging

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] - [%(name)s] - %(message)s'
)

# Ensure we can import from the project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from ERP_server import create_app
from models import db, Order, LagerItem, EmailConfig, NotificationLog


BASE_DIR = PROJECT_ROOT
DATA_DIR = os.path.join(BASE_DIR, 'data')


def load_json(filename):
    """Load a JSON file from the data directory, return empty list/dict on failure."""
    filepath = os.path.join(DATA_DIR, filename)
    logger.debug(f"Loading JSON file: {filepath}")
    if not os.path.exists(filepath):
        logger.warning(f"JSON file not found: {filename}")
        return []
    try:
        with open(filepath, encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Successfully loaded {filename}")
        return data
    except (json.JSONDecodeError, IOError) as e:
        print(f'  [WARNING] Could not read {filename}: {e}')
        logger.error(f"Could not read {filename}: {e}", exc_info=True)
        return []


def migrate_orders():
    """Migrate orders from all 3 JSON files."""
    logger.debug("Starting orders migration from JSON files...")
    count = 0
    for filename, status in [
        ('new_ord.json', 'new'),
        ('for_delivery.json', 'for_delivery'),
        ('realized.json', 'realized')
    ]:
        orders = load_json(filename)
        if not orders:
            print(f'  {filename}: 0 orders (empty or missing)')
            logger.debug(f"{filename}: No orders to migrate")
            continue

        for o in orders:
            order = Order(
                naziv=o.get('naziv', ''),
                cena=float(o.get('cena', 0)),
                placeno=bool(o.get('placeno', False)),
                kupac=o.get('kupac', ''),
                datum=o.get('datum', ''),
                kolicina=int(o.get('kolicina', 1)),
                boja=o.get('boja', ''),
                opis=o.get('opis', ''),
                slika=o.get('slika', ''),
                status=status,
                lager_id=o.get('lager_id')
            )
            db.session.add(order)
            count += 1

        print(f'  {filename}: {len(orders)} orders migrated as "{status}"')
        logger.debug(f"Migrated {len(orders)} orders from {filename} with status '{status}'")

    logger.debug(f"Total orders migrated: {count}")
    return count


def migrate_lager():
    """Migrate lager items from lager.json."""
    logger.debug("Starting lager migration from JSON...")
    items = load_json('lager.json')
    if not items:
        print('  lager.json: 0 items (empty or missing)')
        logger.debug("No lager items to migrate")
        return 0

    for item in items:
        lager_item = LagerItem(
            naziv=item.get('naziv', ''),
            cena=float(item.get('cena', 0)),
            boja=item.get('boja', ''),
            kolicina=int(item.get('kolicina', 0)),
            lokacija=item.get('lokacija', 'Kuća'),
            slika=item.get('slika', '')
        )
        db.session.add(lager_item)

    print(f'  lager.json: {len(items)} items migrated')
    logger.debug(f"Migrated {len(items)} lager items")
    return len(items)


def migrate_email_config():
    """Migrate email config from email_config.json."""
    logger.debug("Starting email config migration...")
    config_data = load_json('email_config.json')
    if not config_data:
        print('  email_config.json: not found or empty, skipping')
        logger.debug("No email config to migrate")
        return

    # email_config.json is a dict, not a list
    if isinstance(config_data, dict):
        config = EmailConfig(
            enabled=config_data.get('enabled', False),
            sender_email=config_data.get('sender_email', ''),
            app_password=config_data.get('app_password', ''),
            receiver_email=config_data.get('receiver_email', ''),
            days_before=int(config_data.get('days_before', 2))
        )
        db.session.add(config)
        print('  email_config.json: migrated')
        logger.debug("Email config migrated successfully")
    else:
        print('  email_config.json: unexpected format, skipping')
        logger.warning(f"Email config has unexpected format: {type(config_data)}")


def migrate_notifications():
    """Migrate notification log from notified.json."""
    logger.debug("Starting notification log migration...")
    notified = load_json('notified.json')
    if not notified:
        print('  notified.json: not found or empty, skipping')
        logger.debug("No notifications to migrate")
        return

    count = 0
    for key in notified:
        if isinstance(key, str):
            existing = NotificationLog.query.filter_by(notify_key=key).first()
            if not existing:
                db.session.add(NotificationLog(notify_key=key))
                count += 1

    print(f'  notified.json: {count} notification keys migrated')
    logger.debug(f"Migrated {count} notification keys")


def main():
    logger.info("Starting JSON to SQLite migration")
    print('=' * 50)
    print('JSON → SQLite Migration')
    print('=' * 50)

    app = create_app()

    with app.app_context():
        # Check if database already has data
        existing_orders = Order.query.count()
        existing_lager = LagerItem.query.count()
        logger.debug(f"Current database state: {existing_orders} orders, {existing_lager} lager items")
        
        if existing_orders > 0 or existing_lager > 0:
            print(f'\n  Database already has data ({existing_orders} orders, {existing_lager} lager items).')
            logger.warning("Database contains existing data")
            answer = input('  Overwrite? (y/N): ').strip().lower()
            logger.debug(f"User overwrite choice: {answer}")
            if answer != 'y':
                print('  Migration cancelled.')
                logger.info("Migration cancelled by user")
                return
            # Clear existing data
            logger.debug("Clearing existing data...")
            NotificationLog.query.delete()
            EmailConfig.query.delete()
            LagerItem.query.delete()
            Order.query.delete()
            db.session.commit()
            print('  Existing data cleared.\n')
            logger.debug("Existing data cleared successfully")

        print('\nMigrating orders...')
        order_count = migrate_orders()

        print('\nMigrating lager...')
        lager_count = migrate_lager()

        print('\nMigrating email config...')
        migrate_email_config()

        print('\nMigrating notification log...')
        migrate_notifications()

        # Commit all changes
        try:
            db.session.commit()
            logger.debug("All migrations committed to database")
        except Exception as e:
            logger.error(f"Failed to commit migrations: {e}", exc_info=True)
            db.session.rollback()
            raise

        print('\n' + '=' * 50)
        print(f'Migration complete!')
        print(f'  Orders: {order_count}')
        print(f'  Lager items: {lager_count}')
        print(f'  Database: {os.path.join(DATA_DIR, "erp.db")}')
        print(f'\nOriginal JSON files are preserved in data/ as backup.')
        print('=' * 50)
        logger.debug(f"Migration completed: {order_count} orders, {lager_count} lager items")


if __name__ == '__main__':
    main()
