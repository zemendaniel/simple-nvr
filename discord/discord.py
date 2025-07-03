import time

import requests


def send_message(content, webhook):
    if not webhook:
        return

    data = {"content": content}
    try:
        response = requests.post(webhook, json=data)
        if response.status_code == 204:
            print("[INFO] Discord message sent.")
        elif response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            wait_time = float(retry_after) if retry_after else 1.0
            print(f"[WARN] Rate limited by Discord. Retrying after {wait_time}s")
            time.sleep(wait_time)
            return send_message(content, webhook)  # retry once after wait
        else:
            print(f"[ERROR] Failed to send message: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"[ERROR] Exception during sending message: {e}")