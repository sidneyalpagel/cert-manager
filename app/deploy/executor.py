import subprocess
import os
from datetime import datetime

def run_cmd(cmd, timeout=60):
    """Executa comando local e retorna (returncode, stdout+stderr)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True,
            text=True, timeout=timeout
        )
        output = result.stdout + result.stderr
        return result.returncode, output
    except subprocess.TimeoutExpired:
        return 1, f'Timeout após {timeout}s'
    except Exception as e:
        return 1, str(e)

def deploy_web(server, settings):
    """Deploy para servidor web: rsync + comando pós-deploy."""
    lines = []
    hostname = server['hostname']
    ssh_user = server['ssh_user']
    ssh_port = server['ssh_port']
    cert_dest = server['cert_dest_dir']
    post_cmd = server['post_deploy_cmd'] or 'systemctl reload apache2'
    ssh_key = settings.get('ssh_key_path', '/root/.ssh/id_certbot')
    cert_dir = os.path.join(
        settings.get('cert_base_dir', '/etc/letsencrypt/live'),
        settings.get('cert_domain', 'santahelena.pr.gov.br')
    )
    timeout = int(settings.get('ssh_timeout', '30'))

    ssh_opts = (
        f'-i {ssh_key} -p {ssh_port} '
        f'-o StrictHostKeyChecking=no '
        f'-o ConnectTimeout={timeout}'
    )

    lines.append(f'[{datetime.now():%H:%M:%S}] Iniciando deploy em {hostname}')

    # rsync dos certificados
    rsync_cmd = (
        f'rsync -az --delete --copy-links '
        f'-e "ssh {ssh_opts}" '
        f'{cert_dir}/ {ssh_user}@{hostname}:{cert_dest}/'
    )
    lines.append(f'[{datetime.now():%H:%M:%S}] rsync {cert_dir}/ → {cert_dest}/')
    rc, out = run_cmd(rsync_cmd, timeout=60)
    lines.append(out.strip())
    if rc != 0:
        lines.append(f'[{datetime.now():%H:%M:%S}] ERRO no rsync (rc={rc})')
        return False, '\n'.join(lines)

    # Ajuste de permissões
    perm_cmd = (
        f'ssh {ssh_opts} {ssh_user}@{hostname} '
        f'"chmod 600 {cert_dest}/privkey.pem"'
    )
    rc, out = run_cmd(perm_cmd, timeout=timeout)
    if out.strip():
        lines.append(out.strip())

    # Comando pós-deploy (reload do serviço)
    lines.append(f'[{datetime.now():%H:%M:%S}] Executando: {post_cmd}')
    reload_cmd = f'ssh {ssh_opts} {ssh_user}@{hostname} "{post_cmd}"'
    rc, out = run_cmd(reload_cmd, timeout=timeout)
    lines.append(out.strip())
    if rc != 0:
        lines.append(f'[{datetime.now():%H:%M:%S}] ERRO no pós-deploy (rc={rc})')
        return False, '\n'.join(lines)

    lines.append(f'[{datetime.now():%H:%M:%S}] Deploy concluído com sucesso')
    return True, '\n'.join(lines)

def deploy_zimbra(server, settings):
    """Deploy para servidor Zimbra: rsync + zmcertmgr + restart serviços."""
    lines = []
    hostname = server['hostname']
    ssh_user = server['ssh_user']
    ssh_port = server['ssh_port']
    zimbra_dir = server['cert_dest_dir'] or '/opt/zimbra/ssl/letsencrypt'
    ssh_key = settings.get('ssh_key_path', '/root/.ssh/id_certbot')
    cert_dir = os.path.join(
        settings.get('cert_base_dir', '/etc/letsencrypt/live'),
        settings.get('cert_domain', 'santahelena.pr.gov.br')
    )
    ca_path = '/etc/letsencrypt/isrgrootx1.pem'
    timeout = int(settings.get('ssh_timeout', '30'))

    ssh_opts = (
        f'-i {ssh_key} -p {ssh_port} '
        f'-o StrictHostKeyChecking=no '
        f'-o ConnectTimeout={timeout}'
    )

    lines.append(f'[{datetime.now():%H:%M:%S}] Iniciando deploy Zimbra em {hostname}')

    # Garantir que o CA root existe localmente
    if not os.path.exists(ca_path):
        rc, out = run_cmd(f'curl -s https://letsencrypt.org/certs/isrgrootx1.pem -o {ca_path}', timeout=30)
        if rc != 0:
            lines.append(f'[{datetime.now():%H:%M:%S}] ERRO ao baixar CA root')
            return False, '\n'.join(lines)

    # rsync dos certificados + CA root
    rsync_cmd = (
        f'rsync -az --delete --copy-links --checksum '
        f'-e "ssh {ssh_opts}" '
        f'{cert_dir}/ {ssh_user}@{hostname}:{zimbra_dir}/ '
        f'&& rsync -az --checksum -e "ssh {ssh_opts}" '
        f'{ca_path} {ssh_user}@{hostname}:{zimbra_dir}/isrgrootx1.pem'
    )
    lines.append(f'[{datetime.now():%H:%M:%S}] rsync → {zimbra_dir}/')
    rc, out = run_cmd(rsync_cmd, timeout=60)
    if out.strip():
        lines.append(out.strip())
    if rc != 0:
        lines.append(f'[{datetime.now():%H:%M:%S}] ERRO no rsync (rc={rc})')
        return False, '\n'.join(lines)

    # Script remoto completo do Zimbra
    zimbra_script = f"""
