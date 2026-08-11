from flask import Blueprint, render_template
from app.routes.auth import login_required
from app.models import get_all_servers, get_server_last_deploy, get_deploy_logs, get_recent_failures, get_all_settings
from datetime import datetime, timezone
import subprocess
import os

dashboard_bp = Blueprint('dashboard', __name__)

def get_cert_expiry(settings):
    """Retorna dias até o vencimento do certificado."""
    try:
        cert_path = os.path.join(
            settings.get('cert_base_dir', '/etc/letsencrypt/live'),
            settings.get('cert_domain', 'santahelena.pr.gov.br'),
            'cert.pem'
        )
        result = subprocess.run(
            ['openssl', 'x509', '-enddate', '-noout', '-in', cert_path],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            date_str = result.stdout.strip().replace('notAfter=', '')
            expiry = datetime.strptime(date_str, '%b %d %H:%M:%S %Y %Z')
            expiry = expiry.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            return (expiry - now).days
    except Exception:
        pass
    return None

@dashboard_bp.route('/')
@login_required
def index():
    settings = get_all_settings()
    servers = get_all_servers()
    server_list = []
    for s in servers:
        last = get_server_last_deploy(s['id'])
        server_list.append({
            'server': s,
            'last_deploy': last
        })

    recent_logs = get_deploy_logs(limit=20)
    failures = get_recent_failures()
    cert_days = get_cert_expiry(settings)

    return render_template('dashboard.html',
        servers=server_list,
        recent_logs=recent_logs,
        failures=failures,
        cert_days=cert_days,
        settings=settings
    )
