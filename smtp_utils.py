# smtp_utils.py

import os
from pathlib import Path
from dotenv import load_dotenv
import smtplib
from email.message import EmailMessage

# ─── load .env from the project root ─────────────────────────────────────────
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)
# ─────────────────────────────────────────────────────────────────────────────

def get_smtp_connection():
    """
    Reads SMTP settings from the environment and returns
    an authenticated SMTP connection using STARTTLS.
    """
    server = os.getenv("SMTP_SERVER")
    port   = int(os.getenv("SMTP_PORT", 587))
    user   = os.getenv("SMTP_USERNAME")
    pwd    = os.getenv("SMTP_PASSWORD")

    if not all([server, port, user, pwd]):
        raise RuntimeError("Missing one of SMTP_SERVER/PORT/USERNAME/PASSWORD in .env")

    smtp = smtplib.SMTP(server, port)
    smtp.ehlo()
    smtp.starttls()
    smtp.ehlo()
    smtp.login(user, pwd)
    return smtp

def send_email_via_smtp(
    subject: str,
    body: str,
    to_addresses: list[str],
    attachments: list[str] = []
):
    """
    Sends an email to the given addresses with the specified subject/body
    and optional file attachments.
    """
    # filter out any None or empty
    tos = [addr for addr in to_addresses if addr]
    if not tos:
        raise RuntimeError("No valid recipient addresses supplied")

    msg = EmailMessage()
    msg["From"]    = os.getenv("SMTP_USERNAME")
    msg["To"]      = ", ".join(tos)
    msg["Subject"] = subject
    msg.set_content(body)

    # Attach any files
    for path in attachments:
        with open(path, "rb") as f:
            data = f.read()
        filename = os.path.basename(path)
        maintype, subtype = "application", "octet-stream"
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=filename)

    smtp = get_smtp_connection()
    smtp.send_message(msg)
    smtp.quit()

# Optional smoke-test
if __name__ == "__main__":
    try:
        smtp = get_smtp_connection()
        print("✅ SMTP connection successful!")
        smtp.quit()
    except Exception as e:
        print("❌ SMTP connection failed:", e)
