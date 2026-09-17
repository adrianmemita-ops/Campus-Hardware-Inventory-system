import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from controllers.tracker_controller import TrackerController
from controllers.auth_controller import AuthController


BG = "#F4FAF5"
PANEL = "#FFFFFF"
FOREST = "#1F5D3A"
GREEN = "#2E7D50"
MINT = "#E4F2E7"
INK = "#193528"


class TrackerWindow:
    def __init__(self, root, username, on_logout):
        self.root, self.controller = root, TrackerController()
        self.username, self.auth, self.on_logout = username, AuthController(), on_logout
        self.selected_item_id = None
        root.title(f"Campus Inventory | Admin: {username}"); root.geometry("1040x720"); root.configure(bg=BG)
        style = ttk.Style(root); style.theme_use("clam")
        style.configure("Modern.Treeview", background=PANEL, fieldbackground=PANEL, foreground=INK, rowheight=30, borderwidth=0, font=("Segoe UI", 10))
        style.configure("Modern.Treeview.Heading", background=FOREST, foreground="white", relief="flat", font=("Segoe UI", 10, "bold"))
        style.map("Modern.Treeview", background=[("selected", MINT)], foreground=[("selected", INK)])
        header = tk.Frame(root, bg=FOREST, height=68); header.pack(fill="x")
        tk.Label(header, text="ADMIN INVENTORY", bg=FOREST, fg="white", font=("Segoe UI", 17, "bold")).pack(side="left", padx=24, pady=18)
        tk.Label(header, text=f"Signed in as {username}", bg=FOREST, fg="#CBE6D1", font=("Segoe UI", 10)).pack(side="left")
        tk.Button(header, text="Logout", command=on_logout, bg="#B83B3B", fg="white", relief="flat", width=10).pack(side="right", padx=22)
        form = tk.LabelFrame(root, text="  Add or edit inventory  ", padx=14, pady=12, bg=PANEL, fg=FOREST, font=("Segoe UI", 10, "bold")); form.pack(fill="x", padx=18, pady=16)
        self.entries = {}
        for column, (label, key) in enumerate((("Item name", "name"), ("Category", "category"), ("Quantity in stock", "quantity"), ("Unit price", "price"))):
            tk.Label(form, text=label, bg=PANEL, fg=INK, font=("Segoe UI", 9, "bold")).grid(row=0, column=column, sticky="w", padx=7)
            entry = tk.Entry(form, width=22, relief="flat", bg="#F0F7F1", fg=INK, insertbackground=FOREST); entry.grid(row=1, column=column, padx=7, pady=(4, 10), ipady=5); self.entries[key] = entry
        tk.Button(form, text="Add item", command=self.add_item, bg=GREEN, fg="white", relief="flat", width=13).grid(row=2, column=0, padx=7, ipady=3)
        tk.Button(form, text="Update selected", command=self.update_item, bg="#4F8F62", fg="white", relief="flat", width=15).grid(row=2, column=1, padx=7, ipady=3)
        tk.Button(form, text="Clear", command=self.clear_form, bg=MINT, fg=FOREST, relief="flat", width=13).grid(row=2, column=2, padx=7, ipady=3)
        tk.Button(form, text="Delete selected", command=self.delete_item, bg="#B83B3B", fg="white", relief="flat", width=15).grid(row=2, column=3, padx=7, ipady=3)
        table_frame = tk.LabelFrame(root, text="  Inventory  ", padx=7, pady=7, bg=PANEL, fg=FOREST, font=("Segoe UI", 10, "bold")); table_frame.pack(fill="both", expand=True, padx=18)
        columns = ("id", "name", "category", "quantity", "status", "price", "total"); self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", style="Modern.Treeview")
        for key, heading, width in zip(columns, ("ID", "Item name", "Category", "Quantity", "Stock status", "Unit price", "Asset value"), (45, 220, 150, 75, 110, 110, 130)):
            self.tree.heading(key, text=heading); self.tree.column(key, width=width)
        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True); scroll.pack(side="right", fill="y"); self.tree.bind("<<TreeviewSelect>>", self.select_item)
        bottom = tk.Frame(root, bg=BG); bottom.pack(fill="x", padx=18, pady=14)
        self.total_label = tk.Label(bottom, text="Total asset value: 0.00", bg=BG, fg=FOREST, font=("Segoe UI", 12, "bold")); self.total_label.pack(side="left")
        for text, command in (("Borrower records", self.show_borrowers), ("Reservations", self.show_reservations), ("Account passwords", self.manage_passwords), ("Export CSV", self.export_csv)):
            tk.Button(bottom, text=text, command=command, bg=MINT, fg=FOREST, relief="flat").pack(side="left", padx=4, ipady=3)
        tk.Button(bottom, text="Hold / Release selected", command=self.toggle_hold, bg=MINT, fg=FOREST, relief="flat").pack(side="left", padx=4, ipady=3)
        self.load_inventory()

    def load_inventory(self):
        for row in self.tree.get_children(): self.tree.delete(row)
        for item_id, name, category, quantity, price, availability in self.controller.fetch_all_inventory():
            status = availability if availability == "On Hold" else ("In stock" if quantity > 0 else "Out of stock")
            self.tree.insert("", "end", values=(item_id, name, category, quantity, status, f"₱{price:,.2f}", f"₱{quantity * price:,.2f}"))
        self.total_label.config(text=f"Total asset value: {self.controller.get_total_asset_value():,.2f}")

    def select_item(self, _event=None):
        selected = self.tree.selection()
        if selected:
            values = self.tree.item(selected[0], "values"); self.selected_item_id = values[0]
            for key, value in zip(("name", "category", "quantity", "price"), (values[1], values[2], values[3], values[5].replace("₱", ""))):
                self.entries[key].delete(0, tk.END); self.entries[key].insert(0, value)

    def read_form(self):
        try: return self.entries["name"].get().strip(), self.entries["category"].get().strip(), int(self.entries["quantity"].get()), float(self.entries["price"].get())
        except ValueError: raise ValueError("Quantity must be a whole number and unit price must be numeric.")

    def add_item(self):
        try: result = self.controller.add_inventory(*self.read_form())
        except ValueError as exc: messagebox.showerror("Validation error", str(exc)); return
        if result[0]: self.clear_form(); self.load_inventory()
        else: messagebox.showerror("Could not add item", result[1])

    def update_item(self):
        if self.selected_item_id is None: messagebox.showwarning("Select an item", "Select an inventory row first."); return
        try: result = self.controller.update_inventory(self.selected_item_id, *self.read_form())
        except ValueError as exc: messagebox.showerror("Validation error", str(exc)); return
        if result[0]: self.clear_form(); self.load_inventory()
        else: messagebox.showerror("Could not update item", result[1])

    def clear_form(self):
        self.selected_item_id = None
        for entry in self.entries.values(): entry.delete(0, tk.END)
        self.tree.selection_remove(self.tree.selection())

    def delete_item(self):
        if self.selected_item_id is None:
            messagebox.showwarning("Select an item", "Select an inventory row first.")
            return
        item_name = self.tree.item(self.tree.selection()[0], "values")[1]
        if not messagebox.askyesno("Confirm deletion", f"Delete '{item_name}' from inventory?"):
            return
        result = self.controller.delete_inventory(self.selected_item_id)
        if result[0]:
            messagebox.showinfo("Deleted", result[1])
            self.clear_form()
            self.load_inventory()
        else:
            messagebox.showerror("Could not delete item", result[1])

    def toggle_hold(self):
        if self.selected_item_id is None:
            messagebox.showwarning("Select an item", "Select an inventory row first.")
            return
        values = self.tree.item(self.tree.selection()[0], "values")
        result = self.controller.set_inventory_hold(self.selected_item_id, values[4] != "On Hold")
        if result[0]:
            self.load_inventory()
        else:
            messagebox.showerror("Could not update item", result[1])

    def show_borrowers(self):
        window = tk.Toplevel(self.root); window.title("Borrower records"); window.geometry("980x400")
        columns = ("record", "item", "student", "id", "section", "course", "quantity", "status", "date"); tree = ttk.Treeview(window, columns=columns, show="headings")
        for key in columns: tree.heading(key, text=key.title()); tree.column(key, width=115)
        for row in self.controller.fetch_borrow_records(): tree.insert("", "end", values=row)
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        buttons = tk.Frame(window); buttons.pack(pady=(0, 10))

        def update_status(status):
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Select record", "Select a borrower record first.")
                return
            result = self.controller.update_borrow_status(tree.item(selected[0], "values")[0], status)
            messagebox.showinfo("Borrower record", result[1]) if result[0] else messagebox.showerror("Borrower record", result[1])
            if result[0]:
                window.destroy()
                self.load_inventory()

        tk.Button(buttons, text="Mark Missing", command=lambda: update_status("Missing"), bg="#b8860b", fg="white").pack(side="left", padx=5)
        tk.Button(buttons, text="Return selected", command=lambda: update_status("Returned"), bg="#2e7d32", fg="white").pack(side="left", padx=5)

    def export_csv(self):
        filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=(("CSV files", "*.csv"),))
        if filename: messagebox.showinfo("Export", self.controller.export_to_csv(filename)[1])

    def show_reservations(self):
        window = tk.Toplevel(self.root); window.title("Reservation requests"); window.geometry("1100x430")
        columns = ("id", "item", "student", "student_id", "section", "course", "quantity", "date", "time", "status")
        tree = ttk.Treeview(window, columns=columns, show="headings")
        for key in columns: tree.heading(key, text=key.replace("_", " ").title()); tree.column(key, width=115)
        for row in self.controller.fetch_reservations(): tree.insert("", "end", values=row)
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        buttons = tk.Frame(window); buttons.pack(pady=(0, 10))
        def review(status):
            selected = tree.selection()
            if not selected: messagebox.showwarning("Select request", "Select a reservation first."); return
            result = self.controller.update_reservation_status(tree.item(selected[0], "values")[0], status)
            messagebox.showinfo("Reservation", result[1]) if result[0] else messagebox.showerror("Reservation", result[1])
            if result[0]: window.destroy(); self.load_inventory()
        tk.Button(buttons, text="Approve", command=lambda: review("Approved"), bg="#2e7d32", fg="white").pack(side="left", padx=5)
        tk.Button(buttons, text="Reject", command=lambda: review("Rejected"), bg="#c62828", fg="white").pack(side="left", padx=5)

    def manage_passwords(self):
        window = tk.Toplevel(self.root); window.title("Account password management"); window.geometry("600x420")
        tree = ttk.Treeview(window, columns=("username", "email", "role"), show="headings")
        for key in ("username", "email", "role"): tree.heading(key, text=key.title()); tree.column(key, width=180)
        for row in self.auth.fetch_accounts(): tree.insert("", "end", values=row)
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        tk.Label(window, text="New password (8+ chars, uppercase, number, special character)").pack()
        password = tk.Entry(window, show="*", width=35); password.pack(pady=4)
        def change():
            selected = tree.selection()
            if not selected: messagebox.showwarning("Select account", "Select an account first."); return
            result = self.auth.admin_change_password(tree.item(selected[0], "values")[0], password.get())
            messagebox.showinfo("Password", result[1]) if result[0] else messagebox.showerror("Password", result[1])
        tk.Button(window, text="Show", command=lambda: password.config(show="" if password.cget("show") else "*")).pack(side="left", padx=(170, 5))
        tk.Button(window, text="Change password", command=change, bg="#2e7d32", fg="white").pack(side="left")