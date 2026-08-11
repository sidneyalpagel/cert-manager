from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.routes.auth import login_required
from app.models import get_all_settings, set_setting

config_bp = Blueprint('config', __name__)

@config_bp.route('/configuracao', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        keys = ['cert_domain', 'cert_base_dir', 'cert_dest_dir',
                'ssh_key_path', 'ssh_timeout', 'expiry_warn_days']
        for key in keys:
            val = request.form.get(key, '').strip()
            if val:
                set_setting(key, val)
        flash('Configurações salvas com sucesso.', 'success')
        return redirect(url_for('config.index'))

    settings = get_all_settings()
    return render_template('config.html', settings=settings)
