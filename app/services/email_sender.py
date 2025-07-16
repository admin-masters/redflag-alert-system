import sendgrid, tomllib, pathlib, os
cfg = tomllib.load(pathlib.Path(os.environ["INDITECH_CFG"]) / "sendgrid.toml")
sg = sendgrid.SendGridAPIClient(cfg["API_KEY"])

def send_doctor_report(to, subject, html):
    sg.send({
        "from": {"email": cfg["FROM"], "name": "Inditech RFA"},
        "personalizations": [{"to": [{"email": to}]}],
        "subject": subject,
        "content": [{"type": "text/html", "value": html}]
    })