"""
Auth Blueprint - Autentifikacija korisnika
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User
from datetime import datetime
import secrets
import string
from blueprints.email_notify import get_email_config, send_email

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def landing():
    """Landing page - prikazuje se ako korisnik nije ulogovan"""
    if current_user.is_authenticated:
        return redirect(url_for('orders.dashboard'))
    return render_template('landing.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login stranica"""
    if current_user.is_authenticated:
        # Check if user needs to change password
        if current_user.password_change_required:
            return redirect(url_for('auth.change_password_required'))
        return redirect(url_for('orders.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=True)
            
            # Check if password change is required
            if user.password_change_required:
                return redirect(url_for('auth.change_password_required'))
            
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('orders.dashboard'))
        else:
            flash('Pogrešno korisničko ime ili lozinka!', 'error')
    
    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Logout korisnika"""
    logout_user()
    return redirect(url_for('auth.landing'))


@auth_bp.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    """Registracija novog korisnika - samo admin može"""
    if not current_user.is_admin:
        flash('Samo administrator može kreirati nove korisnike!', 'error')
        return redirect(url_for('orders.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        
        # Validacija
        if not username or not email:
            flash('Korisničko ime i email su obavezni!', 'error')
            return render_template('register.html')
        
        # Provera da li korisnik već postoji
        if User.query.filter_by(username=username).first():
            flash('Korisničko ime već postoji!', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email već postoji!', 'error')
            return render_template('register.html')
        
        # Generiši random lozinku od 8 karaktera
        password = generate_random_password(8)
        
        # Kreiraj novog korisnika
        user = User(
            username=username,
            email=email,
            password_change_required=True,  # Mora promeniti lozinku
            created_at=datetime.now().isoformat()
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Pošalji email novom korisniku sa pristupnim podacima
        email_sent = send_new_user_email(username, email, password)
        
        if email_sent:
            flash(f'Korisnik {username} kreiran! Email sa pristupnim podacima je poslat na {email}', 'success')
        else:
            flash(f'Korisnik {username} kreiran! Privremena lozinka: {password} (Email nije poslat - proverite konfiguraciju)', 'warning')
        
        return redirect(url_for('auth.register'))
    
    return render_template('register.html')


@auth_bp.route('/change-password-required', methods=['GET', 'POST'])
@login_required
def change_password_required():
    """Obavezna promena lozinke nakon prve prijave"""
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validacija
        if not old_password or not new_password or not confirm_password:
            flash('Sva polja su obavezna!', 'error')
            return render_template('change_password_required.html')
        
        if not current_user.check_password(old_password):
            flash('Sadašnja lozinka je pogešna!', 'error')
            return render_template('change_password_required.html')
        
        if new_password != confirm_password:
            flash('Nove lozinke se ne podudaraju!', 'error')
            return render_template('change_password_required.html')
        
        if len(new_password) < 6:
            flash('Nova lozinka mora imati najmanje 6 karaktera!', 'error')
            return render_template('change_password_required.html')
        
        # Promeni lozinku
        current_user.set_password(new_password)
        current_user.password_change_required = False
        db.session.commit()
        
        flash('Lozinka uspešno promenjena! Sada možete nastaviti sa radom.', 'success')
        return redirect(url_for('orders.dashboard'))
    
    return render_template('change_password_required.html')


def generate_random_password(length=8):
    """Generiši random lozinku sa malim i velikim slovima i brojevima"""
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))


def send_new_user_email(username, email, password):
    """Pošalji email novom korisniku sa pristupnim podacima"""
    config = get_email_config()
    
    # Ako email nije omogućen ili nema konfiguracije, preskoči slanje
    if not config.enabled or not config.sender_email or not config.app_password:
        return False
    
    subject = '🔐 Dobrodošli u Latice sa Pričom ERP - Pristupni podaci'
    
    body = f'''
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9; border-radius: 10px; }}
            .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background-color: white; padding: 30px; border-radius: 0 0 10px 10px; }}
            .credentials {{ background-color: #e8f5e9; padding: 15px; border-left: 4px solid #4CAF50; margin: 20px 0; }}
            .credentials strong {{ color: #2e7d32; }}
            .warning {{ background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 20px 0; }}
            .footer {{ text-align: center; margin-top: 20px; color: #888; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎉 Dobrodošli!</h1>
            </div>
            <div class="content">
                <p>Poštovani/a,</p>
                <p>Vaš nalog u <strong>Latice sa Pričom ERP</strong> sistemu je uspešno kreiran.</p>
                
                <div class="credentials">
                    <h3>📧 Vaši pristupni podaci:</h3>
                    <p><strong>Korisničko ime:</strong> {username}</p>
                    <p><strong>Email:</strong> {email}</p>
                    <p><strong>Privremena lozinka:</strong> {password}</p>
                </div>
                
                <div class="warning">
                    <h4>⚠️ Važno!</h4>
                    <p>Pri prvom prijavljivanju biće potrebno da promenite privremenu lozinku. 
                    Molimo vas da čuvate ove pristupne podatke na sigurnom mestu.</p>
                </div>
                
                <p>Možete se prijaviti na sistem i početi sa radom.</p>
                <p>Srdačan pozdrav,<br>
                <strong>Latice sa Pričom ERP Tim</strong></p>
                
                <div class="footer">
                    <p>Ovo je automatska poruka. Molimo vas da ne odgovarate na ovaj email.</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''
    
    # Privremeno promeni receiver_email da šalje novom korisniku
    original_receiver = config.receiver_email
    config.receiver_email = email
    
    success = send_email(subject, body, config)
    
    # Vrati originalni receiver
    config.receiver_email = original_receiver
    
    return success


@auth_bp.route('/api/user/profile')
@login_required
def user_profile():
    """API endpoint za user profile"""
    return jsonify(current_user.to_dict())
