import json
from pathlib import Path

CONFIG_PATH = Path("config.json")


def load_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Missing config file at {CONFIG_PATH}")
    with open(CONFIG_PATH) as f:
        return json.load(f)


conf = load_config()
