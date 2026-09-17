import sqlite3
import time
import re

import bcrypt
from pydantic import ValidationError

from database import DEFAULT_DB_PATH
from models.schemas import UserRegisterSchema
from utils.logger import logger


class AuthController:
    def __init__(self, db_name=DEFAULT_DB_PATH):
        self.db_name = db_name

    def register_user(self, username, email, password, role="user"):
        if role not in {"admin", "user"}:
            return False, "Invalid account type."
        if role == "admin" and email.lower() != f"admin{username.lower()}@gmail.com":
            return False, "Invalid admin registration details."
        try:
            validated = UserRegisterSchema(username=username, email=email, password=password)
        except ValidationError as exc:
            return False, f"Validation Error: {exc.errors()[0]['msg']}"

        hashed_pw = bcrypt.hashpw(validated.password.encode("utf-8"), bcrypt.gensalt())

        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, email, password_hash, role, login_attempts, locked_until) VALUES (?, ?, ?, ?, 0, 0)",
                (validated.username, validated.email, hashed_pw.decode("utf-8"), role),
            )
            conn.commit()
            conn.close()
            logger.info("Account Created: '%s' with email '%s'", validated.username, validated.email)
            return True, "User registered successfully."
        except sqlite3.IntegrityError as e:
            if "username" in str(e):
                return False, "Username already exists."
            else:
                return False, "Email already exists."

    def login_user(self, username, email, password, role=None):
        if not username or not email or not password:
            return False, "Username, email, and password are required."

        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT password_hash, login_attempts, locked_until, role FROM users WHERE username = ? AND email = ?",
            (username, email),
        )
        row = cursor.fetchone()

        if not row:
            conn.close()
            return False, "Invalid username, email, or password."

        password_hash, login_attempts, locked_until, stored_role = row
        if role is not None and role != stored_role:
            conn.close()
            return False, f"This account is registered as {stored_role}."
        current_time = time.time()

        # Check if account is locked
        if locked_until > current_time:
            conn.close()
            remaining_seconds = int(locked_until - current_time)
            return False, f"Account is locked. Try again in {remaining_seconds} seconds."

        # Check password
        if bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8")):
            # Reset login attempts on successful login
            cursor.execute(
                "UPDATE users SET login_attempts = 0, locked_until = 0 WHERE username = ?",
                (username,),
            )
            conn.commit()
            conn.close()
            logger.info("User Logged In: '%s' with email '%s'", username, email)
            return True, f"Login successful. Role: {stored_role}"
        else:
            # Increment failed login attempts
            new_attempts = login_attempts + 1
            if new_attempts >= 3:
                # Lock account for 30 seconds
                locked_until = current_time + 30
                cursor.execute(
                    "UPDATE users SET login_attempts = ?, locked_until = ? WHERE username = ?",
                    (new_attempts, locked_until, username),
                )
                conn.commit()
                conn.close()
                logger.warning("Account locked for user '%s' after 3 failed attempts", username)
                return False, "Account locked for 30 seconds due to 3 failed login attempts."
            else:
                cursor.execute(
                    "UPDATE users SET login_attempts = ? WHERE username = ?",
                    (new_attempts, username),
                )
                conn.commit()
                conn.close()
                remaining_attempts = 3 - new_attempts
                return False, f"Invalid username, email, or password. ({remaining_attempts} attempts remaining)"
        return False, "Invalid username, email, or password."

    def get_user_id(self, username):
        conn = sqlite3.connect(self.db_name)
        try:
            row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    def change_password(self, username, current_password, new_password):
        try:
            validated = UserRegisterSchema(username=username, email="change@example.com", password=new_password)
        except ValidationError as exc:
            return False, f"Validation Error: {exc.errors()[0]['msg']}"
        conn = sqlite3.connect(self.db_name)
        try:
            row = conn.execute("SELECT password_hash FROM users WHERE username = ?", (username,)).fetchone()
            if not row or not bcrypt.checkpw(current_password.encode("utf-8"), row[0].encode("utf-8")):
                return False, "Current password is incorrect."
            password_hash = bcrypt.hashpw(validated.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            conn.execute("UPDATE users SET password_hash = ? WHERE username = ?", (password_hash, username))
            conn.commit()
            return True, "Password changed successfully."
        finally:
            conn.close()

    def admin_change_password(self, username, new_password):
        try:
            validated = UserRegisterSchema(username=username, email="change@example.com", password=new_password)
        except ValidationError as exc:
            return False, f"Validation Error: {exc.errors()[0]['msg']}"
        password_hash = bcrypt.hashpw(validated.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        conn = sqlite3.connect(self.db_name)
        try:
            cursor = conn.execute("UPDATE users SET password_hash = ?, login_attempts = 0, locked_until = 0 WHERE username = ?", (password_hash, username))
            if cursor.rowcount != 1:
                return False, "Account not found."
            conn.commit()
            return True, "Account password changed successfully."
        finally:
            conn.close()

    def fetch_accounts(self):
        conn = sqlite3.connect(self.db_name)
        try:
            return conn.execute("SELECT username, email, role FROM users ORDER BY username").fetchall()
        finally:
            conn.close()
