import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

def send_deploy_notification(server_hostname, server_type, status, output, trigger):
    """Envia email de notificação após deploy."""
    smtp_host = os.environ.get('SMTP_HOST', 'localhost')
    smtp_port = int(os.environ.get('SMTP_PORT', '25'))
    email_from = os.environ.get('EMAIL_FROM', '')
    email_to = os.environ.get('EMAIL_TO', '')
    org_name = os.environ.get('ORG_NAME', 'Cert Manager')
    base_url = os.environ.get('BASE_URL', '')

    if not email_to:
        return

    status_label = 'Sucesso ✅' if status == 'success' else 'Falha ❌'
    trigger_label = 'Automático' if trigger == 'auto' else 'Manual'
    tipo_label = {'zimbra': 'Zimbra', 'hestia': 'Hestia CP', 'web': 'Web'}.get(server_type, server_type)

    subject = f'[Cert Manager] Deploy {status_label} — {server_hostname}'

    # Limitar output para email
    output_lines = (output or '').strip().split('\n')
    output_preview = '\n'.join(output_lines[-30:]) if len(output_lines) > 30 else output or ''

    body = f"""Deploy de certificado SSL concluído.

Servidor:   {server_hostname}
Tipo:       {tipo_label}
Trigger:    {trigger_label}
Status:     {status_label}
Data/hora:  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

--- Saída do deploy ---
{output_preview}

Acesse {base_url} para mais detalhes.

-- Cert Manager | {org_name}
"""

    try:
        msg = MIMEMultipart()
        msg['From'] = email_from
        msg['To'] = email_to
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as smtp:
            smtp.sendmail(email_from, [email_to], msg.as_string())
    except Exception as e:
        print(f'[email] Erro ao enviar notificação: {e}')


def send_failure_summary(failures):
    """Envia resumo de falhas quando há erros no deploy automático."""
    if not failures:
        return

    smtp_host = os.environ.get('SMTP_HOST', 'localhost')
    smtp_port = int(os.environ.get('SMTP_PORT', '25'))
    email_from = os.environ.get('EMAIL_FROM', '')
    email_to = os.environ.get('EMAIL_TO', '')
    org_name = os.environ.get('ORG_NAME', 'Cert Manager')
    base_url = os.environ.get('BASE_URL', '')

    if not email_to:
        return

    lines = [f"  ❌ {f['hostname']} — {f['error']}" for f in failures]
    body = f"""Deploy automático concluído com falhas.

Data/hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

Servidores com falha:
{chr(10).join(lines)}

Acesse {base_url} para ver os logs completos.

-- Cert Manager | {org_name}
"""

    try:
        msg = MIMEMultipart()
        msg['From'] = email_from
        msg['To'] = email_to
        msg['Subject'] = f'[Cert Manager] ⚠️ Falhas no deploy automático — {len(failures)} servidor(es)'
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as smtp:
            smtp.sendmail(email_from, [email_to], msg.as_string())
    except Exception as e:
        print(f'[email] Erro ao enviar resumo de falhas: {e}')
