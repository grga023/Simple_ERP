from flask import Blueprint, jsonify, request, render_template, current_app
from flask_login import login_required
import json
import os

config_bp = Blueprint('config', __name__, url_prefix='/config')

def get_config_path():
    return os.path.join(current_app.config.get('DATA_DIR', 'data'), 'config.json')

def load_config():
    config_file = get_config_path()
    if os.path.exists(config_file):
        with open(config_file) as f:
            return json.load(f)
    return {}

def save_config(data):
    config_file = get_config_path()
    with open(config_file, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

@config_bp.route('/')
@login_required
def config_page():
    """Config stranica"""
    config = load_config()
    return render_template('settings.html', config=config)

@config_bp.route('/api/config', methods=['GET'])
@login_required
def api_get_config():
    return jsonify(load_config())

@config_bp.route('/api/config', methods=['POST'])
@login_required
def api_save_config():
    data = request.get_json()
    save_config(data)
    return jsonify({'status': 'ok', 'message': 'Konfiguracija sačuvana'})

@config_bp.route('/api/config/branding', methods=['POST'])
@login_required
def upload_branding():
    """Upload logo/favicon"""
    if 'file' not in request.files:
        return jsonify({'error': 'Nema fajla'}), 400
    
    file = request.files['file']
    file_type = request.form.get('type', 'logo')  # logo, logoSmall, favicon
    
    if file.filename == '':
        return jsonify({'error': 'Nije izabran fajl'}), 400
    
    # Sačuvaj fajl
    branding_dir = os.path.join(current_app.config.get('IMAGES_DIR', 'images'), 'branding')
    os.makedirs(branding_dir, exist_ok=True)
    
    filename_map = {
        'logo': 'logo.png',
        'logoSmall': 'logo-small.png',
        'favicon': 'favicon.ico'
    }
    
    filename = filename_map.get(file_type, 'logo.png')
    filepath = os.path.join(branding_dir, filename)
    file.save(filepath)
    
    return jsonify({'status': 'ok', 'path': f'/images/branding/{filename}'})
