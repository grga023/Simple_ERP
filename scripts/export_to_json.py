#!/usr/bin/env python3
"""
export_to_json.py - Export SQLite database to JSON files (daily backup).

This script reads data from the SQLite database and exports it to JSON files
in the data/ directory. It creates a snapshot of the current state of the database.

Run manually:
    python export_to_json.py

Or schedule it to run daily at 3 AM using cron (Linux) or Task Scheduler (Windows).
"""

import json
import os
import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] - [%(name)s] - %(message)s'
)
logger = logging.getLogger(__name__)

# Ensure we can import from the project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from ERP_server import create_app
from models import db, Order, LagerItem, EmailConfig, NotificationLog


BASE_DIR = PROJECT_ROOT
DATA_DIR = os.path.join(BASE_DIR, 'data')


def export_orders():
    """Export orders to separate JSON files based on status."""
    logger.debug("Exporting orders...")
    # Get orders by status
    new_orders = Order.query.filter_by(status='new').all()
    for_delivery = Order.query.filter_by(status='for_delivery').all()
    realized = Order.query.filter_by(status='realized').all()

    logger.debug(f"Found {len(new_orders)} new, {len(for_delivery)} for_delivery, {len(realized)} realized orders")

    # Convert to dictionaries
    new_data = [o.to_dict() for o in new_orders]
    delivery_data = [o.to_dict() for o in for_delivery]
    realized_data = [o.to_dict() for o in realized]

    # Save to files
    try:
        with open(os.path.join(DATA_DIR, 'new_ord.json'), 'w', encoding='utf-8') as f:
            json.dump(new_data, f, ensure_ascii=False, indent=2)
        logger.debug("new_ord.json saved")

        with open(os.path.join(DATA_DIR, 'for_delivery.json'), 'w', encoding='utf-8') as f:
            json.dump(delivery_data, f, ensure_ascii=False, indent=2)
        logger.debug("for_delivery.json saved")

        with open(os.path.join(DATA_DIR, 'realized.json'), 'w', encoding='utf-8') as f:
            json.dump(realized_data, f, ensure_ascii=False, indent=2)
        logger.debug("realized.json saved")
        
        logger.debug(f"Orders exported: {len(new_data)} new, {len(delivery_data)} delivery, {len(realized_data)} realized")
    except Exception as e:
        logger.error(f"Error exporting orders: {e}", exc_info=True)
        raise

    return len(new_data), len(delivery_data), len(realized_data)


def export_lager():
    """Export lager items to JSON."""
    logger.debug("Exporting lager items...")
    try:
        items = LagerItem.query.all()
        data = [item.to_dict() for item in items]
        logger.debug(f"Found {len(items)} lager items")

        with open(os.path.join(DATA_DIR, 'lager.json'), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.debug(f"Lager exported: {len(data)} items")
        return len(data)
    except Exception as e:
        logger.error(f"Error exporting lager: {e}", exc_info=True)
        raise


def export_email_config():
    """Export email config to JSON."""
    logger.debug("Exporting email config...")
    try:
        config = EmailConfig.query.first()
        if config:
            data = {
                'enabled': config.enabled,
                'sender_email': config.sender_email,
                'app_password': config.app_password,
                'receiver_email': config.receiver_email,
                'days_before': config.days_before
            }
            with open(os.path.join(DATA_DIR, 'email_config.json'), 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug("Email config exported successfully")
            return True
        logger.warning("No email config found to export")
        return False
    except Exception as e:
        logger.error(f"Error exporting email config: {e}", exc_info=True)
        raise


def export_notifications():
    """Export notification log to JSON."""
    logger.debug("Exporting notification log...")
    try:
        logs = NotificationLog.query.all()
        data = [log.notify_key for log in logs]
        logger.debug(f"Found {len(logs)} notification log entries")

        with open(os.path.join(DATA_DIR, 'notified.json'), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.debug(f"Notification log exported: {len(data)} entries")
        return len(data)
    except Exception as e:
        logger.error(f"Error exporting notification log: {e}", exc_info=True)
        raise


def main():
    logger.info("Starting database export to JSON...")
    print('=' * 50)
    print(f'Database Export to JSON - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 50)

    try:
        app = create_app()
    except Exception as e:
        logger.error(f"Failed to create app: {e}", exc_info=True)
        print(f"Error: {e}")
        sys.exit(1)

    with app.app_context():
        try:
            logger.debug("Executing WAL checkpoint...")
            db.session.execute(db.text("PRAGMA wal_checkpoint(TRUNCATE)"))
        except Exception as e:
            logger.warning(f"WAL checkpoint warning (not critical): {e}")
            print(f"  WAL checkpoint warning (nije kritično): {e}")

        # Ensure data directory exists
        os.makedirs(DATA_DIR, exist_ok=True)
        logger.debug(f"Data directory ensured: {DATA_DIR}")

        print('\nExporting orders...')
        new_count, delivery_count, realized_count = export_orders()
        print(f'  new_ord.json: {new_count} orders')
        print(f'  for_delivery.json: {delivery_count} orders')
        print(f'  realized.json: {realized_count} orders')

        print('\nExporting lager...')
        lager_count = export_lager()
        print(f'  lager.json: {lager_count} items')

        print('\nExporting email config...')
        email_exported = export_email_config()
        if email_exported:
            print('  email_config.json: exported')
        else:
            print('  email_config.json: no config found')

        print('\nExporting notification log...')
        notif_count = export_notifications()
        print(f'  notified.json: {notif_count} entries')

        print('\n' + '=' * 50)
        print('Export complete!')
        print(f'  Total orders: {new_count + delivery_count + realized_count}')
        print(f'  Lager items: {lager_count}')
        print(f'  Location: {DATA_DIR}')
        print('=' * 50)
        
        logger.info(f"Export completed successfully: {new_count + delivery_count + realized_count} orders, {lager_count} lager items")


if __name__ == '__main__':
    main()
