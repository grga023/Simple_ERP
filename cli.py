#!/usr/bin/env python3
"""
ERP Latice sa Pričom - CLI Interface
"""

import sys
import os
import subprocess
import argparse
import logging
from pathlib import Path

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] - [%(name)s] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Učitaj konfiguraciju
SCRIPT_DIR = Path(__file__).parent.resolve()
CONFIG_FILE = SCRIPT_DIR / ".erp.conf"

def load_config():
    config = {}
    if CONFIG_FILE.exists():
        logger.debug(f"Loading config from {CONFIG_FILE}")
        try:
            with open(CONFIG_FILE) as f:
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        config[key] = value
            logger.info(f"Configuration loaded: {len(config)} entries")
        except Exception as e:
            logger.error(f"Error loading config: {e}", exc_info=True)
            raise
    else:
        logger.warning(f"Config file not found: {CONFIG_FILE}")
    return config

CONFIG = load_config()

def cmd_start(args):
    """Pokreni aplikaciju"""
    logger.info("Starting ERP application...")
    if args.foreground:
        logger.info("Running in foreground mode")
        # Pokreni direktno u terminalu
        main_script = SCRIPT_DIR / "ERP_server.py"
        venv_python = SCRIPT_DIR / "venv" / "bin" / "python"
        
        if not venv_python.exists():
            logger.error(f"Venv Python not found: {venv_python}")
            print(f"GREŠKA: Venv Python nije pronađen: {venv_python}")
            sys.exit(1)
        
        if main_script.exists():
            logger.info(f"Executing: {venv_python} {main_script}")
            os.execv(str(venv_python), [str(venv_python), str(main_script)] + args.extra)
        else:
            logger.error(f"Main script not found: {main_script}")
            print(f"GREŠKA: Glavni skript nije pronađen: {main_script}")
            sys.exit(1)
    else:
        logger.info("Starting ERP as systemd service")
        # Pokreni kao servis
        result = subprocess.run(["sudo", "systemctl", "start", "erp"])
        if result.returncode == 0:
            logger.info("ERP service started successfully")
            print("ERP servis pokrenut.")
        else:
            logger.error(f"Failed to start ERP service: exit code {result.returncode}")
        cmd_status(args)

def cmd_stop(args):
    """Zaustavi servis"""
    logger.info("Stopping ERP service...")
    result = subprocess.run(["sudo", "systemctl", "stop", "erp"])
    if result.returncode == 0:
        logger.info("ERP service stopped successfully")
        print("ERP servis zaustavljen.")
    else:
        logger.error(f"Failed to stop ERP service: exit code {result.returncode}")

def cmd_restart(args):
    """Restartuj servis"""
    logger.info("Restarting ERP service...")
    result = subprocess.run(["sudo", "systemctl", "restart", "erp"])
    if result.returncode == 0:
        logger.info("ERP service restarted successfully")
        print("ERP servis restartovan.")
    else:
        logger.error(f"Failed to restart ERP service: exit code {result.returncode}")

def cmd_status(args):
    """Proveri status aplikacije"""
    logger.debug("Checking ERP status...")
    print("ERP Latice sa Pričom - Status")
    print("=" * 40)
    print(f"Instalacija: {CONFIG.get('INSTALL_DIR', 'N/A')}")
    print(f"Data dir:    {CONFIG.get('DATA_DIR', 'N/A')}")
    print(f"Img dir:     {CONFIG.get('IMG_DIR', 'N/A')}")
    print(f"Verzija:     {CONFIG.get('VERSION', 'N/A')}")
    
    # Proveri symlinkove
    data_link = SCRIPT_DIR / "data"
    img_link = SCRIPT_DIR / "images"
    
    print(f"\nSymlinkovi:")
    print(f"  data: {'✓ OK' if data_link.is_symlink() else '✗ NEDOSTAJE'}")
    print(f"  img:  {'✓ OK' if img_link.is_symlink() else '✗ NEDOSTAJE'}")
    
    if not data_link.is_symlink():
        logger.warning("Data symlink is missing")
    if not img_link.is_symlink():
        logger.warning("Images symlink is missing")
    
    # Proveri servis status
    print(f"\nServis status:")
    subprocess.run(["systemctl", "status", "erp", "--no-pager", "-l"])

