#!/usr/bin/env python3
"""
Latice sa pričom ERP - Flask Application
"""

import os
import sys
import logging
import json
import threading
import sqlite3
import argparse
from logging.handlers import RotatingFileHandler
from flask import Flask, jsonify, send_from_directory
from flask_login import LoginManager
import flask.cli
from models import db, User
from blueprints.orders import orders_bp
from blueprints.lager import lager_bp
from blueprints.email_notify import email_bp, notification_scheduler
from blueprints.config import config_bp
from blueprints.auth import auth_bp


def load_erp_config():
    """Učitaj konfiguraciju iz .erp.conf"""
    config = {}
    config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.erp.conf')
    if os.path.exists(config_file):
        with open(config_file) as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    config[key] = value
    return config


def configure_logging(app, level):
    """Configure logging to journald (stdout/stderr) and to a file."""
    log_dir = os.path.join(app.config.get('DATA_DIR', 'data'), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'erp.log')

    formatter = logging.Formatter('%(asctime)s %(levelname)s [%(name)s] %(message)s')

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=5)
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
    root_logger.addHandler(stream_handler)
    root_logger.addHandler(file_handler)

    app.logger.handlers = []
    app.logger.propagate = True

    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.handlers = []
    werkzeug_logger.propagate = False
    werkzeug_logger.setLevel(logging.CRITICAL)


def create_app():
    """Application factory pattern."""
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    IMAGES_DIR = os.path.join(BASE_DIR, 'images')

    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(IMAGES_DIR, exist_ok=True)

    app = Flask(
        __name__,
        static_folder='static',
        template_folder='templates'
    )

    # ─── Configuration ─────────────────────────────────────────
    db_file = os.path.join(DATA_DIR, 'erp.db')
    
    def get_sqlite_connection():
        conn = sqlite3.connect(db_file, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=OFF")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA cache_size=-32000")
        return conn
    
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_file}"
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'creator': get_sqlite_connection
    }
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['IMAGES_DIR'] = IMAGES_DIR
    app.config['DATA_DIR'] = DATA_DIR
    app.config['SECRET_KEY'] = 'latice-sa-pricom-erp-secret'

    # ─── Initialize Extensions ─────────────────────────────────
    db.init_app(app)
    
    # Flask-Login setup
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Morate biti ulogovani da biste pristupili ovoj stranici.'
    login_manager.login_message_category = 'error'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    with app.app_context():
        db.create_all()

    @app.context_processor
    def inject_config():
        config_file = os.path.join(DATA_DIR, 'config.json')
        config = {}
        if os.path.exists(config_file):
            try:
                with open(config_file) as f:
                    config = json.load(f)
            except:
                pass
        return {'config': config}

    # ─── Register Blueprints ───────────────────────────────────
    # Auth blueprint must be first (handles landing page at '/')
    app.register_blueprint(auth_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(lager_bp)
    app.register_blueprint(email_bp)
    app.register_blueprint(config_bp)

    # ─── Serve Uploaded Images ─────────────────────────────────
    @app.route('/images/<path:filename>')
    def serve_image(filename):
        return send_from_directory(IMAGES_DIR, filename)

    # ─── Central Error Handlers ────────────────────────────────
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({'error': 'Neispravan zahtev', 'status': 400}), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Resurs nije pronađen', 'status': 404}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({'error': 'Metoda nije dozvoljena', 'status': 405}), 405

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({'error': 'Greška na serveru', 'status': 500}), 500

    # ─── Health Check ─────────────────────────────────────────
    @app.route('/health')
    def health_check():
        """Health check endpoint"""
        return jsonify({'status': 'healthy','version': '1.0.0','database': 'connected'})

    return app


def main():
    parser = argparse.ArgumentParser(description='ERP Latice sa Pričom Server')
    parser.add_argument('-p', '--port', type=int, default=None, help='Port (default: 8000)')
    parser.add_argument('-H', '--host', type=str, default='0.0.0.0', help='Host (default: 0.0.0.0)')
    parser.add_argument('-d', '--debug', action='store_true', help='Debug mode')
    args = parser.parse_args()

    # Učitaj config
    erp_config = load_erp_config()
    
    # Prioritet: CLI argument > config fajl > default
    port = args.port or int(erp_config.get('PORT', 8000))
    host = args.host or erp_config.get('HOST', '0.0.0.0')
    debug = args.debug or erp_config.get('DEBUG', 'false').lower() == 'true'

    app = create_app()
    configure_logging(app, logging.DEBUG if debug else logging.INFO)

    flask.cli.show_server_banner = lambda *args, **kwargs: None

    t = threading.Thread(target=notification_scheduler, args=(app,), daemon=True)
    t.start()

    app.logger.info("Starting ERP server on %s:%s", host, port)
    app.run(host=host, port=port, debug=debug, use_reloader=False)


if __name__ == '__main__':
    main()
