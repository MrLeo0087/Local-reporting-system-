"""
One-time script to create the very first Admin account.

Admins create Staff accounts through the API, but nothing creates the first
Admin — that has to be done directly against the database. Run this once:

    python create_first_admin.py

It will prompt for a name, email, and password, then insert an admin row
into the staff table (category and ward_no stay NULL for admins).
"""
import getpass
import sys

from app.database import SessionLocal
from app.models.staff import Staff
from app.auth.security import hash_password


def main():
    print("Create the first Admin account")
    print("-------------------------------")
    full_name = input("Full name: ").strip()
    email = input("Email: ").strip()
    password = getpass.getpass("Password (min 8 characters): ")

    if not full_name or not email:
        print("Full name and email are required.")
        sys.exit(1)
    if len(password) < 8:
        print("Password must be at least 8 characters.")
        sys.exit(1)

    db = SessionLocal()
    try:
        existing = db.query(Staff).filter(Staff.email == email).first()
        if existing:
            print(f"A staff account with email '{email}' already exists.")
            sys.exit(1)

        admin = Staff(
            full_name=full_name,
            email=email,
            password_hash=hash_password(password),
            role="admin",
            category=None,
            ward_no=None,
        )
        db.add(admin)
        db.commit()
        print(f"Admin account created for {email}. You can now log in at POST /staff/login.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
