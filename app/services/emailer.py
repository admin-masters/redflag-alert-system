# app/services/emailer.py
"""
Thin SES wrapper – for now just prints to console so you can run end-to-end
without AWS creds. Replace with boto3 or SendGrid later.
"""
import logging

log = logging.getLogger("emailer")

def send_email(to_email: str, subject: str, html_body: str) -> None:
    log.warning("EMAILER STUB → would send to %s: %s", to_email, subject)
    # In dev we just log. In prod, call SES/sendgrid here.