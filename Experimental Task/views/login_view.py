import re
import time
import tkinter as tk
from tkinter import messagebox

from controllers.auth_controller import AuthController


GREEN = "#4CAF50"
DARK_GREEN = "#2E7D32"
PALE_GREEN = "#E8F5E9"
INK = "#193528"
MINT = "#F4FAF5"
WHITE = "#FFFFFF"


class LoginWindow:
    def __init__(self, root, on_login_success):
        self.root = root
        self.on_login_success = on_login_success
        self.auth = AuthController()
        self.password_visible = False
        self.is_register_mode = False
        self.role = tk.StringVar(value="user")
        self.lockout_end_time = None
        self.timer_id = None

        root.title("System Auth - Login")
        root.geometry("420x540")
        root.resizable(False, False)
        root.configure(bg=MINT)

        tk.Label(root, text="CAMPUS INVENTORY", bg=MINT, fg=DARK_GREEN, font=("Segoe UI", 21, "bold")).pack(pady=(24, 3))
        self.mode_label = tk.Label(root, text="LOGIN", bg=MINT, fg=DARK_GREEN, font=("Segoe UI", 11, "bold"))
        self.mode_label.pack(pady=(0, 8))
        form = tk.Frame(root, bg=WHITE, padx=26, pady=18, highlightbackground="#D5E8D8", highlightthickness=1)
        form.pack(fill="x", padx=26)
        tk.Label(form, text="Username", bg=WHITE, fg=INK, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.entry_user = tk.Entry(form, width=40, relief="flat", bg="#F1F7F2", fg=INK, insertbackground=DARK_GREEN)
        self.entry_user.pack(fill="x", pady=(4, 10), ipady=5)

        tk.Label(form, text="Email", bg=WHITE, fg=INK, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.entry_email = tk.Entry(form, width=40, relief="flat", bg="#F1F7F2", fg=INK, insertbackground=DARK_GREEN)
        self.entry_email.pack(fill="x", pady=(4, 10), ipady=5)

        tk.Label(form, text="Password", bg=WHITE, fg=INK, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        pass_frame = tk.Frame(form, bg=WHITE)
        pass_frame.pack(fill="x", pady=(4, 8))
        self.entry_pass = tk.Entry(pass_frame, show="*", width=31, relief="flat", bg="#F1F7F2", fg=INK, insertbackground=DARK_GREEN)
        self.entry_pass.pack(side=tk.LEFT, fill="x", expand=True, ipady=5)
        self.toggle_btn = tk.Button(pass_frame, text="Show", command=self.toggle_password, width=6, bg="#DCEFE0", fg=DARK_GREEN, relief="flat")
        self.toggle_btn.pack(side=tk.LEFT, padx=(6, 0), ipady=2)

        role_frame = tk.LabelFrame(form, text="Account type", padx=8, pady=2, bg=WHITE, fg=DARK_GREEN, font=("Segoe UI", 9, "bold"))
        role_frame.pack(fill="x", pady=(5, 0))
        tk.Radiobutton(role_frame, text="User", variable=self.role, value="user", bg=WHITE, activebackground=WHITE, fg=INK).pack(side=tk.LEFT, padx=12)
        tk.Radiobutton(role_frame, text="Admin", variable=self.role, value="admin", bg=WHITE, activebackground=WHITE, fg=INK).pack(side=tk.LEFT, padx=12)

        btn_frame = tk.Frame(form, bg=WHITE)
        btn_frame.pack(pady=(14, 2))
        self.btn_login = tk.Button(btn_frame, text="Login", command=self.handle_login, bg=GREEN, fg="white", width=12, relief="flat", font=("Segoe UI", 10, "bold"))
        self.btn_login.pack(side=tk.LEFT, padx=5, ipady=3)
        self.btn_register = tk.Button(btn_frame, text="Register", command=self.switch_to_register, bg=DARK_GREEN, fg="white", width=12, relief="flat", font=("Segoe UI", 10, "bold"))
        self.btn_register.pack(side=tk.LEFT, padx=5, ipady=3)
        self.btn_submit = tk.Button(btn_frame, text="Register", command=self.handle_register, bg=GREEN, fg="white", width=12, relief="flat", font=("Segoe UI", 10, "bold"))
        self.btn_back = tk.Button(btn_frame, text="Back to Login", command=self.switch_to_login, bg=DARK_GREEN, fg="white", width=12, relief="flat", font=("Segoe UI", 10, "bold"))

        self.timer_label = tk.Label(root, text="", bg=MINT, font=("Segoe UI", 10, "bold"), fg="#c62828")
        self.timer_label.pack(pady=5)

    def switch_to_register(self):
        self.is_register_mode = True
        self.password_visible = False
        self.root.title("System Auth - Register")
        self.mode_label.config(text="REGISTER ACCOUNT", fg=DARK_GREEN)
        self.entry_pass.config(show="*")
        self.toggle_btn.config(text="Show")
        self.btn_login.pack_forget()
        self.btn_register.pack_forget()
        self.btn_submit.pack(side=tk.LEFT, padx=5)
        self.btn_back.pack(side=tk.LEFT, padx=5)

    def switch_to_login(self):
        self.is_register_mode = False
        self.password_visible = False
        self.root.title("System Auth - Login")
        self.mode_label.config(text="LOGIN", fg=DARK_GREEN)
        self.btn_login.pack(side=tk.LEFT, padx=5)
        self.btn_register.pack(side=tk.LEFT, padx=5)
        self.btn_submit.pack_forget()
        self.btn_back.pack_forget()
        self.entry_user.delete(0, tk.END)
        self.entry_email.delete(0, tk.END)
        self.entry_pass.delete(0, tk.END)
        self.entry_pass.config(show="*")
        self.toggle_btn.config(text="Show")
        self.cancel_timer()

    def toggle_password(self):
        self.password_visible = not self.password_visible
        self.entry_pass.config(show="" if self.password_visible else "*")
        self.toggle_btn.config(text="Hide" if self.password_visible else "Show")

    def cancel_timer(self):
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None
        self.timer_label.config(text="")

    def update_timer(self):
        if self.lockout_end_time is None:
            return
        remaining = self.lockout_end_time - time.time()
        if remaining > 0:
            self.timer_label.config(text=f"Account locked. Try again in {int(remaining)} seconds")
            self.btn_login.config(state="disabled")
            self.timer_id = self.root.after(1000, self.update_timer)
        else:
            self.timer_label.config(text="Account unlocked. You can login now.")
            self.btn_login.config(state="normal")
            self.lockout_end_time = None
            self.timer_id = self.root.after(3000, lambda: self.timer_label.config(text=""))

    def start_lockout_timer(self, seconds_remaining):
        self.cancel_timer()
        self.lockout_end_time = time.time() + seconds_remaining
        self.update_timer()

    def handle_login(self):
        username = self.entry_user.get().strip()
        email = self.entry_email.get().strip()
        password = self.entry_pass.get().strip()
        if not username or not email or not password:
            messagebox.showerror("Login Failed", "Username, email, and password are all required.")
            return
        success, message = self.auth.login_user(username, email, password, self.role.get())
        if success:
            self.cancel_timer()
            self.on_login_success(username, self.role.get(), self.auth.get_user_id(username))
            return
        match = re.search(r"(\d+)\s*seconds", message)
        if match and "locked" in message.lower():
            self.start_lockout_timer(int(match.group(1)))
        messagebox.showerror("Login Failed", message)

    def handle_register(self):
        username = self.entry_user.get().strip()
        email = self.entry_email.get().strip()
        password = self.entry_pass.get().strip()
        if not username or not email or not password:
            messagebox.showerror("Registration Failed", "Username, email, and password are all required.")
            return
        success, message = self.auth.register_user(username, email, password, self.role.get())
        if success:
            messagebox.showinfo("Registration Successful", message)
            self.switch_to_login()
        else:
            messagebox.showerror("Registration Failed", message)