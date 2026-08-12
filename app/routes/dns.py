from flask import Blueprint, redirect, current_app
from app.routes.auth import login_required
from app.models import get_setting
import requests
import os

dns_bp = Blueprint('dns', __name__)

def get_technitium_url():
    return os.environ.get('TECHNITIUM_URL', 'http://192.168.0.64:5380')

def get_technitium_token():
    """Faz login no Technitium e retorna o token de sessão."""
    try:
        url = get_technitium_url()
        user = os.environ.get('TECHNITIUM_USER', 'admin')
        passwd = os.environ.get('TECHNITIUM_PASS', 'RhiUrj89')
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
    return None, get_technitium_url()

@dns_bp.route('/dns/technitium')
@login_required
def technitium_redirect():
    """Redireciona para o Technitium já autenticado."""
    token, url = get_technitium_token()
    if token:
        return redirect(f'{url}/#token={token}')
    # Fallback: redireciona para o login normal
    return redirect(f'{url}/')
