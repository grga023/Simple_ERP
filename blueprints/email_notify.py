from flask import Blueprint, request, jsonify
import logging
from flask_login import login_required
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from models import db, Order, EmailConfig, NotificationLog

email_bp = Blueprint('email', __name__)
logger = logging.getLogger(__name__)


# ─── Helper Functions ──────────────────────────────────────────

def get_email_config():
    """Get or create the singleton email config row."""
    logger.debug("Fetching email configuration")
    config = EmailConfig.query.first()
    if not config:
        logger.info("Email config not found, creating default config")
        config = EmailConfig(
            enabled=False,
            sender_email='',
            app_password='',
            receiver_email='',
            days_before=2
        )
        db.session.add(config)
        db.session.commit()
        logger.info("Default email config created")
    return config


def send_email(subject, body, config):
    """Send an HTML email via Gmail SMTP."""
    logger.info(f"Sending email: {subject}")
    try:
        recipients = [e.strip() for e in config.receiver_email.split(',') if e.strip()]
        logger.debug(f"Email recipients: {recipients}")
        
        msg = MIMEMultipart()
        msg['From'] = config.sender_email
        msg['To'] = ', '.join(recipients)
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))
        
        logger.debug("Connecting to Gmail SMTP server...")
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            logger.debug(f"Authenticating as {config.sender_email}")
            server.login(config.sender_email, config.app_password)
            server.send_message(msg)
        
        logger.info(f"Email sent successfully to {len(recipients)} recipient(s)")
        return True
    except Exception as e:
        logger.exception(f"Email send failed: {e}")
        return False


def check_and_notify():
    """Check all new + for_delivery orders and send email if date is within N days."""
    logger.debug("Starting notification check...")
    config = get_email_config()
    if not config.enabled:
        logger.debug("Email notifications disabled, skipping check")
        return

    days_before = config.days_before
    today = datetime.now().date()
    target_date = today + timedelta(days=days_before)
    
    logger.info(f"Checking orders for notification: days_before={days_before}, target_date={target_date}")

    orders = Order.query.filter(Order.status.in_(['new', 'for_delivery'])).all()
    logger.debug(f"Found {len(orders)} orders with status 'new' or 'for_delivery'")

    alerts = []
    for order in orders:
        if not order.date:
            continue
        try:
            order_date = datetime.strptime(order.date, '%d.%m.%Y').date()
        except ValueError:
            logger.warning(f"Invalid date format for order {order.id}: {order.date}")
            continue

        notify_key = f"{order.id}_{order.date}"
        existing = NotificationLog.query.filter_by(notify_key=notify_key).first()

        if today <= order_date <= target_date and not existing:
            alerts.append(order)
            db.session.add(NotificationLog(notify_key=notify_key))
            logger.debug(f"Order {order.id} ({order.name}) added to alerts")

    if alerts:
        logger.info(f"Sending notification for {len(alerts)} order(s)")
        body = '<h2>\u26A0\uFE0F Porud\u017ebine sa pribli\u017eavaju\u0107im datumom!</h2>'
        body += f'<p>Slede\u0107e porud\u017ebine imaju rok u narednih {days_before} dana:</p>'
        body += '<table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse;">'
        body += '<tr style="background:#f0f0f0;"><th>Naziv</th><th>Kupac</th><th>Datum</th><th>Cena</th><th>Opis</th></tr>'
        for o in alerts:
            description = (o.description or '').replace('\r\n', '<br>').replace('\n', '<br>')
            body += f"<tr><td>{o.name}</td><td>{o.customer}</td>"
            body += f"<td><strong>{o.date}</strong></td><td>{o.price}</td>"
            body += f"<td>{opis}</td></tr>"
        body += '</table>'
        body += '<br><p style="color:#888;">Latice sa pri\u010dom ERP - automatska notifikacija</p>'

        send_email(
            f'\u26A0\uFE0F {len(alerts)} porud\u017ebin(a) - rok uskoro!',
            body, config
        )
        db.session.commit()
        logger.info(f"Notification email sent for {len(alerts)} order(s)")
    else:
        logger.debug("No orders to notify")

def notification_scheduler(app):
    """Background thread that checks every ~23 hours."""
    logger.info("Notification scheduler thread started")
    while True:
        try:
            logger.debug("Scheduler running notification check...")
            with app.app_context():
                check_and_notify()
            logger.debug("Scheduler check completed, sleeping for 23 hours")
        except Exception as e:
            logger.exception(f"Scheduler error: {e}")
        time.sleep(3600 * 23)


# ─── Page Route ────────────────────────────────────────────────
# Settings page has been moved to config_bp and settings.html


@email_bp.route('/api/email_config', methods=['GET'])
@login_required
def get_config():
    logger.debug("Fetching email configuration via API")
    config = get_email_config()
    return jsonify({
        'enabled': config.enabled,
        'sender_email': config.sender_email,
        'receiver_email': config.receiver_email,
        'days_before': config.days_before,
        'has_password': bool(config.app_password)
    })


@email_bp.route('/api/email_config', methods=['POST'])
@login_required
def save_config():
    data = request.get_json()
    logger.info("Updating email configuration")
    
    config = get_email_config()
    config.enabled = data.get('enabled', config.enabled)
    config.sender_email = data.get('sender_email', config.sender_email)
    config.receiver_email = data.get('receiver_email', config.receiver_email)
    config.days_before = int(data.get('days_before', config.days_before))
    
    if data.get('app_password'):
        logger.debug("Email app password updated")
        config.app_password = data['app_password']
    
    db.session.commit()
    logger.info(f"Email config saved: enabled={config.enabled}, sender={config.sender_email}")
    return jsonify({'ok': True})


@email_bp.route('/api/test_email', methods=['POST'])
@login_required
def test_email_route():
    logger.info("Test email requested")
    config = get_email_config()
    if not config.sender_email or not config.app_password or not config.receiver_email:
        logger.warning("Test email failed: incomplete email configuration")
        return jsonify({'ok': False, 'error': 'Email konfiguracija nije kompletna.'}), 400
    
    success = send_email(
        '✅ Test - Latice sa pričom ERP',
        '<h2>Test notifikacija</h2><p>Email notifikacije su uspešno konfigurisane!</p>',
        config
    )
    
    if success:
        logger.info("Test email sent successfully")
    else:
        logger.error("Test email failed")
    
    return jsonify({'ok': success})


@email_bp.route('/api/check_notifications', methods=['POST'])
@login_required
def trigger_check():
    logger.info("Manual notification check triggered")
    check_and_notify()
    logger.info("Manual notification check completed")
    return jsonify({'ok': True})
