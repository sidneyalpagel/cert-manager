from flask import Blueprint, redirect, current_app
from app.routes.auth import login_required
from app.models import get_setting
import requests
import os

dns_bp = Blueprint('dns', __name__)

def get_technitium_url():
    return os.environ.get('TECHNITIUM_URL', '')

def get_dns_panel_url():
    """Retorna URL do painel DNS — Technitium ou Cloudflare conforme configurado."""
    return os.environ.get('DNS_PANEL_URL', os.environ.get('TECHNITIUM_URL', ''))

def get_technitium_token():
    """Faz login no Technitium e retorna o token de sessão."""
    try:
        url = get_technitium_url()
        if not url or 'cloudflare' in url:
            return None, url
        user = os.environ.get('TECHNITIUM_USER', 'admin')
        passwd = os.environ.get('TECHNITIUM_PASS', '')
        r = requests.get(
            f'{url}/api/user/login',
            params={'user': user, 'pass': passwd, 'includeInfo': 'true'},
            timeout=5
        )
        data = r.json()
        if data.get('status') == 'ok':
            return data.get('token'), url
    except Exception:
        pass
    return None, get_dns_panel_url()

@dns_bp.route('/dns/technitium')
@login_required
def technitium_redirect():
    """Redireciona para o painel DNS configurado."""
    panel_url = get_dns_panel_url()

    # Se for Cloudflare, redireciona direto
    if 'cloudflare' in panel_url.lower() or not os.environ.get('TECHNITIUM_URL'):
        return redirect(panel_url)

    # Se for Technitium, faz login automático
    token, url = get_technitium_token()
    if token:
        return redirect(f'{url}/#token={token}')
    return redirect(panel_url or url or '/')
