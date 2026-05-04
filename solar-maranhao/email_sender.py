"""
Envio de email com relatório PDF via SMTP (Gmail).
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

from config import RECIPIENT_EMAIL

MESES_PT_FULL = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}


def send_report_email(pdf_path, year, month):
    """
    Envia o relatório PDF por email via Gmail SMTP.
    Usa as variáveis de ambiente GMAIL_FROM e GMAIL_APP_PASSWORD.
    """
    gmail_from = os.environ.get("GMAIL_FROM", "francisco.santo@beng.eng.br")
    app_password = os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "")

    if not app_password:
        raise ValueError("GMAIL_APP_PASSWORD não configurada. Execute: export GMAIL_APP_PASSWORD='sua senha'")

    month_name = MESES_PT_FULL.get(month, str(month))
    subject = f"Relatório de Geração Solar – {month_name}/{year}"

    body = f"""Bom dia pessoal,

Segue o relatório do mês {month_name}/{year}.

O relatório contém:
• Sumário executivo e informações das usinas
• KPIs principais: geração, fator de capacidade, yield específico, gap vs meta
• Análise comparativa entre usinas (ranking, tendências)
• Análise de causas de variação de desempenho
• Análise de riscos e plano de ação
• Impacto financeiro estimado
• Conclusão executiva com recomendações

Atenciosamente,
Sistema de Monitoramento Solar – Maranhão
"""

    msg = MIMEMultipart()
    msg["From"] = gmail_from
    msg["To"] = RECIPIENT_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    # Anexar PDF
    with open(pdf_path, "rb") as f:
        pdf_data = f.read()
    attachment = MIMEApplication(pdf_data, _subtype="pdf")
    attachment.add_header("Content-Disposition", "attachment",
                          filename=os.path.basename(pdf_path))
    msg.attach(attachment)

    # Enviar via SMTP
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_from, app_password)
        server.sendmail(gmail_from, RECIPIENT_EMAIL, msg.as_string())

    print(f"  - Email enviado para {RECIPIENT_EMAIL}")
    return True
