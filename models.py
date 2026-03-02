from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import logging

db = SQLAlchemy()
logger = logging.getLogger(__name__)


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    password_change_required = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.String(50), default='')

    def set_password(self, password):
        logger.debug(f"Setting password for user: {self.username}")
        self.password_hash = generate_password_hash(password)
        logger.debug(f"Password updated for user: {self.username}")

    def check_password(self, password):
        result = check_password_hash(self.password_hash, password)
        if result:
            logger.debug(f"Password check successful for user: {self.username}")
        else:
            logger.warning(f"Password check failed for user: {self.username}")
        return result

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_admin': self.is_admin,
            'created_at': self.created_at
        }


class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False, default=0)
    paid = db.Column(db.Boolean, default=False)
    customer = db.Column(db.String(200), nullable=False)
    date = db.Column(db.String(20), default='')
    quantity = db.Column(db.Integer, default=1)
    color = db.Column(db.String(100), default='')
    description = db.Column(db.Text, default='')
    image = db.Column(db.String(300), default='')
    status = db.Column(db.String(20), nullable=False, default='new')
    lager_id = db.Column(db.Integer, db.ForeignKey('lager.id'), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'paid': self.paid,
            'customer': self.customer,
            'date': self.date,
            'quantity': self.quantity,
            'color': self.color,
            'description': self.description,
            'image': self.image,
            'status': self.status,
            'lager_id': self.lager_id
        }


class LagerItem(db.Model):
    __tablename__ = 'lager'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, default=0)
    color = db.Column(db.String(100), default='')
    quantity = db.Column(db.Integer, default=0)
    location = db.Column(db.String(100), default='House')
    image = db.Column(db.String(300), default='')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'color': self.color,
            'quantity': self.quantity,
            'location': self.location,
            'image': self.image
        }


class EmailConfig(db.Model):
    __tablename__ = 'email_config'

    id = db.Column(db.Integer, primary_key=True)
    enabled = db.Column(db.Boolean, default=False)
    sender_email = db.Column(db.String(200), default='')
    app_password = db.Column(db.String(200), default='')
    receiver_email = db.Column(db.String(500), default='')
    days_before = db.Column(db.Integer, default=2)


class NotificationLog(db.Model):
    __tablename__ = 'notification_log'

    id = db.Column(db.Integer, primary_key=True)
    notify_key = db.Column(db.String(200), unique=True, nullable=False)