def cmd_logs(args):
    """Prikaži logove"""
    logger.debug(f"Viewing logs: service={args.service}, lines={args.lines}, follow={args.follow}")
    if args.service:
        # Systemd journal logovi
        cmd = ["sudo", "journalctl", "-u", "erp", "-n", str(args.lines)]
        if args.follow:
            cmd.append("-f")
        logger.info(f"Viewing systemd logs: {' '.join(cmd)}")
        subprocess.run(cmd)
    else:
        # Aplikacijski logovi
        log_file = Path(CONFIG.get('DATA_DIR', '')) / "logs" / "erp.log"
        logger.debug(f"Log file path: {log_file}")
        if log_file.exists():
            if args.follow:
                logger.info(f"Following log file: {log_file}")
                subprocess.run(["tail", "-f", str(log_file)])
            else:
                logger.info(f"Viewing last {args.lines} lines of log file")
                subprocess.run(["tail", "-n", str(args.lines), str(log_file)])
        else:
            logger.error(f"Log file not found: {log_file}")
            print("Log fajl ne postoji.")

def cmd_config(args):
    """Prikaži ili izmeni konfiguraciju"""
    if args.show:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE) as f:
                print(f.read())
        else:
            print("Config fajl ne postoji.")
    elif args.edit:
        editor = os.environ.get('EDITOR', 'nano')
        subprocess.run([editor, str(CONFIG_FILE)])
    else:
        # Default: prikaži status
        print("ERP Konfiguracija:")
        print("=" * 40)
        for key, value in CONFIG.items():
            print(f"  {key}: {value}")
        print("\nKoristi --show za sirovi config ili --edit za editovanje.")

def cmd_enable(args):
    """Uključi autostart"""
    subprocess.run(["sudo", "systemctl", "enable", "erp"])
    print("Autostart uključen.")

def cmd_disable(args):
    """Isključi autostart"""
    subprocess.run(["sudo", "systemctl", "disable", "erp"])
    print("Autostart isključen.")

def cmd_uninstall(args):
    """Deinstaliraj aplikaciju"""
    logger.warning("Uninstall initiated")
    print("ERP Latice - Deinstalacija")
    print("=" * 40)
    print(f"Instalacija: {CONFIG.get('INSTALL_DIR', 'N/A')}")
    print(f"Data dir:    {CONFIG.get('DATA_DIR', 'N/A')} (NEĆE biti obrisano)")
    print(f"Img dir:     {CONFIG.get('IMG_DIR', 'N/A')} (NEĆE biti obrisano)")
    print("")
    
    confirm = input("Da li ste sigurni da želite da deinstalirate? [y/N]: ")
    if confirm.lower() == 'y':
        logger.info("Starting uninstallation process...")
        print("\nDeinstalacija u toku...")
        
        # Zaustavi servis
        print("  - Zaustavljanje servisa...")
        logger.info("Stopping ERP service...")
        subprocess.run(["sudo", "systemctl", "stop", "erp"], stderr=subprocess.DEVNULL)
        subprocess.run(["sudo", "systemctl", "disable", "erp"], stderr=subprocess.DEVNULL)
        logger.info("Service stopped and disabled")
        
        # Obriši servis fajl
        print("  - Brisanje servis fajla...")
        logger.info("Removing systemd service file...")
        subprocess.run(["sudo", "rm", "-f", "/etc/systemd/system/erp.service"])
        subprocess.run(["sudo", "systemctl", "daemon-reload"])
        logger.info("Service file removed")
        
        # Obriši CLI komandu
        print("  - Brisanje 'erp' komande...")
        logger.info("Removing CLI command...")
        subprocess.run(["sudo", "rm", "-f", "/usr/local/bin/erp"])
        logger.info("CLI command removed")
        
        # Obriši instalaciju
        install_dir = CONFIG.get('INSTALL_DIR', '')
        if install_dir and os.path.exists(install_dir):
            print(f"  - Brisanje instalacije: {install_dir}")
            logger.info(f"Removing installation directory: {install_dir}")
            subprocess.run(["sudo", "rm", "-rf", install_dir])
            logger.info("Installation directory removed")
        
        logger.info("Uninstallation completed successfully")
        print("\n✓ Deinstalacija završena.")
        print(f"  Data i img folderi su sačuvani.")
    else:
        logger.info("Uninstallation cancelled by user")
        print("Deinstalacija otkazana.")

