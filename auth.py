"""Simple local password gate for the web app (single-PC use, not hardened
multi-user security). Credentials are set by the user on first run and stored
locally as a salted hash."""

import json

from werkzeug.security import check_password_hash, generate_password_hash

from app_paths import DATA_DIR

CONFIG_PATH = DATA_DIR / "auth_config.json"
SECRET_KEY_PATH = DATA_DIR / "secret.key"


def is_configured():
    return CONFIG_PATH.exists()


def set_credentials(username, password):
    CONFIG_PATH.write_text(
        json.dumps({"username": username, "password_hash": generate_password_hash(password)}),
        encoding="utf-8",
    )


def verify(username, password):
    if not is_configured():
        return False
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return username == cfg["username"] and check_password_hash(cfg["password_hash"], password)


def get_username():
    if not is_configured():
        return None
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))["username"]


def get_secret_key():
    """A persistent random key so login sessions survive app restarts."""
    if SECRET_KEY_PATH.exists():
        return SECRET_KEY_PATH.read_bytes()
    import os
    key = os.urandom(32)
    SECRET_KEY_PATH.write_bytes(key)
    return key
