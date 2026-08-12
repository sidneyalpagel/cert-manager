from flask import Blueprint, render_template, send_file, abort, current_app
from app.routes.auth import login_required
from app.models import get_all_settings
import os
import io

downloads_bp = Blueprint('downloads', __name__)

def gerar_tudo_pem(settings):
    """Concatena privkey + cert + fullchain no formato esperado pelo HikCentral."""
    cert_dir = os.path.join(
        settings.get('cert_base_dir', '/etc/letsencrypt/live'),
        settings.get('cert_domain', 'santahelena.pr.gov.br')
    )
    arquivos = [
        os.path.join(cert_dir, 'privkey.pem'),
        os.path.join(cert_dir, 'cert.pem'),
        os.path.join(cert_dir, 'fullchain.pem'),
    ]
    conteudo = ''
    for arq in arquivos:
        if not os.path.exists(arq):
            return None, f'Arquivo não encontrado: {arq}'
        with open(arq, 'r') as f:
            conteudo += f.read().strip() + '\n\n'
    return conteudo, None

def get_cert_info(settings):
    """Retorna informações do certificado atual."""
    import subprocess
    cert_dir = os.path.join(
        settings.get('cert_base_dir', '/etc/letsencrypt/live'),
        settings.get('cert_domain', 'santahelena.pr.gov.br')
    )
    cert_path = os.path.join(cert_dir, 'cert.pem')
    info = {}
    try:
        r = subprocess.run(
            ['openssl', 'x509', '-noout', '-subject', '-dates', '-in', cert_path],
            capture_output=True, text=True, timeout=10
        )
        for line in r.stdout.splitlines():
            if 'notAfter' in line:
                info['vencimento'] = line.split('=', 1)[1].strip()
            if 'subject' in line:
                info['dominio'] = line.split('=', 1)[1].strip()
        # Tamanho dos arquivos
        for nome in ['privkey.pem', 'cert.pem', 'fullchain.pem']:
            p = os.path.join(cert_dir, nome)
            if os.path.exists(p):
                stat = os.stat(p)
                info[nome] = {
                    'tamanho': stat.st_size,
                    'modificado': stat.st_mtime
                }
    except Exception as e:
        info['erro'] = str(e)
    return info

@downloads_bp.route('/downloads')
@login_required
def index():
    settings = get_all_settings()
    conteudo, erro = gerar_tudo_pem(settings)
    info = get_cert_info(settings)
    return render_template('downloads.html',
        settings=settings,
        erro=erro,
        info=info,
        tamanho=len(conteudo) if conteudo else 0
    )

@downloads_bp.route('/downloads/tudo.pem')
@login_required
def baixar_tudo_pem():
    settings = get_all_settings()
    conteudo, erro = gerar_tudo_pem(settings)
    if erro:
        abort(404, description=erro)
    return send_file(
        io.BytesIO(conteudo.encode('utf-8')),
        mimetype='application/x-pem-file',
        as_attachment=True,
        download_name='tudo.pem'
    )

@downloads_bp.route('/downloads/<nome>')
@login_required
def baixar_arquivo(nome):
    """Download individual de qualquer arquivo do certificado."""
    arquivos_permitidos = ['cert.pem', 'privkey.pem', 'fullchain.pem', 'chain.pem']
    if nome not in arquivos_permitidos:
        abort(403)
    settings = get_all_settings()
    cert_dir = os.path.join(
        settings.get('cert_base_dir', '/etc/letsencrypt/live'),
        settings.get('cert_domain', 'santahelena.pr.gov.br')
    )
    path = os.path.join(cert_dir, nome)
    if not os.path.exists(path):
        abort(404)
    return send_file(
        path,
        mimetype='application/x-pem-file',
        as_attachment=True,
        download_name=nome
    )
