import os
from persistence.model.app_config import AppConfig
import requests


def send_message(content):
    webhook = AppConfig.get().discord_webhook
    if not webhook:
        return
    
    data = {
        "content": content
    }

    try:
        response = requests.post(webhook, json=data)
        if response.status_code == 204:
            print("[INFO] Discord message sent.")
        else:
            print(f"[ERROR] Failed to send message: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"[ERROR] Exception during sending message: {e}")