set -e
ZDIR="{zimbra_dir}"
mkdir -p $ZDIR
rm -f $ZDIR/zimbra.crt $ZDIR/ca.crt

# Montar zimbra.crt = cert + chain
cat $ZDIR/cert.pem $ZDIR/chain.pem > $ZDIR/zimbra.crt

# Montar ca.crt com cadeia completa: chain + isrgrootx1
# (necessário para Zimbra validar a cadeia YR1 -> Root YR -> ISRG Root X1)
cat $ZDIR/chain.pem $ZDIR/isrgrootx1.pem > $ZDIR/ca.crt

# Copiar nova chave privada para o local do Zimbra
cp $ZDIR/privkey.pem /opt/zimbra/ssl/zimbra/commercial/commercial.key
chown zimbra:zimbra /opt/zimbra/ssl/zimbra/commercial/commercial.key
chmod 640 /opt/zimbra/ssl/zimbra/commercial/commercial.key

# Ajustar permissões do diretório
chown -R zimbra:zimbra $ZDIR
chmod 600 $ZDIR/privkey.pem

# Verificar e fazer deploy
sudo -u zimbra /opt/zimbra/bin/zmcertmgr verifycrt comm \\
  $ZDIR/privkey.pem $ZDIR/zimbra.crt $ZDIR/ca.crt

sudo -u zimbra /opt/zimbra/bin/zmcertmgr deploycrt comm \\
  $ZDIR/zimbra.crt $ZDIR/ca.crt

# Reiniciar serviços
sudo -u zimbra /opt/zimbra/bin/zmcontrol restart

echo "Zimbra deploy OK"
"""

    lines.append(f'[{datetime.now():%H:%M:%S}] Executando zmcertmgr + restart serviços')
    remote_cmd = f"ssh {ssh_opts} {ssh_user}@{hostname} 'bash -s' << 'ENDSSH'\n{zimbra_script}\nENDSSH"
    rc, out = run_cmd(remote_cmd, timeout=600)
    lines.append(out.strip())
    if rc != 0:
        lines.append(f'[{datetime.now():%H:%M:%S}] ERRO no deploy Zimbra (rc={rc})')
        return False, '\n'.join(lines)

    lines.append(f'[{datetime.now():%H:%M:%S}] Deploy Zimbra concluído com sucesso')
    return True, '\n'.join(lines)
    """Deploy para servidor Zimbra: rsync + zmcertmgr + restart serviços."""
    lines = []
    hostname = server['hostname']
    ssh_user = server['ssh_user']
    ssh_port = server['ssh_port']
    zimbra_dir = server['cert_dest_dir'] or '/opt/zimbra/ssl/letsencrypt'
    ssh_key = settings.get('ssh_key_path', '/root/.ssh/id_certbot')
    cert_dir = os.path.join(
        settings.get('cert_base_dir', '/etc/letsencrypt/live'),
        settings.get('cert_domain', 'santahelena.pr.gov.br')
    )
    timeout = int(settings.get('ssh_timeout', '30'))

    ssh_opts = (
        f'-i {ssh_key} -p {ssh_port} '
        f'-o StrictHostKeyChecking=no '
        f'-o ConnectTimeout={timeout}'
    )

    lines.append(f'[{datetime.now():%H:%M:%S}] Iniciando deploy Zimbra em {hostname}')

    # Garantir que o CA root existe localmente
    ca_path = '/etc/letsencrypt/isrgrootx1.pem'
    if not os.path.exists(ca_path):
        rc, out = run_cmd(f'curl -s https://letsencrypt.org/certs/isrgrootx1.pem -o {ca_path}', timeout=30)
        if rc != 0:
            lines.append(f'[{datetime.now():%H:%M:%S}] ERRO ao baixar CA root')
            return False, '\n'.join(lines)

    # rsync dos certificados + CA root
    rsync_cmd = (
        f'rsync -az --delete --copy-links --checksum '
        f'-e "ssh {ssh_opts}" '
        f'{cert_dir}/ {ssh_user}@{hostname}:{zimbra_dir}/ '
        f'&& rsync -az --checksum -e "ssh {ssh_opts}" '
        f'{ca_path} {ssh_user}@{hostname}:{zimbra_dir}/ca.crt'
    )
    lines.append(f'[{datetime.now():%H:%M:%S}] rsync → {zimbra_dir}/')
    rc, out = run_cmd(rsync_cmd, timeout=60)
    lines.append(out.strip())
    if rc != 0:
        lines.append(f'[{datetime.now():%H:%M:%S}] ERRO no rsync (rc={rc})')
        return False, '\n'.join(lines)

    # Verificar se os arquivos chegaram
    check_cmd = f'ssh {ssh_opts} {ssh_user}@{hostname} "ls -la {zimbra_dir}/"'
    rc, out = run_cmd(check_cmd, timeout=timeout)
    lines.append(out.strip())

    # Script remoto completo do Zimbra
    zimbra_script = f"""
