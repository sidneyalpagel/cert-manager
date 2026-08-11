#!/bin/bash
# =============================================================
# certbot-hook.sh — Chamado pelo Certbot após renovação
# Instalar em: /etc/letsencrypt/renewal-hooks/deploy/
# =============================================================

WEBHOOK_URL="https://certmanager.santahelena.pr.gov.br/api/webhook/certbot"
HOOK_TOKEN="DEFINA_O_MESMO_TOKEN_DO_.env"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Certificado renovado — disparando deploy automático..."

curl -s -X POST "$WEBHOOK_URL" \
     -H "X-Hook-Token: $HOOK_TOKEN" \
     -H "Content-Type: application/json" \
     --max-time 10 \
     --retry 3 || true

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Webhook disparado."
