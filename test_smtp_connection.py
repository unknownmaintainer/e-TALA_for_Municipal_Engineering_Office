# Utility to test Brevo SMTP Connection
import smtplib
import ssl
import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=env_path)

host = os.getenv('EMAIL_HOST', 'smtp-relay.brevo.com')
port = int(os.getenv('EMAIL_PORT', '587'))
user = os.getenv('EMAIL_HOST_USER')
password = os.getenv('EMAIL_HOST_PASSWORD')
from_email = os.getenv('DEFAULT_FROM_EMAIL', user or 'noreply@carigara.gov.ph')
to_email = os.getenv('TEST_RECIPIENT_EMAIL', user or 'admin@carigara.gov.ph')

try:
    context = ssl.create_default_context()
    server = smtplib.SMTP(host, port, timeout=15)
    server.ehlo()
    server.starttls(context=context)
    server.ehlo()
    server.login(user, password)
    message = f"From: {from_email}\r\nTo: {to_email}\r\nSubject: eTala SMTP Test Confirmation\r\n\r\nHello from eTala Engineering Office System! This confirms SMTP is active and working."
    sender_addr = user or from_email
    server.sendmail(sender_addr, [to_email], message)
    server.quit()
    print(f"SUCCESS: Test email successfully sent to {to_email}!")
except Exception as e:
    print(f"ERROR: SMTP Test failed: {e}")
