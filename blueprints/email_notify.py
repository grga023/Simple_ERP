from flask import Blueprint, request, jsonify
from flask_login import login_required
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from models import db, Order, EmailConfig, NotificationLog

email_bp = Blueprint('email', __name__)


# ─── Helper Functions ──────────────────────────────────────────

def get_email_config():
    """Get or create the singleton email config row."""
    config = EmailConfig.query.first()
    if not config:
        config = EmailConfig(
            enabled=False,
            sender_email='',
            app_password='',
            receiver_email='',
            days_before=2
        )
        db.session.add(config)
        db.session.commit()
    return config


def send_email(subject, body, config):
    """Send an HTML email via Gmail SMTP."""
    try:
        recipients = [e.strip() for e in config.receiver_email.split(',') if e.strip()]
        msg = MIMEMultipart()
        msg['From'] = config.sender_email
        msg['To'] = ', '.join(recipients)
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(config.sender_email, config.app_password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f'[EMAIL ERROR] {e}')
        return False


def check_and_notify():
    """Check all new + for_delivery orders and send email if date is within N days."""
    config = get_email_config()
    if not config.enabled:
        return

    days_before = config.days_before
    today = datetime.now().date()
    target_date = today + timedelta(days=days_before)

    orders = Order.query.filter(Order.status.in_(['new', 'for_delivery'])).all()

    alerts = []
    for order in orders:
        if not order.date:
            continue
        try:
            order_date = datetime.strptime(order.date, '%d.%m.%Y').date()
        except ValueError:
            continue

        notify_key = f"{order.id}_{order.date}"
        existing = NotificationLog.query.filter_by(notify_key=notify_key).first()

        if today <= order_date <= target_date and not existing:
            alerts.append(order)
            db.session.add(NotificationLog(notify_key=notify_key))

    if alerts:
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


def notification_scheduler(app):
    """Background thread that checks every ~23 hours."""
    while True:
        try:
            with app.app_context():
                check_and_notify()
        except Exception as e:
            print(f'[SCHEDULER ERROR] {e}')
        time.sleep(3600 * 23)


# ─── Page Route ────────────────────────────────────────────────
# Settings page has been moved to config_bp and settings.html


@email_bp.route('/api/email_config', methods=['GET'])
@login_required
def get_config():
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
    config = get_email_config()
    config.enabled = data.get('enabled', config.enabled)
    config.sender_email = data.get('sender_email', config.sender_email)
    config.receiver_email = data.get('receiver_email', config.receiver_email)
    config.days_before = int(data.get('days_before', config.days_before))
    if data.get('app_password'):
        config.app_password = data['app_password']
    db.session.commit()
    return jsonify({'ok': True})


@email_bp.route('/api/test_email', methods=['POST'])
@login_required
def test_email_route():
    config = get_email_config()
    if not config.sender_email or not config.app_password or not config.receiver_email:
        return jsonify({'ok': False, 'error': 'Email konfiguracija nije kompletna.'}), 400
    success = send_email(
        '\u2705 Test - Latice sa pri\u010dom ERP',
        '<h2>Test notifikacija</h2><p>Email notifikacije su uspe\u0161no konfigurisane!</p>',
        config
    )
    return jsonify({'ok': success})


@email_bp.route('/api/check_notifications', methods=['POST'])
@login_required
def trigger_check():
    check_and_notify()
    return jsonify({'ok': True})