set -e
ZDIR="{zimbra_dir}"
mkdir -p $ZDIR
rm -f $ZDIR/zimbra.crt
cat $ZDIR/cert.pem $ZDIR/chain.pem > $ZDIR/zimbra.crt
chown -R zimbra:zimbra $ZDIR
chmod 600 $ZDIR/privkey.pem
sudo -u zimbra /opt/zimbra/bin/zmcertmgr verifycrt comm $ZDIR/privkey.pem $ZDIR/zimbra.crt $ZDIR/ca.crt
sudo -u zimbra /opt/zimbra/bin/zmcertmgr deploycrt comm $ZDIR/zimbra.crt $ZDIR/ca.crt
sudo -u zimbra /opt/zimbra/bin/zmproxyctl restart
sudo -u zimbra /opt/zimbra/bin/zmmailboxdctl restart
echo "Zimbra deploy OK"
"""

    lines.append(f'[{datetime.now():%H:%M:%S}] Executando zmcertmgr + restart serviços')
    remote_cmd = f"ssh {ssh_opts} {ssh_user}@{hostname} 'bash -s' << 'ENDSSH'\n{zimbra_script}\nENDSSH"
    rc, out = run_cmd(remote_cmd, timeout=300)
    lines.append(out.strip())
    if rc != 0:
        lines.append(f'[{datetime.now():%H:%M:%S}] ERRO no deploy Zimbra (rc={rc})')
        return False, '\n'.join(lines)

    lines.append(f'[{datetime.now():%H:%M:%S}] Deploy Zimbra concluído com sucesso')
    return True, '\n'.join(lines)

def deploy_hestia(server, settings):
    """Deploy para servidor Hestia CP: rsync wildcard + reload nginx/apache."""
    lines = []
    hostname = server['hostname']
    ssh_user = server['ssh_user']
    ssh_port = server['ssh_port']
    ssh_key = settings.get('ssh_key_path', '/root/.ssh/id_certbot')
    domain = settings.get('cert_domain', 'santahelena.pr.gov.br')
    cert_dir = os.path.join(
        settings.get('cert_base_dir', '/etc/letsencrypt/live'),
        domain
    )
    timeout = int(settings.get('ssh_timeout', '30'))
    # hestia_user pode ser customizado via cert_dest_dir (ex: "admin")
    hestia_user = server['cert_dest_dir'] or 'admin'

    ssh_opts = (
        f'-i {ssh_key} -p {ssh_port} '
        f'-o StrictHostKeyChecking=no '
        f'-o ConnectTimeout={timeout}'
    )

    lines.append(f'[{datetime.now():%H:%M:%S}] Iniciando deploy Hestia em {hostname}')

    # Script remoto: copia certificados para cada domínio e recarrega
    hestia_script = f"""
set -e
DOMAIN="{domain}"
HESTIA_USER="{hestia_user}"
CERT_DIR="/tmp/certmanager_ssl"
LE_DIR="/etc/letsencrypt/live/$DOMAIN"

