import os
import sys
import tkinter as tk

from database import init_db
from views.login_view import LoginWindow
from views.tracker_view import TrackerWindow
from views.user_view import UserWindow


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)


def launch_main_app(root, username, role, user_id):
    """Clear the login window and load the main Inventory Tracker GUI."""
    for widget in root.winfo_children():
        widget.destroy()
    logout = lambda: show_login(root)
    TrackerWindow(root, username, logout) if role == "admin" else UserWindow(root, username, user_id, logout)


def show_login(root):
    for widget in root.winfo_children():
        widget.destroy()
    LoginWindow(root, on_login_success=lambda username, role, user_id: launch_main_app(root, username, role, user_id))


if __name__ == "__main__":
    db_path = init_db()
    root = tk.Tk()
    show_login(root)
    root.mainloop()
