import os, base64, json, requests
from dotenv import load_dotenv

load_dotenv()
OKTA_DOMAIN = os.getenv("OKTA_DOMAIN")       # dev-123456.okta.com
OKTA_TOKEN  = os.getenv("OKTA_TOKEN")        # SSWS token

HEAD = {
    "Authorization": f"SSWS {OKTA_TOKEN}",
    "Accept":        "application/json",
    "Content-Type":  "application/json"
}

def create_user(email: str, first: str, last: str):
    """Create & activate a user in Okta."""
    url = f"https://{OKTA_DOMAIN}/api/v1/users?activate=true"
    body = {
        "profile": {
            "firstName": first,
            "lastName":  last,
            "email":     email,
            "login":     email
        },
        "credentials": { "password": { "value": "TempPassw0rd!" } }
    }
    r = requests.post(url, headers=HEAD, json=body)
    r.raise_for_status()
    return r.json()["id"]


#offboarding functions

def get_user_id_by_email(email: str) -> str:
    """Return Okta user-id (or raise) for the given login email."""
    url = f"https://{OKTA_DOMAIN}/api/v1/users"
    params = {"filter": f'profile.login eq "{email}"'}
    r = requests.get(url, headers=HEAD, params=params)
    r.raise_for_status()
    users = r.json()
    if not users:
        raise ValueError(f"No Okta user found for {email}")
    return users[0]["id"]


def deactivate_user(email: str) -> str:
    """Deactivate & disable sign-in for the given Okta account."""
    uid = get_user_id_by_email(email)
    url = f"https://{OKTA_DOMAIN}/api/v1/users/{uid}/lifecycle/deactivate"
    r = requests.post(url, headers=HEAD)
    r.raise_for_status()
    return uid