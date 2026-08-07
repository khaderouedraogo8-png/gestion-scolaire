#!/usr/bin/env python3
"""Test de charge headless — usage :
  python scripts/run_load_test.py [--host URL] [--users N] [--duration 30s]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCUSTFILE = ROOT / "locustfile.py"


def main() -> int:
    parser = argparse.ArgumentParser(description="Locust headless contre la stack prod/dev")
    parser.add_argument("--host", default="http://localhost:8080", help="URL de base")
    parser.add_argument("--users", type=int, default=10, help="Utilisateurs simultanes")
    parser.add_argument("--spawn-rate", type=int, default=2, help="Montee en charge / sec")
    parser.add_argument("--duration", default="30s", help="Duree du test")
    args = parser.parse_args()

    try:
        import locust  # noqa: F401
    except ImportError:
        print("Installation de locust…")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "locust", "-q"])

    cmd = [
        sys.executable,
        "-m",
        "locust",
        "-f",
        str(LOCUSTFILE),
        f"--host={args.host}",
        "--headless",
        "-u",
        str(args.users),
        "-r",
        str(args.spawn_rate),
        "-t",
        args.duration,
    ]
    print(f"Lancement : {' '.join(cmd)}")
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
