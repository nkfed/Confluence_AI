import shutil
import os

def setup_env():
    """Скрипт для первинного налаштування середовища (наприклад, копіювання .env.example)."""
    if not os.path.exists(".env"):
        shutil.copy(".env.example", ".env")
        print(".env file created from .env.example")
    else:
        print(".env already exists")

if __name__ == "__main__":
    setup_env()