def cmd_port(args):
    """Promeni port"""
    new_port = args.port
    
    if not new_port:
        # Samo prikaži trenutni port
        current_port = CONFIG.get('PORT', '8000')
        logger.info(f"Current port: {current_port}")
        print(f"Trenutni port: {current_port}")
        return
    
    logger.info(f"Changing port to: {new_port}")
    
    # Validiraj port
    try:
        port_int = int(new_port)
        if port_int < 1 or port_int > 65535:
            raise ValueError
    except ValueError:
        logger.error(f"Invalid port number: {new_port}")
        print(f"GREŠKA: Nevažeći port: {new_port}")
        sys.exit(1)
    
    # Ažuriraj config fajl
    logger.debug(f"Updating config file: {CONFIG_FILE}")
    config_lines = []
    port_found = False
    
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            for line in f:
                if line.startswith('PORT='):
                    config_lines.append(f'PORT={new_port}\n')
                    port_found = True
                else:
                    config_lines.append(line)
    
    if not port_found:
        config_lines.append(f'PORT={new_port}\n')
    
    # Snimi config
    with open(CONFIG_FILE, 'w') as f:
        f.writelines(config_lines)
    
    logger.info(f"Port updated in config file: {new_port}")
    print(f"Port promenjen na: {new_port}")
    
    # Ažuriraj systemd servis
    logger.info("Updating systemd service file...")
    print("Ažuriranje systemd servisa...")
    
    service_file = "/etc/systemd/system/erp.service"
    subprocess.run([
        "sudo", "sed", "-i", 
        f"s/--port [0-9]*/--port {new_port}/g",
        service_file
    ])
    
    subprocess.run(["sudo", "systemctl", "daemon-reload"])
    logger.info("Systemd daemon reloaded")
    
    # Pitaj za restart
    restart = input("Restartovati servis sada? [Y/n]: ").strip()
    if restart.lower() != 'n':
        logger.info("Restarting service with new port...")
        subprocess.run(["sudo", "systemctl", "restart", "erp"])
        print("Servis restartovan.")
        logger.info("Service restarted successfully")
    else:
        logger.info("Service restart deferred")
        print("Restartuj servis ručno sa: erp restart")

def cmd_backup(args):
    """Pokreni backup ručno"""
    logger.info("Starting manual backup...")
    backup_script = SCRIPT_DIR / "backup.sh"
    
    if not backup_script.exists():
        logger.error(f"Backup script not found: {backup_script}")
        print(f"GREŠKA: Backup skripta nije pronađena: {backup_script}")
        sys.exit(1)
    
    print("Pokretanje backup-a...")
    print(f"  INSTALL_DIR: {CONFIG.get('INSTALL_DIR', 'N/A')}")
    print(f"  DATA_DIR:    {CONFIG.get('DATA_DIR', 'N/A')}")
    print("")
    
    logger.debug(f"Running backup script: {backup_script}")
    if args.verbose:
        result = subprocess.run(["bash", str(backup_script)])
    else:
        result = subprocess.run(["bash", str(backup_script)], capture_output=True)
    
    if result.returncode == 0:
        logger.info("Backup completed successfully")
        print("✓ Backup uspešno završen.")
        log_file = Path(CONFIG.get('DATA_DIR', '')) / "logs" / "backup.log"
        print(f"  Log: {log_file}")
    else:
        logger.error(f"Backup failed with exit code: {result.returncode}")
        print("✗ Backup nije uspeo.")
        if not args.verbose:
            print("Pokreni sa -v za više detalja.")
            # Prikaži error ako postoji
            if result.stderr:
                error_msg = result.stderr.decode()
                logger.error(f"Backup stderr: {error_msg}")
                print(f"\nGreška:\n{error_msg}")
        sys.exit(1)

def cmd_health(args):
    """Proveri health status servera"""
    import urllib.request
    import urllib.error
    
    port = CONFIG.get('PORT', '8000')
    url = f"http://localhost:{port}/health"
    
    logger.info(f"Checking server health at {url}")
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            logger.info("Server health check passed")
            print(f"✓ Server je ZDRAV")
            print(f"  URL: {url}")
            print(f"  Status: {response.status}")
            if args.verbose:
                response_data = response.read().decode()
                logger.debug(f"Health response: {response_data}")
                print(f"  Response: {response_data}")
    except urllib.error.URLError as e:
        logger.error(f"Server health check failed: {e.reason}")
        print(f"✗ Server nije dostupan")
        print(f"  URL: {url}")
        print(f"  Greška: {e.reason}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during health check: {e}", exc_info=True)
        print(f"✗ Greška: {e}")
        sys.exit(1)


