import json
from werkzeug.security import generate_password_hash


def prompt_config():
    print("Configure admin user:")
    admin_name = input("Admin username: ").strip() or "admin"
    admin_password = input("Admin password: ")
    hashed_password = generate_password_hash(admin_password, method='scrypt')

    print("\nConfigure camera:")
    cam_url = input("Camera URL (default: /dev/video0): ").strip() or "/dev/video0"
    cam_fps = int(input("FPS (default: 30): ") or 30)
    cam_width = int(input("Width (default: 1280): ") or 1280)
    cam_height = int(input("Height (default: 720): ") or 720)

    print("\nConfigure TURN server:")
    turn_ip_port = input("TURN server IP:Port (e.g. 123.123.123.123:3478): ").strip()
    turn_username = input("TURN username: ").strip()
    turn_password = input("TURN password: ")

    print("\nApp settings:")
    secret_key = input("App secret key (used for session/auth): ").strip()

    return {
        "user": {
            "name": admin_name,
            "password": hashed_password
        },
        "camera": {
            "url": cam_url,
            "fps": cam_fps,
            "width": cam_width,
            "height": cam_height
        },
        "turn": {
            "url": f"turn:{turn_ip_port}",
            "username": turn_username,
            "password": turn_password
        },
        "app_config": {
            "secret_key": secret_key
        }
    }


def main():
    config = prompt_config()
    with open("config.json", "w") as f:
        json.dump(config, f, indent=2)
    print("\nConfig saved to config.json")


if __name__ == "__main__":
    main()
