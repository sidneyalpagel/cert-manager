import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'troque-esta-chave-em-producao'
    DATABASE = os.environ.get('DATABASE') or os.path.join(BASE_DIR, 'data', 'certmanager.db')
    CERT_BASE_DIR = os.environ.get('CERT_BASE_DIR', '/etc/letsencrypt/live')
    CERT_DOMAIN = os.environ.get('CERT_DOMAIN', 'santahelena.pr.gov.br')
    CERT_DEST_DIR = os.environ.get('CERT_DEST_DIR', '/opt/certificados')
    SSH_KEY_PATH = os.environ.get('SSH_KEY_PATH', '/root/.ssh/id_certbot')
    SSH_TIMEOUT = int(os.environ.get('SSH_TIMEOUT', '30'))
    EXPIRY_WARN_DAYS = int(os.environ.get('EXPIRY_WARN_DAYS', '30'))
