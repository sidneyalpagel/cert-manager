#!/bin/bash
# =============================================================
# deploy.sh — Atualiza o Cert Manager a partir do branch main
# Uso: bash deploy.sh
# O token do GitHub é lido de /root/.github_token
# =============================================================
set -e

APP_DIR="/opt/cert-manager"
GITHUB_USER="sidneyalpagel"
REPO="cert-manager"
BRANCH="main"
SERVICE="cert-manager"
VENV="$APP_DIR/venv"
DATA_DIR="$APP_DIR/data"
TOKEN_FILE="/root/.github_token"

echo "=============================="
echo " Cert Manager — Deploy"
echo " $(date '+%Y-%m-%d %H:%M:%S')"
echo "=============================="

# Ler token do arquivo local (nunca fica no código)
if [ ! -f "$TOKEN_FILE" ]; then
    echo "ERRO: Arquivo $TOKEN_FILE não encontrado."
    echo "Crie-o com: echo 'seu_token' > $TOKEN_FILE && chmod 600 $TOKEN_FILE"
    exit 1
fi
TOKEN=$(cat "$TOKEN_FILE" | tr -d '[:space:]')
REPO_URL="https://${GITHUB_USER}:${TOKEN}@github.com/${GITHUB_USER}/${REPO}.git"

# 1. Clonar ou atualizar o repositório
if [ -d "$APP_DIR/.git" ]; then
    echo "[1/5] Atualizando código do GitHub..."
    cd "$APP_DIR"
    git remote set-url origin "$REPO_URL"
    git fetch origin
    git reset --hard origin/$BRANCH
    git clean -fd
    # Limpar token da URL remota após uso
    git remote set-url origin "https://github.com/${GITHUB_USER}/${REPO}.git"
else
    echo "[1/5] Clonando repositório..."
    git clone -b "$BRANCH" "$REPO_URL" "$APP_DIR"
    cd "$APP_DIR"
    # Limpar token da URL remota após clone
    git remote set-url origin "https://github.com/${GITHUB_USER}/${REPO}.git"
fi

# 2. Garantir que o diretório de dados existe (fora do git)
echo "[2/5] Verificando diretório de dados..."
mkdir -p "$DATA_DIR"

# 3. Criar/atualizar virtualenv
echo "[3/5] Atualizando dependências Python..."
if [ ! -d "$VENV" ]; then
    python3 -m venv "$VENV"
fi
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q -r "$APP_DIR/requirements.txt"

# 4. Criar .env se não existir
if [ ! -f "$APP_DIR/.env" ]; then
    echo "[4/5] Criando .env inicial..."
    cat > "$APP_DIR/.env" << 'EOF'
SECRET_KEY=GERE_UMA_CHAVE_SEGURA_AQUI
CERT_DOMAIN=santahelena.pr.gov.br
CERT_BASE_DIR=/etc/letsencrypt/live
CERT_DEST_DIR=/opt/certificados
SSH_KEY_PATH=/root/.ssh/id_certbot
SSH_TIMEOUT=30
EXPIRY_WARN_DAYS=30
HOOK_TOKEN=DEFINA_UM_TOKEN_SECRETO_AQUI
EOF
    echo "    ⚠️  Edite $APP_DIR/.env com suas configurações!"
else
    echo "[4/5] Arquivo .env já existe — mantendo."
fi

# 5. Instalar e reiniciar o serviço systemd
echo "[5/5] Reiniciando serviço..."
mkdir -p /var/log/cert-manager
cp "$APP_DIR/cert-manager.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable "$SERVICE"
systemctl restart "$SERVICE"

echo ""
echo "✅ Deploy concluído!"
systemctl status "$SERVICE" --no-pager -l