def cmd_info(args):
    """Prikaži sve informacije o instalaciji"""
    print("ERP Latice sa Pričom - Info")
    print("=" * 50)
    print(f"\n📁 Putanje:")
    print(f"   Instalacija:  {CONFIG.get('INSTALL_DIR', 'N/A')}")
    print(f"   Data:         {CONFIG.get('DATA_DIR', 'N/A')}")
    print(f"   Slike:        {CONFIG.get('IMG_DIR', 'N/A')}")
    
    print(f"\n🌐 Server:")
    print(f"   Host:         {CONFIG.get('HOST', '0.0.0.0')}")
    print(f"   Port:         {CONFIG.get('PORT', '8000')}")
    print(f"   URL:          http://localhost:{CONFIG.get('PORT', '8000')}")
    
    print(f"\n📋 Verzija:")
    print(f"   Verzija:      {CONFIG.get('VERSION', 'N/A')}")
    print(f"   Instalirano:  {CONFIG.get('INSTALLED_DATE', 'N/A')}")
    
    # Disk usage
    data_dir = CONFIG.get('DATA_DIR', '')
    if data_dir and os.path.exists(data_dir):
        result = subprocess.run(['du', '-sh', data_dir], capture_output=True, text=True)
        if result.returncode == 0:
            size = result.stdout.split()[0]
            print(f"\n💾 Disk:")
            print(f"   Data folder:  {size}")
    
    # Cron status
    print(f"\n⏰ Backup:")
    result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
    if 'backup.sh' in result.stdout:
        print(f"   Cron:         ✓ Aktivan (3:00 AM)")
    else:
        print(f"   Cron:         ✗ Nije podešen")


