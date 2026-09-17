import tkinter as tk
from tkinter import ttk, messagebox

from controllers.tracker_controller import TrackerController


BG = "#F4FAF5"
PANEL = "#FFFFFF"
FOREST = "#1F5D3A"
GREEN = "#2E7D50"
MINT = "#E4F2E7"
INK = "#193528"


class UserWindow:
    def __init__(self, root, username, user_id, on_logout):
        self.root, self.user_id = root, user_id
        self.controller = TrackerController()
        self.selected_item_id = None
        root.title(f"Campus Inventory | User: {username}")
        root.geometry("980x720")
        root.configure(bg=BG)
        style = ttk.Style(root); style.theme_use("clam")
        style.configure("User.Treeview", background=PANEL, fieldbackground=PANEL, foreground=INK, rowheight=31, borderwidth=0, font=("Segoe UI", 10))
        style.configure("User.Treeview.Heading", background=FOREST, foreground="white", relief="flat", font=("Segoe UI", 10, "bold"))
        style.map("User.Treeview", background=[("selected", MINT)], foreground=[("selected", INK)])
        header = tk.Frame(root, bg=FOREST, height=68); header.pack(fill="x")
        tk.Label(header, text="BORROW EQUIPMENT", bg=FOREST, fg="white", font=("Segoe UI", 17, "bold")).pack(side="left", padx=24, pady=18)
        tk.Label(header, text="Select an item and choose an action", bg=FOREST, fg="#CBE6D1", font=("Segoe UI", 10)).pack(side="left")
        tk.Button(header, text="Logout", command=on_logout, bg="#B83B3B", fg="white", relief="flat", width=10).pack(side="right", padx=22)
        frame = tk.LabelFrame(root, text="  Available inventory  ", padx=8, pady=8, bg=PANEL, fg=FOREST, font=("Segoe UI", 10, "bold"))
        frame.pack(fill="both", expand=True, padx=16, pady=14)
        self.tree = ttk.Treeview(frame, columns=("id", "name", "category", "stock", "status"), show="headings", style="User.Treeview")
        for key, heading, width in (("id", "ID", 50), ("name", "Item name", 280), ("category", "Category", 180), ("stock", "Available", 100), ("status", "Status", 120)):
            self.tree.heading(key, text=heading); self.tree.column(key, width=width)
        self.tree.pack(fill="both", expand=True); self.tree.bind("<<TreeviewSelect>>", lambda _: self.select_item())
        form = tk.LabelFrame(root, text="  Borrow or reserve  ", padx=10, pady=10, bg=PANEL, fg=FOREST, font=("Segoe UI", 10, "bold"))
        form.pack(fill="x", padx=16, pady=(0, 16))
        self.fields = {}
        for column, (label, key) in enumerate((("Student name", "name"), ("Student ID number", "student_id"), ("Section", "section"), ("Course", "course"), ("Quantity", "quantity"))):
            tk.Label(form, text=label, bg=PANEL, fg=INK, font=("Segoe UI", 9, "bold")).grid(row=0, column=column, sticky="w", padx=5)
            entry = tk.Entry(form, width=21, relief="flat", bg="#F0F7F1", fg=INK, insertbackground=FOREST); entry.grid(row=1, column=column, padx=5, pady=3, ipady=4); self.fields[key] = entry
        self.missing = tk.BooleanVar(value=False)
        tk.Checkbutton(form, text="Mark as missing", variable=self.missing, bg=PANEL, fg=INK, activebackground=PANEL).grid(row=2, column=0, sticky="w", padx=5, pady=5)
        tk.Button(form, text="Borrow selected item", command=self.borrow, bg=GREEN, fg="white", relief="flat", width=20).grid(row=2, column=4, padx=5, pady=5, ipady=3)
        tk.Label(form, text="Reserve date (YYYY-MM-DD)", bg=PANEL, fg=INK).grid(row=3, column=0, sticky="w", padx=5)
        tk.Label(form, text="Reserve time (HH:MM)", bg=PANEL, fg=INK).grid(row=3, column=1, sticky="w", padx=5)
        self.reservation_date = tk.Entry(form, width=21, relief="flat", bg="#F0F7F1", fg=INK, insertbackground=FOREST); self.reservation_date.grid(row=4, column=0, padx=5, pady=3, ipady=4)
        self.reservation_time = tk.Entry(form, width=21, relief="flat", bg="#F0F7F1", fg=INK, insertbackground=FOREST); self.reservation_time.grid(row=4, column=1, padx=5, pady=3, ipady=4)
        self.reserve_button = tk.Button(form, text="Request reservation", command=self.reserve, bg="#4F8F62", fg="white", relief="flat", width=20)
        self.reserve_button.grid(row=4, column=4, padx=5, pady=3, ipady=3)
        self.load_inventory()

    def load_inventory(self):
        for row in self.tree.get_children(): self.tree.delete(row)
        for item_id, name, category, quantity, _price, availability in self.controller.fetch_all_inventory():
            status = availability if availability == "On Hold" else ("Available" if quantity > 0 else "Out of stock")
            self.tree.insert("", "end", values=(item_id, name, category, quantity, status))

    def select_item(self):
        selected = self.tree.selection(); self.selected_item_id = self.tree.item(selected[0], "values")[0] if selected else None
        self.reserve_button.config(state="disabled" if selected and self.tree.item(selected[0], "values")[4] == "On Hold" else "normal")

    def borrow(self):
        if self.selected_item_id is None:
            messagebox.showwarning("Select an item", "Select an inventory item first."); return
        values = {key: field.get().strip() for key, field in self.fields.items()}
        try:
            quantity = int(values["quantity"])
        except ValueError:
            messagebox.showerror("Invalid quantity", "Quantity must be a positive whole number."); return
        result = self.controller.borrow_item(self.selected_item_id, self.user_id, values["name"], values["student_id"], values["section"], values["course"], "Missing" if self.missing.get() else "Borrowed", quantity)
        if result[0]:
            messagebox.showinfo("Saved", result[1]); self.load_inventory()
            for field in self.fields.values(): field.delete(0, tk.END)
        else: messagebox.showerror("Could not borrow", result[1])

    def reserve(self):
        if self.selected_item_id is None:
            messagebox.showwarning("Select an item", "Select an inventory item first."); return
        values = {key: field.get().strip() for key, field in self.fields.items()}
        try:
            quantity = int(values["quantity"])
        except ValueError:
            messagebox.showerror("Invalid quantity", "Quantity must be a positive whole number."); return
        result = self.controller.create_reservation(self.selected_item_id, self.user_id, values["name"], values["student_id"], values["section"], values["course"], self.reservation_date.get().strip(), self.reservation_time.get().strip(), quantity)
        if result[0]: messagebox.showinfo("Reservation", result[1])
        else: messagebox.showerror("Could not reserve", result[1])