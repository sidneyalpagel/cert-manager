from flask import Flask
from config import Config
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_db(app):
    db_path = app.config['DATABASE']
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(app):
    with app.app_context():
        db = get_db(app)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hostname TEXT NOT NULL,
                ip TEXT,
                type TEXT NOT NULL CHECK(type IN ('web', 'zimbra', 'hestia')),
                ssh_user TEXT NOT NULL DEFAULT 'root',
                ssh_port INTEGER NOT NULL DEFAULT 22,
                cert_dest_dir TEXT NOT NULL DEFAULT '/opt/certificados',
                post_deploy_cmd TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS deploy_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER REFERENCES servers(id),
                server_hostname TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('success', 'error', 'running')),
                trigger TEXT NOT NULL DEFAULT 'auto' CHECK(trigger IN ('auto', 'manual')),
                output TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                finished_at TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            INSERT OR IGNORE INTO settings (key, value) VALUES
                ('cert_domain', 'santahelena.pr.gov.br'),
                ('cert_base_dir', '/etc/letsencrypt/live'),
                ('cert_dest_dir', '/opt/certificados'),
                ('ssh_key_path', '/root/.ssh/id_certbot'),
                ('ssh_timeout', '30'),
                ('expiry_warn_days', '30');
        ''')
        db.commit()
        db.close()

def create_app():
    app = Flask(__name__,
                template_folder=os.path.join(BASE_DIR, 'templates'),
                static_folder=os.path.join(BASE_DIR, 'static'))
    app.config.from_object(Config)

    os.makedirs(os.path.dirname(app.config['DATABASE']), exist_ok=True)
    init_db(app)

    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.servidores import servidores_bp
    from app.routes.logs import logs_bp
    from app.routes.config import config_bp
    from app.routes.api import api_bp
    from app.routes.dns import dns_bp
    from app.routes.downloads import downloads_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(servidores_bp)
    app.register_blueprint(logs_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(dns_bp)
    app.register_blueprint(downloads_bp)

    @app.context_processor
    def inject_org():
        return {
            'ORG_NAME': app.config.get('ORG_NAME', 'Cert Manager'),
            'ORG_SHORT': app.config.get('ORG_SHORT', ''),
        }

    return app
