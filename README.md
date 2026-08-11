# Cert Manager — Santa Helena / PR

Interface web para gerenciamento e deploy automático de certificados SSL wildcard (Let's Encrypt) em múltiplos servidores, incluindo Zimbra.

## Arquitetura

```
Certbot (timer systemd)
    └── certbot-hook.sh
            └── POST /api/webhook/certbot
                    └── deploy em todos os servidores (threads paralelas)
                            ├── Servidores web: rsync + reload apache/nginx
                            └── Zimbra: rsync + zmcertmgr + restart serviços
```

## Instalação no servidor

### Pré-requisitos

```bash
apt update
apt install -y python3 python3-venv python3-pip nginx git openssl curl
```

### Deploy inicial

```bash
# Clonar e instalar
git clone https://github.com/SEU_USUARIO/cert-manager.git /opt/cert-manager
cd /opt/cert-manager
bash deploy.sh

# Editar as configurações
nano /opt/cert-manager/.env

# Criar diretório de logs
mkdir -p /var/log/cert-manager

# Configurar Nginx
cp nginx.conf /etc/nginx/sites-available/cert-manager
ln -s /etc/nginx/sites-available/cert-manager /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

### Hook do Certbot

```bash
cp certbot-hook.sh /etc/letsencrypt/renewal-hooks/deploy/
chmod +x /etc/letsencrypt/renewal-hooks/deploy/certbot-hook.sh
# Editar o token no arquivo:
nano /etc/letsencrypt/renewal-hooks/deploy/certbot-hook.sh
```

### Atualizar após mudanças no código

```bash
bash /opt/cert-manager/deploy.sh
```

## Variáveis de ambiente (.env)

| Variável | Descrição | Padrão |
|---|---|---|
| `SECRET_KEY` | Chave secreta Flask | — (obrigatório) |
| `CERT_DOMAIN` | Domínio do certificado | santahelena.pr.gov.br |
| `CERT_BASE_DIR` | Diretório base do Let's Encrypt | /etc/letsencrypt/live |
| `CERT_DEST_DIR` | Destino padrão nos servidores | /opt/certificados |
| `SSH_KEY_PATH` | Chave SSH privada | /root/.ssh/id_certbot |
| `SSH_TIMEOUT` | Timeout SSH em segundos | 30 |
| `EXPIRY_WARN_DAYS` | Dias de aviso antes do vencimento | 30 |
| `HOOK_TOKEN` | Token de autenticação do webhook | — |

## Gerar SECRET_KEY

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

## Stack

- Python 3 + Flask
- SQLite (banco em `/opt/cert-manager/data/certmanager.db`)
- Gunicorn (servidor WSGI)
- Nginx (proxy reverso HTTPS)
- systemd (gerenciamento do serviço)
