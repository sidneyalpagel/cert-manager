from flask import Blueprint, render_template, request
from app.routes.auth import login_required
from app.models import get_deploy_logs, get_db

logs_bp = Blueprint('logs', __name__)

@logs_bp.route('/logs')
@login_required
def index():
    limit = int(request.args.get('limit', 100))
    logs = get_deploy_logs(limit=limit)
    return render_template('logs.html', logs=logs, limit=limit)

@logs_bp.route('/logs/<int:log_id>')
@login_required
def detail(log_id):
    log = get_db().execute(
        'SELECT * FROM deploy_logs WHERE id = ?', (log_id,)
    ).fetchone()
    return render_template('log_detail.html', log=log)
