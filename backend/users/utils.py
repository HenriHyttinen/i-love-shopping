import requests
from django.conf import settings


def verify_recaptcha(token):
    if not settings.RECAPTCHA_SECRET_KEY:
        return True
    if not token:
        return False
    response = requests.post(
        "https://www.google.com/recaptcha/api/siteverify",
        data={"secret": settings.RECAPTCHA_SECRET_KEY, "response": token},
        timeout=5,
    )
    data = response.json()
    return data.get("success", False)
