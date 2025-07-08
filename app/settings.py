# app/settings.py
import os
import tomllib
from pathlib import Path
from functools import lru_cache

# DEFAULT_CFG = "/var/www/inditech_secrets.toml"
DEFAULT_CFG = "inditech_secrets.toml"


@lru_cache
def get_cfg() -> dict:
    cfg_path = Path(os.getenv("INDITECH_CFG", DEFAULT_CFG))
    if not cfg_path.exists():
        raise RuntimeError(f"Secret file not found at {cfg_path}")
    return tomllib.loads(cfg_path.read_text())


# quick helpers
def db_url() -> str:
    return get_cfg()["database"]["url"]


def ses_apikey() -> str:
    return get_cfg()["ses"]["apikey"]


def wa_api_token() -> str:
    return get_cfg()["whatsapp"]["token"]