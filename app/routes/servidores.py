from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.routes.auth import login_required
from app.models import (get_all_servers, get_server, create_server,
                        update_server, delete_server, get_server_last_deploy,
                        get_all_settings)
from app.deploy.executor import test_ssh_connection

servidores_bp = Blueprint('servidores', __name__)

@servidores_bp.route('/servidores')
@login_required
def index():
    servers = get_all_servers()
    server_list = []
    for s in servers:
        last = get_server_last_deploy(s['id'])
        server_list.append({'server': s, 'last_deploy': last})
    return render_template('servidores.html', servers=server_list)

@servidores_bp.route('/servidores/novo', methods=['GET', 'POST'])
@login_required
def novo():
    if request.method == 'POST':
        hostname = request.form.get('hostname', '').strip()
        ip = request.form.get('ip', '').strip()
        type_ = request.form.get('type', 'web')
        ssh_user = request.form.get('ssh_user', 'root').strip()
        ssh_port = int(request.form.get('ssh_port', 22))
        cert_dest = request.form.get('cert_dest_dir', '/opt/certificados').strip()
        post_cmd = request.form.get('post_deploy_cmd', '').strip()

        if not hostname:
            flash('Hostname é obrigatório.', 'error')
        else:
            create_server(hostname, ip, type_, ssh_user, ssh_port, cert_dest, post_cmd)
            flash(f'Servidor {hostname} cadastrado com sucesso.', 'success')
            return redirect(url_for('servidores.index'))

    return render_template('servidor_form.html', server=None, action='novo')

@servidores_bp.route('/servidores/<int:server_id>/editar', methods=['GET', 'POST'])
@login_required
def editar(server_id):
    server = get_server(server_id)
    if not server:
        flash('Servidor não encontrado.', 'error')
        return redirect(url_for('servidores.index'))

    if request.method == 'POST':
        hostname = request.form.get('hostname', '').strip()
        ip = request.form.get('ip', '').strip()
        type_ = request.form.get('type', 'web')
        ssh_user = request.form.get('ssh_user', 'root').strip()
        ssh_port = int(request.form.get('ssh_port', 22))
        cert_dest = request.form.get('cert_dest_dir', '/opt/certificados').strip()
        post_cmd = request.form.get('post_deploy_cmd', '').strip()

        update_server(server_id, hostname, ip, type_, ssh_user, ssh_port, cert_dest, post_cmd)
        flash(f'Servidor {hostname} atualizado.', 'success')
        return redirect(url_for('servidores.index'))

    return render_template('servidor_form.html', server=server, action='editar')

@servidores_bp.route('/servidores/<int:server_id>/remover', methods=['POST'])
@login_required
def remover(server_id):
    server = get_server(server_id)
    if server:
        delete_server(server_id)
        flash(f'Servidor {server["hostname"]} removido.', 'success')
    return redirect(url_for('servidores.index'))

@servidores_bp.route('/servidores/<int:server_id>/testar', methods=['POST'])
@login_required
def testar(server_id):
    server = get_server(server_id)
    if not server:
        return jsonify({'ok': False, 'msg': 'Servidor não encontrado'})
    settings = get_all_settings()
    ok, msg = test_ssh_connection(server, settings)
    return jsonify({'ok': ok, 'msg': msg})
