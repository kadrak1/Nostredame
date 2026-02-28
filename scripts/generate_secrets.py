"""Generate secure secrets for .env file.

Run: python scripts/generate_secrets.py
"""

import secrets

from cryptography.fernet import Fernet


def main():
    jwt_secret = secrets.token_urlsafe(32)
    encryption_key = Fernet.generate_key().decode()

    print("=" * 50)
    print("Generated secrets for .env")
    print("=" * 50)
    print()
    print(f"JWT_SECRET_KEY={jwt_secret}")
    print(f"ENCRYPTION_KEY={encryption_key}")
    print()
    print("Copy these values to your .env file.")
    print("NEVER share or commit these secrets!")
    print("=" * 50)


if __name__ == "__main__":
    main()
