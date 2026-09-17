import os
import sqlite3
from pathlib import Path

from utils.logger import logger


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_DB_PATH = PROJECT_ROOT / "lab_tracker.db"


def init_db(db_name=None):
    db_path = Path(db_name) if db_name else DEFAULT_DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user')),
                login_attempts INTEGER DEFAULT 0,
                locked_until REAL DEFAULT 0
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS borrow_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inventory_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                student_name TEXT NOT NULL,
                student_id TEXT NOT NULL,
                section TEXT NOT NULL,
                course TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'Borrowed'
                    CHECK (status IN ('Borrowed', 'Missing', 'Returned')),
                borrowed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                returned_at TIMESTAMP,
                FOREIGN KEY (inventory_id) REFERENCES inventory(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inventory_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                student_name TEXT NOT NULL,
                student_id TEXT NOT NULL,
                section TEXT NOT NULL,
                course TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                reservation_date TEXT NOT NULL,
                reservation_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending'
                    CHECK (status IN ('Pending', 'On Hold', 'Approved', 'Rejected')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (inventory_id) REFERENCES inventory(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )

        user_columns = {row[1] for row in cursor.execute("PRAGMA table_info(users)")}
        if "role" not in user_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
        borrow_columns = {row[1] for row in cursor.execute("PRAGMA table_info(borrow_records)")}
        if "quantity" not in borrow_columns:
            cursor.execute("ALTER TABLE borrow_records ADD COLUMN quantity INTEGER NOT NULL DEFAULT 1")
        reservation_columns = {row[1] for row in cursor.execute("PRAGMA table_info(reservations)")}
        if "quantity" not in reservation_columns:
            cursor.execute("ALTER TABLE reservations ADD COLUMN quantity INTEGER NOT NULL DEFAULT 1")
        reservation_sql = cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'reservations'"
        ).fetchone()[0]
        if "'On Hold'" not in reservation_sql:
            cursor.execute(
                """
                CREATE TABLE reservations_migrated (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    inventory_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    student_name TEXT NOT NULL,
                    student_id TEXT NOT NULL,
                    section TEXT NOT NULL,
                    course TEXT NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 1,
                    reservation_date TEXT NOT NULL,
                    reservation_time TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Pending'
                        CHECK (status IN ('Pending', 'On Hold', 'Approved', 'Rejected')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (inventory_id) REFERENCES inventory(id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
                """
            )
            cursor.execute(
                """
                INSERT INTO reservations_migrated
                    (id, inventory_id, user_id, student_name, student_id, section, course,
                     quantity, reservation_date, reservation_time, status, created_at)
                SELECT id, inventory_id, user_id, student_name, student_id, section, course,
                       quantity, reservation_date, reservation_time, status, created_at
                FROM reservations
                """
            )
            cursor.execute("DROP TABLE reservations")
            cursor.execute("ALTER TABLE reservations_migrated RENAME TO reservations")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT NOT NULL,
                category TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                availability_status TEXT NOT NULL DEFAULT 'Available'
                    CHECK (availability_status IN ('Available', 'On Hold')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

        inventory_columns = {row[1] for row in cursor.execute("PRAGMA table_info(inventory)")}
        if "availability_status" not in inventory_columns:
            cursor.execute(
                "ALTER TABLE inventory ADD COLUMN availability_status TEXT NOT NULL DEFAULT 'Available'"
            )

        conn.commit()
        conn.close()
        logger.info("Database initialized successfully at %s", db_path)
        return str(db_path)
    except sqlite3.Error as exc:
        logger.error("Error initializing database: %s", exc)
        raise
