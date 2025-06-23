import os

import requests


def send_message(content):
    data = {
        "content": content
    }

    try:
        response = requests.post(os.environ.get('DISCORD'), json=data)
        if response.status_code == 204:
            print("[INFO] Discord message sent.")
        else:
            print(f"[ERROR] Failed to send message: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"[ERROR] Exception during sending message: {e}")
