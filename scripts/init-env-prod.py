#!/usr/bin/env python3
"""Génère deploy/.env.prod à partir de env.prod.example avec secrets aléatoires."""
from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "deploy" / "env.prod.example"
OUTPUT = ROOT / "deploy" / ".env.prod"


def token(n: int = 32) -> str:
    return secrets.token_urlsafe(n)


def set_line(content: str, key: str, value: str) -> str:
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            return "\n".join(lines) + "\n"
    lines.append(f"{key}={value}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialiser deploy/.env.prod pour la production")
    parser.add_argument("--domain", default="localhost", help="Domaine public (certificat SSL)")
    parser.add_argument("--http-port", default="80", help="Port HTTP (8080 pour test local)")
    parser.add_argument("--force", action="store_true", help="Écraser un .env.prod existant")
    args = parser.parse_args()

    if OUTPUT.exists() and not args.force:
        print(f"Existe déjà : {OUTPUT}  (utilisez --force pour regénérer)", file=sys.stderr)
        return 1

    if not EXAMPLE.is_file():
        print(f"Modèle introuvable : {EXAMPLE}", file=sys.stderr)
        return 1

    db_password = token(24)
    content = EXAMPLE.read_text(encoding="utf-8")
    replacements = {
        "CHANGE_ME_STRONG_PASSWORD": db_password,
        "CHANGE_ME_32_CHARS_MINIMUM________": token(32),
        "CHANGE_ME_REFRESH________________": token(32),
        "CHANGE_ME_32_CHARS_ENCRYPTION_KEY!!": token(24)[:32].ljust(32, "!"),
        "CHANGE_ME_QR_HMAC___________________": token(32),
    }
    for old, new in replacements.items():
        content = content.replace(old, new)

    port = args.http_port.strip()
    domain = args.domain.strip()
    if port == "80" and domain != "localhost":
        cors = f"https://{domain}"
    elif port == "80":
        cors = "http://localhost"
    else:
        cors = f"http://localhost:{port}"

    content = set_line(content, "HTTP_PORT", port)
    content = set_line(content, "CORS_ORIGINS", cors)
    content = set_line(content, "DOMAIN", domain)

    OUTPUT.write_text(content, encoding="utf-8")
    print(f"Créé : {OUTPUT}")
    print(f"  Domaine   : {domain}")
    print(f"  Port HTTP : {port}")
    print(f"  CORS      : {cors}")
    print("\nÉditez SMTP_* si besoin, puis lancez deploy-prod.sh ou docker compose.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
