import os
import sys
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, parseaddr

def test_brevo_smtp(host, port, user, password, from_email, to_email):
    print(f"Testing Brevo SMTP connection to {host}:{port} with user {user}...")
    try:
        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=10)
        else:
            server = smtplib.SMTP(host, port, timeout=10)
            server.ehlo()
            server.starttls()
            server.ehlo()
        
        print("Connected & TLS established. Authenticating...")
        server.login(user, password)
        print("Authentication SUCCESSFUL!")

        parsed_name, clean_from = parseaddr(from_email)
        sender_header = formataddr((parsed_name, clean_from)) if parsed_name else clean_from

        msg = MIMEMultipart('alternative')
        msg['Subject'] = "eTala Test Email"
        msg['From'] = sender_header
        msg['To'] = to_email
        msg.attach(MIMEText("This is a test email from eTala diagnostic suite.", 'plain'))

        print(f"Sending from {clean_from} to {to_email}...")
        server.sendmail(clean_from, [to_email], msg.as_string())
        server.quit()
        print("Email sent successfully via Brevo SMTP!")
        return True
    except Exception as e:
        print(f"SMTP Error: {type(e).__name__}: {e}")
        return False

if __name__ == '__main__':
    print("Brevo SMTP Test Utility")
