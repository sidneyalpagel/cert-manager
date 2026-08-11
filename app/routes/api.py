from flask import Blueprint, request, jsonify, current_app
from app.routes.auth import login_required
from app.models import (get_all_servers, get_server, create_deploy_log,
                        finish_deploy_log, get_all_settings)
from app.deploy.executor import deploy_web, deploy_zimbra
import threading
import hmac
import hashlib
import os

api_bp = Blueprint('api', __name__)

def run_deploy_server(app, server, settings, log_id, trigger='manual'):
    """Executa deploy em thread separada para não bloquear a interface."""
    with app.app_context():
        from app.models import finish_deploy_log
        try:
            if server['type'] == 'zimbra':
                ok, output = deploy_zimbra(server, settings)
            else:
                ok, output = deploy_web(server, settings)
            finish_deploy_log(log_id, 'success' if ok else 'error', output)
        except Exception as e:
            finish_deploy_log(log_id, 'error', str(e))

def run_deploy_all(app, servers, settings, trigger='manual'):
    """Deploy em todos os servidores."""
    with app.app_context():
        from app.models import create_deploy_log, finish_deploy_log
        for server in servers:
            log_id = create_deploy_log(server['id'], server['hostname'], trigger)
            try:
                if server['type'] == 'zimbra':
                    ok, output = deploy_zimbra(server, settings)
                else:
                    ok, output = deploy_web(server, settings)
                finish_deploy_log(log_id, 'success' if ok else 'error', output)
            except Exception as e:
                finish_deploy_log(log_id, 'error', str(e))

@api_bp.route('/api/deploy/all', methods=['POST'])
@login_required
def deploy_all():
    """Deploy manual em todos os servidores."""
    servers = get_all_servers()
    settings = get_all_settings()
    app = current_app._get_current_object()

    t = threading.Thread(
        target=run_deploy_all,
        args=(app, [dict(s) for s in servers], settings, 'manual')
    )
    t.daemon = True
    t.start()

    return jsonify({'ok': True, 'msg': f'Deploy iniciado em {len(servers)} servidor(es).'})

@api_bp.route('/api/deploy/<int:server_id>', methods=['POST'])
@login_required
def deploy_one(server_id):
    """Deploy manual em um servidor específico."""
    server = get_server(server_id)
    if not server:
        return jsonify({'ok': False, 'msg': 'Servidor não encontrado'}), 404

    settings = get_all_settings()
    log_id = create_deploy_log(server['id'], server['hostname'], 'manual')
    app = current_app._get_current_object()

    t = threading.Thread(
        target=run_deploy_server,
        args=(app, dict(server), settings, log_id, 'manual')
    )
    t.daemon = True
    t.start()

    return jsonify({'ok': True, 'msg': f'Deploy iniciado em {server["hostname"]}', 'log_id': log_id})

@api_bp.route('/api/webhook/certbot', methods=['POST'])
def certbot_webhook():
    """
    Chamado pelo script certbot-hook.sh após renovação automática.
    Protegido por token secreto no header X-Hook-Token.
    """
    token = os.environ.get('HOOK_TOKEN', '')
    if token:
        received = request.headers.get('X-Hook-Token', '')
        if not hmac.compare_digest(token, received):
            return jsonify({'ok': False, 'msg': 'Unauthorized'}), 401

    servers = get_all_servers()
    settings = get_all_settings()
    app = current_app._get_current_object()

    t = threading.Thread(
        target=run_deploy_all,
        args=(app, [dict(s) for s in servers], settings, 'auto')
    )
    t.daemon = True
    t.start()

    return jsonify({'ok': True, 'msg': f'Deploy automático iniciado em {len(servers)} servidor(es).'})

@api_bp.route('/api/status', methods=['GET'])
@login_required
def status():
    """Retorna status resumido para polling da interface."""
    from app.models import get_db
    db = get_db()
    running = db.execute(
        "SELECT COUNT(*) FROM deploy_logs WHERE status = 'running'"
    ).fetchone()[0]
    return jsonify({'running': running})