mkdir -p $CERT_DIR

# Copiar certificados recebidos para diretório temporário
cp $LE_DIR/cert.pem    $CERT_DIR/$DOMAIN.crt
cp $LE_DIR/privkey.pem $CERT_DIR/$DOMAIN.key
cp $LE_DIR/chain.pem   $CERT_DIR/$DOMAIN.ca
cp $LE_DIR/fullchain.pem $CERT_DIR/$DOMAIN.pem

echo "Atualizando certificado wildcard no Hestia para usuário $HESTIA_USER..."

# Listar todos os domínios do usuário que usam SSL
for DOM in $(ls /home/$HESTIA_USER/conf/web/ 2>/dev/null); do
    SSL_DIR="/home/$HESTIA_USER/conf/web/$DOM/ssl"
    if [ -d "$SSL_DIR" ]; then
        echo "  → $DOM"
        cp $CERT_DIR/$DOMAIN.crt  $SSL_DIR/$DOM.crt  2>/dev/null || true
        cp $CERT_DIR/$DOMAIN.key  $SSL_DIR/$DOM.key  2>/dev/null || true
        cp $CERT_DIR/$DOMAIN.ca   $SSL_DIR/$DOM.ca   2>/dev/null || true
        cp $CERT_DIR/$DOMAIN.pem  $SSL_DIR/$DOM.pem  2>/dev/null || true
        chmod 640 $SSL_DIR/$DOM.key
    fi
done

# Também atualiza o certificado do próprio painel Hestia
if [ -d "/usr/local/hestia/ssl" ]; then
    cp $CERT_DIR/$DOMAIN.crt /usr/local/hestia/ssl/certificate.crt
    cp $CERT_DIR/$DOMAIN.key /usr/local/hestia/ssl/certificate.key
    echo "  → Painel Hestia atualizado"
fi

# Recarregar serviços web
systemctl reload nginx  2>/dev/null && echo "  → nginx recarregado" || true
systemctl reload apache2 2>/dev/null && echo "  → apache2 recarregado" || true

# Reiniciar o painel Hestia para pegar o novo certificado
systemctl restart hestia 2>/dev/null && echo "  → hestia reiniciado" || true

rm -rf $CERT_DIR
echo "Hestia deploy OK"
"""

    lines.append(f'[{datetime.now():%H:%M:%S}] Sincronizando certificados via rsync')

    # Primeiro envia os certificados para o servidor via rsync
    tmp_dir = f'/tmp/certmanager_ssl_{domain}'
    rsync_cmd = (
        f'rsync -az --delete '
        f'-e "ssh {ssh_opts}" '
        f'{cert_dir}/ {ssh_user}@{hostname}:/etc/letsencrypt/live/{domain}/'
    )
    rc, out = run_cmd(rsync_cmd, timeout=60)
    if out.strip():
        lines.append(out.strip())
    if rc != 0:
        lines.append(f'[{datetime.now():%H:%M:%S}] ERRO no rsync (rc={rc})')
        return False, '\n'.join(lines)

    lines.append(f'[{datetime.now():%H:%M:%S}] Distribuindo para domínios Hestia e recarregando serviços')
    remote_cmd = f"ssh {ssh_opts} {ssh_user}@{hostname} 'bash -s' << 'ENDSSH'\n{hestia_script}\nENDSSH"
    rc, out = run_cmd(remote_cmd, timeout=120)
    lines.append(out.strip())
    if rc != 0:
        lines.append(f'[{datetime.now():%H:%M:%S}] ERRO no deploy Hestia (rc={rc})')
        return False, '\n'.join(lines)

    lines.append(f'[{datetime.now():%H:%M:%S}] Deploy Hestia concluído com sucesso')
    return True, '\n'.join(lines)


def test_ssh_connection(server, settings):
    """Testa conectividade SSH com um servidor."""
    hostname = server['hostname']
    ssh_user = server['ssh_user']
    ssh_port = server['ssh_port']
    ssh_key = settings.get('ssh_key_path', '/root/.ssh/id_certbot')
    timeout = int(settings.get('ssh_timeout', '30'))

    ssh_opts = (
        f'-i {ssh_key} -p {ssh_port} '
        f'-o StrictHostKeyChecking=no '
        f'-o ConnectTimeout={timeout}'
    )
    cmd = f'ssh {ssh_opts} {ssh_user}@{hostname} "echo OK"'
    rc, out = run_cmd(cmd, timeout=timeout + 5)
    return rc == 0, out.strip()
