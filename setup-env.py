import secrets

secret_key = secrets.token_hex(32)

discord_webhook = input("Discord webhook (or leave empty for no notifications):\n")

with open(".env", "w", encoding="utf-8") as f:
    f.write(f"""
APP_NAME=simple-nvr
SECRET_KEY={secret_key}
DISCORD={discord_webhook}
""")
