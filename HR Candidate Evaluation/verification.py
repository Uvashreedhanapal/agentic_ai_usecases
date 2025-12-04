import os
import requests
from dotenv import load_dotenv

load_dotenv()
VERIFICATION_API_URL = os.getenv('VERIFICATION_API_URL')
VERIFICATION_API_KEY = os.getenv('VERIFICATION_API_KEY')

def mock_verify_identity(name: str, email: str, phone: str):
    return {
        "identity_check": "passed" if email else "incomplete",
        "email_domain": email.split('@')[-1] if email and '@' in email else None,
        "flagged": False,
        "notes": "mocked verification"
    }

def provider_verify_identity(name: str, email: str, phone: str):
    if not VERIFICATION_API_URL or not VERIFICATION_API_KEY:
        raise RuntimeError("Real verification provider not configured")

    payload = {"name": name, "email": email, "phone": phone}
    headers = {"Authorization": f"Bearer {VERIFICATION_API_KEY}"}

    resp = requests.post(VERIFICATION_API_URL + "/verify/identity", json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()