def cmd_update(args):
    """Ažuriraj aplikaciju iz git-a"""
    logger.info("Starting application update...")
    install_dir = SCRIPT_DIR
    
    print("Ažuriranje ERP aplikacije...")
    
    # Proveri da li je git repo
    git_dir = install_dir / ".git"
    if not git_dir.exists():
        logger.error(f"Not a git repository: {install_dir}")
        print(f"✗ {install_dir} nije git repozitorijum.")
        print("")
        print("Opcije za ažuriranje:")
        print("  1. Ručno ažuriraj:")
        print(f"     cd /putanja/do/Simple_ERP")
        print(f"     git pull")
        print(f"     ./install.sh")
        print("")
        print("  2. Ili konvertuj instalaciju u git repo:")
        print(f"     cd {install_dir}")
        print(f"     sudo git init")
        print(f"     sudo git remote add origin https://github.com/grga023/Simple_ERP.git")
        print(f"     sudo git fetch origin")
        print(f"     sudo git reset --hard origin/master")
        sys.exit(1)
    
    # Zaustavi servis
    print("  Zaustavljanje servisa...")
    logger.info("Stopping service before update...")
    subprocess.run(["sudo", "systemctl", "stop", "erp"], stderr=subprocess.DEVNULL)
    logger.info("Service stopped")
    
    # Ako je specifikovan branch, koristi branch
    if hasattr(args, 'branch') and args.branch:
        logger.info(f"Updating to branch: {args.branch}")
        print(f"  Ažuriram na branch: {args.branch}")
        result = subprocess.run(["sudo", "git", "fetch", "origin"], cwd=str(install_dir), 
                              capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Git fetch failed: {result.stderr}")
            print(f"✗ Git fetch nije uspeo: {result.stderr}")
            subprocess.run(["sudo", "systemctl", "start", "erp"])
            sys.exit(1)
        
        result = subprocess.run(["sudo", "git", "checkout", args.branch], cwd=str(install_dir), 
                              capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Git checkout failed: {result.stderr}")
            print(f"✗ Nije moguće preći na branch {args.branch}: {result.stderr}")
            subprocess.run(["sudo", "systemctl", "start", "erp"])
            sys.exit(1)
        
        result = subprocess.run(["sudo", "git", "pull", "origin", args.branch], cwd=str(install_dir), 
                              capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Git pull failed: {result.stderr}")
            print(f"✗ Git pull nije uspeo: {result.stderr}")
            subprocess.run(["sudo", "systemctl", "start", "erp"])
            sys.exit(1)
        logger.info(f"Successfully updated to branch: {args.branch}")
        print(result.stdout)
    else:
        # Koristi stabilne tagove (default)
        logger.info("Searching for latest stable tag...")
        print("  Pronalazim najnoviji stabilni tag...")
        
        # Fetch tags
        subprocess.run(["sudo", "git", "fetch", "--tags", "origin"], cwd=str(install_dir), 
                      capture_output=True, text=True)
        
        # Dobavi trenutni tag
        result = subprocess.run(["git", "describe", "--tags", "--exact-match"], 
                              cwd=str(install_dir), capture_output=True, text=True)
        current_tag = result.stdout.strip() if result.returncode == 0 else None
        
        # Dobavi sve stabilne tagove
        result = subprocess.run(["git", "tag", "-l", "*_stabile"], cwd=str(install_dir), 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print(f"✗ Nije moguće dohvatiti tagove: {result.stderr}")
            subprocess.run(["sudo", "systemctl", "start", "erp"])
            sys.exit(1)
        
        stable_tags = sorted([t.strip() for t in result.stdout.strip().split('\n') if t.strip()])
        
        if not stable_tags:
            print("✗ Nema dostupnih stabilnih tagova (_stabile)")
            subprocess.run(["sudo", "systemctl", "start", "erp"])
            sys.exit(1)
        
        # Pronađi najnoviji tag
        latest_tag = stable_tags[-1]
        
        if current_tag:
            print(f"  Trenutna verzija: {current_tag}")
            if current_tag == latest_tag:
                print(f"✓ Već ste na najnovijoj stabilnoj verziji: {latest_tag}")
                subprocess.run(["sudo", "systemctl", "start", "erp"])
                return
        else:
            print(f"  Trenutno niste na tag-u")
        
        print(f"  Ažuriram na najnoviji stabilni tag: {latest_tag}")
        
        # Checkout na najnoviji stabilni tag
        result = subprocess.run(["sudo", "git", "checkout", latest_tag], cwd=str(install_dir), 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"✗ Checkout na {latest_tag} nije uspeo: {result.stderr}")
            subprocess.run(["sudo", "systemctl", "start", "erp"])
            sys.exit(1)
        
        print(f"✓ Prebačeno na verziju: {latest_tag}")
    
    # Ažuriraj dependencies
    print("  Ažuriranje Python paketa...")
    venv_pip = install_dir / "venv" / "bin" / "pip"
    req_file = install_dir / "requirements.txt"
    if req_file.exists():
        subprocess.run(["sudo", str(venv_pip), "install", "-r", str(req_file)], 
                      capture_output=not args.verbose)
    
    # Pokreni servis
    print("  Pokretanje servisa...")
    subprocess.run(["sudo", "systemctl", "start", "erp"])
    
    print("✓ Ažuriranje završeno.")

def cmd_db(args):
    """Database operacije"""
    data_dir = Path(CONFIG.get('DATA_DIR', ''))
    db_file = data_dir / 'erp.db'
    
    if args.action == 'info':
        if db_file.exists():
            size = db_file.stat().st_size / (1024 * 1024)  # MB
            print(f"Database: {db_file}")
            print(f"Veličina: {size:.2f} MB")
        else:
            print("Database ne postoji.")
    
    elif args.action == 'backup':
        if db_file.exists():
            backup_file = data_dir / f"erp_backup_{subprocess.run(['date', '+%Y%m%d_%H%M%S'], capture_output=True, text=True).stdout.strip()}.db"
            subprocess.run(['cp', str(db_file), str(backup_file)])
            print(f"✓ Backup kreiran: {backup_file}")
        else:
            print("Database ne postoji.")
    
    elif args.action == 'vacuum':
        print("Optimizacija baze...")
        venv_python = SCRIPT_DIR / "venv" / "bin" / "python"
        subprocess.run([
            str(venv_python), '-c',
            f"import sqlite3; c=sqlite3.connect('{db_file}'); c.execute('VACUUM'); c.close(); print('✓ VACUUM završen')"
        ])

def cmd_reset_users(args):
    """Obriši sve korisnike i kreiraj novog admina"""
    logger.warning("User reset initiated")
    confirm = input("Ovo će obrisati sve korisnike. Nastavi? [y/N]: ").strip().lower()
    if confirm != 'y':
        logger.info("User reset cancelled by user")
        print("Reset korisnika otkazan.")
        return

    try:
        logger.info("Resetting users...")
        from datetime import datetime
        import secrets
        import string
        from ERP_server import create_app
        from models import db, User

        app = create_app()
        with app.app_context():
            user_count = User.query.count()
            logger.info(f"Deleting {user_count} users from database")
            User.query.delete()
            db.session.commit()
            logger.info("All users deleted")

            username = 'admin'
            password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))

            user = User(
                username=username,
                email='admin@local',
                is_admin=True,
                password_change_required=True,
                created_at=datetime.now().isoformat()
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            logger.info(f"New admin user created: {username}")

            print("✓ Korisnici resetovani.")
            print("Admin kredencijali:")
            print(f"  Username: {username}")
            print(f"  Password: {password}")
            print("  (Lozinka mora biti promenjena pri prvoj prijavi)")
    except Exception as e:
        logger.error(f"Error resetting users: {e}", exc_info=True)
        print(f"✗ Greška: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        prog='erp',
        description='ERP Latice sa Pričom - CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
            Primeri:
            erp status          Proveri status aplikacije i servisa
            erp start           Pokreni kao systemd servis
            erp start -f        Pokreni u terminalu (foreground)
            erp stop            Zaustavi servis
            erp restart         Restartuj servis
            erp logs -f         Prati aplikacijske logove
            erp config --edit   Edituj konfiguraciju
            erp health          Proveri da li server radi
            erp backup          Ručni backup
            erp update          Ažuriraj iz git-a
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Dostupne komande')
    
    # status
    subparsers.add_parser('status', help='Proveri status')
    
    # info
    subparsers.add_parser('info', help='Prikaži sve informacije')
    
    # health
    health_parser = subparsers.add_parser('health', help='Proveri health servera')
    health_parser.add_argument('-v', '--verbose', action='store_true', help='Prikaži response')
    
    # start
    start_parser = subparsers.add_parser('start', help='Pokreni aplikaciju')
    start_parser.add_argument('-f', '--foreground', action='store_true', 
                               help='Pokreni u foreground modu (ne kao servis)')
    start_parser.add_argument('extra', nargs='*', help='Dodatni argumenti')
    
    # stop
    subparsers.add_parser('stop', help='Zaustavi servis')
    
    # restart
    subparsers.add_parser('restart', help='Restartuj servis')
    
    # logs
    logs_parser = subparsers.add_parser('logs', help='Prikaži logove')
    logs_parser.add_argument('-f', '--follow', action='store_true', help='Prati log')
    logs_parser.add_argument('-n', '--lines', type=int, default=50, help='Broj linija')
    logs_parser.add_argument('-s', '--service', action='store_true', 
                              help='Prikaži systemd journal umesto app loga')
    
    # config
    config_parser = subparsers.add_parser('config', help='Konfiguracija')
    config_parser.add_argument('--show', action='store_true', help='Prikaži config fajl')
    config_parser.add_argument('--edit', action='store_true', help='Edituj config')
    
    # port
    port_parser = subparsers.add_parser('port', help='Prikaži ili promeni port')
    port_parser.add_argument('port', nargs='?', help='Novi port (npr. 9000)')
    
    # backup
    backup_parser = subparsers.add_parser('backup', help='Pokreni backup ručno')
    backup_parser.add_argument('-v', '--verbose', action='store_true', help='Prikaži detalje')
    
    # update
    update_parser = subparsers.add_parser('update', help='Ažuriraj aplikaciju iz git-a')
    update_parser.add_argument('-v', '--verbose', action='store_true', help='Prikaži detalje')
    update_parser.add_argument('-b', '--branch', help='Specifikuj branch (default: koristi stabilne tagove)')
    
    # db
    db_parser = subparsers.add_parser('db', help='Database operacije')
    db_parser.add_argument('action', choices=['info', 'backup', 'vacuum'], 
                           help='info/backup/vacuum')

    # reset-users
    subparsers.add_parser('reset-users', help='Obriši sve korisnike i kreiraj admina')
    
    # enable/disable autostart
    subparsers.add_parser('enable', help='Uključi autostart na boot')
    subparsers.add_parser('disable', help='Isključi autostart')
    
    # uninstall
    subparsers.add_parser('uninstall', help='Deinstaliraj aplikaciju')
    
    args = parser.parse_args()
    
    commands = {
        'status': cmd_status,
        'info': cmd_info,
        'health': cmd_health,
        'start': cmd_start,
        'stop': cmd_stop,
        'restart': cmd_restart,
        'config': cmd_config,
        'port': cmd_port,
        'logs': cmd_logs,
        'backup': cmd_backup,
        'update': cmd_update,
        'db': cmd_db,
        'reset-users': cmd_reset_users,
        'enable': cmd_enable,
        'disable': cmd_disable,
        'uninstall': cmd_uninstall,
    }
    
    if args.command:
        commands[args.command](args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
