import os
from twilio.rest import Client

def send_whatsapp(body: str) -> None:
    sid = os.environ["TWILIO_ACCOUNT_SID"]
    token = os.environ["TWILIO_AUTH_TOKEN"]
    from_ = os.environ["TWILIO_WHATSAPP_FROM"]  # "whatsapp:+14155238886"
    to = os.environ["WHATSAPP_TO"]              # "whatsapp:+34..."

    client = Client(sid, token)
    client.messages.create(from_=from_, to=to, body=body)
