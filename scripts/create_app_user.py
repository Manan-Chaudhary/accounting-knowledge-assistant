#!/usr/bin/env python3
"""Create or update an app_users row with a bcrypt password hash.

No default credentials are seeded into the repo (AU-62). Run deliberately:

  python -m scripts.create_app_user --email you@example.com --password '...' --role staff

Roles: staff | admin | team
  - staff/admin: firm users (Testing nav hidden)
  - team: Team 83 / reviewer accounts (Testing nav visible)
"""

from __future__ import annotations

import argparse
import sys

from app.auth import ALLOWED_ROLES
from app.auth.passwords import hash_password
from app.db.database import SessionLocal
from app.db.models import AppUser


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or update an app user.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--role", default="staff", choices=sorted(ALLOWED_ROLES))
    parser.add_argument(
        "--inactive",
        action="store_true",
        help="Create/update the account as disabled.",
    )
    args = parser.parse_args()

    email = args.email.strip().lower()
    if not email or "@" not in email:
        print("Invalid email.", file=sys.stderr)
        return 1
    if not args.password:
        print("Password must not be empty.", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        user = db.query(AppUser).filter(AppUser.email == email).one_or_none()
        if user is None:
            user = AppUser(email=email)
            db.add(user)
            action = "created"
        else:
            action = "updated"

        user.password_hash = hash_password(args.password)
        user.role = args.role
        user.is_active = not args.inactive
        db.commit()
        db.refresh(user)
        print(f"{action}: id={user.id} email={user.email} role={user.role} active={user.is_active}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
