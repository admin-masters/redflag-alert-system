# app/services/whatsapp.py
import urllib.parse

def deeplink(phone_e164: str, message: str) -> str:
    """
    Return a https://wa.me/ link that opens WhatsApp with a pre-populated message.
    """
    escaped = urllib.parse.quote_plus(message)
    return f"https://wa.me/{phone_e164}?text={escaped}"