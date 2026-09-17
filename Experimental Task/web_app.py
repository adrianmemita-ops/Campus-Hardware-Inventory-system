import io
import csv
from functools import wraps

from flask import Flask, flash, redirect, render_template_string, request, send_file, session, url_for

from controllers.auth_controller import AuthController
from controllers.tracker_controller import TrackerController
from database import init_db


app = Flask(__name__)
app.config["SECRET_KEY"] = "campus-inventory-development-key"

LAYOUT = """
<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }} | Campus Inventory</title><style>
:root{--forest:#164a35;--green:#2e7d50;--mint:#e8f4ec;--ink:#193528;--line:#d9e8dd;--red:#ad3b3b;--gold:#9a6b00}*{box-sizing:border-box}body{margin:0;color:var(--ink);background:linear-gradient(135deg,#f4faf5,#e8f4ec);font:15px system-ui,-apple-system,"Segoe UI",sans-serif}nav{background:var(--forest);color:white;padding:18px 5vw;display:flex;justify-content:space-between;align-items:center;gap:20px}nav strong{letter-spacing:.08em}nav a{color:white;text-decoration:none;margin-left:16px}main{max-width:1240px;margin:32px auto;padding:0 22px}h1{margin:0 0 8px;font-size:clamp(28px,4vw,46px)}h2{margin-top:0}.muted{color:#63806e}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:24px 0}.card{background:rgba(255,255,255,.94);border:1px solid var(--line);border-radius:8px;padding:20px;box-shadow:0 10px 30px #164a3510}.wide{grid-column:1/-1}.grid>section:nth-of-type(2),.grid>section:nth-of-type(3),.grid>section:nth-of-type(4){grid-column:1/-1}.grid>section:nth-of-type(2){order:8}.grid>section:nth-of-type(4){order:9}.grid>section:nth-of-type(3){order:10}.metric{font-size:30px;font-weight:700;color:var(--forest)}.form-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;align-items:end}label{display:block;font-weight:650;font-size:13px;margin-bottom:5px}input,select{width:100%;padding:10px;border:1px solid #c9ddcf;border-radius:5px;background:white;color:var(--ink)}button,.button{border:0;border-radius:5px;padding:10px 14px;background:var(--green);color:white;font-weight:700;cursor:pointer;text-decoration:none;display:inline-block}.danger{background:var(--red)}.gold{background:var(--gold)}.soft{background:var(--mint);color:var(--forest)}.actions{display:flex;gap:7px;flex-wrap:wrap;align-items:end}.flash{padding:12px 15px;background:#fff8dc;border:1px solid #ead99a;border-radius:5px;margin-bottom:15px}table{width:100%;border-collapse:collapse;margin-top:12px}th,td{padding:10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{color:var(--forest);font-size:11px;text-transform:uppercase;letter-spacing:.05em}.pill{display:inline-block;padding:4px 9px;border-radius:99px;background:var(--mint);color:var(--green);font-size:12px;font-weight:700}.auth{max-width:450px;margin:8vh auto}.auth .form-row{margin:14px 0}.auth button{width:100%;margin-top:8px}.inline{display:inline}.section-title{display:flex;justify-content:space-between;gap:16px;align-items:center}.small-form{display:grid;grid-template-columns:1fr auto;gap:7px;margin-top:8px}@media(max-width:800px){.grid,.form-grid{grid-template-columns:1fr}.grid>section:nth-of-type(2),.grid>section:nth-of-type(3),.grid>section:nth-of-type(4){grid-column:auto;order:initial}nav{align-items:flex-start;flex-direction:column}table{display:block;overflow-x:auto;white-space:nowrap}.wide{grid-column:auto}}
+</style></head><body><nav><strong>CAMPUS INVENTORY</strong><span>{% if session.get('username') %}{{ session.username }} ({{ session.role }}) · <a href="{{ url_for('logout') }}">Log out</a>{% endif %}</span></nav><main>{% for message in get_flashed_messages() %}<div class="flash">{{ message }}</div>{% endfor %}{{ body|safe }}</main></body></html>"""


def page(title, body, **context):
    return render_template_string(LAYOUT, title=title, body=render_template_string(body, **context))


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Administrator access is required for that action.")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)
    return wrapped


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        form = request.form
        success, message = AuthController().login_user(form.get("username", "").strip(), form.get("email", "").strip(), form.get("password", ""), form.get("role", "user"))
        if success:
            username = form["username"].strip()
            session.update(username=username, role=form["role"], user_id=AuthController().get_user_id(username))
            return redirect(url_for("dashboard"))
        flash(message)
    body = """<section class="card auth"><h1>Welcome back.</h1><p class="muted">Sign in to manage campus equipment.</p><form method="post"><div class="form-row"><label>Username</label><input name="username" required></div><div class="form-row"><label>Email</label><input name="email" type="email" required></div><div class="form-row"><label>Password</label><input name="password" type="password" required></div><div class="form-row"><label>Account type</label><select name="role"><option>user</option><option>admin</option></select></div><button>Sign in</button></form><p class="muted">Need an account? <a href="/register">Register here</a>.</p></section>"""
    return page("Sign in", body)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        form = request.form
        success, message = AuthController().register_user(form["username"].strip(), form["email"].strip(), form["password"], form["role"])
        flash(message)
        if success:
            return redirect(url_for("login"))
    body = """<section class="card auth"><h1>Create account.</h1><form method="post"><div class="form-row"><label>Username</label><input name="username" required></div><div class="form-row"><label>Email</label><input name="email" type="email" required></div><div class="form-row"><label>Password</label><input name="password" type="password" required></div><div class="form-row"><label>Account type</label><select name="role"><option>user</option><option>admin</option></select></div><button>Register</button></form><p><a href="/">Back to sign in</a></p></section>"""
    return page("Register", body)


@app.get("/dashboard")
@login_required
def dashboard():
    return admin_dashboard() if session["role"] == "admin" else user_dashboard()


def admin_dashboard():
    tracker = TrackerController()
    inventory = tracker.fetch_all_inventory()
    body = """
    <h1>Admin inventory</h1><p class="muted">Manage stock, loans, reservations, and accounts from one place.</p>
    <div class="grid"><div class="card"><span class="muted">Inventory items</span><div class="metric">{{ inventory|length }}</div></div><div class="card"><span class="muted">Units available</span><div class="metric">{{ inventory|sum(attribute=3) }}</div></div><div class="card"><span class="muted">Total asset value</span><div class="metric">₱{{ '%.2f'|format(total) }}</div></div>
    <section class="card wide"><div class="section-title"><h2>Inventory</h2><a class="button soft" href="{{ url_for('export_csv') }}">Export CSV</a></div><form method="post" action="{{ url_for('add_inventory') }}" class="form-grid"><div><label>Item name</label><input name="item_name" required></div><div><label>Category</label><input name="category" required></div><div><label>Quantity</label><input name="quantity" type="number" min="0" required></div><div><label>Unit price</label><input name="unit_price" type="number" min="0" step=".01" required></div><button>Add item</button></form><table><tr><th>Item</th><th>Category</th><th>Qty</th><th>Status</th><th>Price</th><th>Actions</th></tr>{% for item in inventory %}<tr><td>{{ item[1] }}</td><td>{{ item[2] }}</td><td>{{ item[3] }}</td><td><span class="pill">{{ item[5] if item[5] == 'On Hold' else ('In stock' if item[3] else 'Out of stock') }}</span></td><td>₱{{ '%.2f'|format(item[4]) }}</td><td><form method="post" action="/inventory/{{ item[0] }}/hold" class="inline"><button class="soft">{{ 'Release' if item[5] == 'On Hold' else 'Hold' }}</button></form><a class="button soft" href="/inventory/{{ item[0] }}/edit">Edit</a><form method="post" action="/inventory/{{ item[0] }}/delete" class="inline"><button class="danger">Delete</button></form></td></tr>{% else %}<tr><td colspan="6">No inventory has been added yet.</td></tr>{% endfor %}</table></section>
    <section class="card"><h2>Borrower records</h2><table><tr><th>Item</th><th>Student</th><th>Course</th><th>Qty</th><th>Status</th><th>Action</th></tr>{% for row in borrowers %}<tr><td>{{ row[1] }}</td><td>{{ row[2] }}<br>{{ row[3] }}</td><td>{{ row[5] }}</td><td>{{ row[6] }}</td><td>{{ row[7] }}</td><td>{% if row[7] != 'Returned' %}<form method="post" action="/borrowers/{{ row[0] }}/status"><select name="status"><option>Missing</option><option>Returned</option></select><button>Update</button></form>{% endif %}</td></tr>{% else %}<tr><td colspan="6">No borrower records.</td></tr>{% endfor %}</table></section>
    <section class="card"><h2>Reservations</h2><table><tr><th>Item</th><th>Student</th><th>Details</th><th>Qty</th><th>Status</th><th>Action</th></tr>{% for row in reservations %}<tr><td>{{ row[1] }}</td><td>{{ row[2] }}<br>{{ row[3] }}</td><td>{{ row[7] }} {{ row[8] }}<br>{{ row[5] }}</td><td>{{ row[6] }}</td><td>{{ row[9] }}</td><td>{% if row[9] in ['Pending','On Hold'] %}<form method="post" action="/reservations/{{ row[0] }}/status"><select name="status"><option>Approved</option><option>On Hold</option><option>Rejected</option></select><button>Review</button></form>{% endif %}</td></tr>{% else %}<tr><td colspan="6">No reservations.</td></tr>{% endfor %}</table></section>
    <section class="card"><h2>Account password management</h2><table><tr><th>Username</th><th>Email</th><th>Role</th><th>New password</th></tr>{% for account in accounts %}<tr><td>{{ account[0] }}</td><td>{{ account[1] }}</td><td>{{ account[2] }}</td><td><form method="post" action="/accounts/{{ account[0] }}/password" class="small-form"><input name="password" type="password" placeholder="New password" required><button>Change</button></form></td></tr>{% endfor %}</table></section></div>"""
    return page("Admin dashboard", body, inventory=inventory, total=tracker.get_total_asset_value(), borrowers=tracker.fetch_borrow_records(), reservations=tracker.fetch_reservations(), accounts=AuthController().fetch_accounts())


def user_dashboard():
    inventory = TrackerController().fetch_all_inventory()
    body = """
    <h1>Borrow equipment</h1><p class="muted">Select an item, enter borrower details, then borrow it or request a reservation.</p><section class="card"><h2>Available inventory</h2><table><tr><th>Item</th><th>Category</th><th>Available</th><th>Status</th></tr>{% for item in inventory %}<tr><td>{{ item[1] }}</td><td>{{ item[2] }}</td><td>{{ item[3] }}</td><td><span class="pill">{{ item[5] if item[5] == 'On Hold' else ('Available' if item[3] else 'Out of stock') }}</span></td></tr>{% endfor %}</table></section><section class="card"><h2>Borrow or reserve</h2><form method="post" action="/borrow"><div class="form-grid"><div><label>Item</label><select name="item_id" required>{% for item in inventory %}<option value="{{ item[0] }}">{{ item[1] }} ({{ item[3] }} available)</option>{% endfor %}</select></div><div><label>Student name</label><input name="student_name" required></div><div><label>Student ID</label><input name="student_id" required></div><div><label>Section</label><input name="section" required></div><div><label>Course</label><input name="course" required></div><div><label>Quantity</label><input name="quantity" type="number" min="1" value="1" required></div><div><label>Loan status</label><select name="status"><option>Borrowed</option><option>Missing</option></select></div><div class="actions"><button>Borrow selected item</button></div></div></form><hr><form method="post" action="/reserve"><div class="form-grid"><div><label>Item</label><select name="item_id" required>{% for item in inventory %}<option value="{{ item[0] }}">{{ item[1] }}</option>{% endfor %}</select></div><div><label>Student name</label><input name="student_name" required></div><div><label>Student ID</label><input name="student_id" required></div><div><label>Section</label><input name="section" required></div><div><label>Course</label><input name="course" required></div><div><label>Reservation date</label><input name="reservation_date" type="date" required></div><div><label>Reservation time</label><input name="reservation_time" type="time" required></div><div><label>Quantity</label><input name="quantity" type="number" min="1" value="1" required></div><div class="actions"><button>Request reservation</button></div></div></form></section>"""
    return page("User dashboard", body, inventory=inventory)


def form_int(name):
    try:
        return int(request.form[name])
    except (KeyError, TypeError, ValueError):
        raise ValueError(f"{name.replace('_', ' ').capitalize()} must be a whole number.")


@app.post("/inventory/add")
@admin_required
def add_inventory():
    try:
        result = TrackerController().add_inventory(request.form["item_name"], request.form["category"], form_int("quantity"), float(request.form["unit_price"]))
    except (ValueError, KeyError) as exc:
        flash(str(exc))
    else:
        flash(result[1])
    return redirect(url_for("dashboard"))


@app.route("/inventory/<int:item_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_inventory(item_id):
    tracker = TrackerController()
    current = next((row for row in tracker.fetch_all_inventory() if row[0] == item_id), None)
    if not current:
        flash("Inventory item not found.")
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        try:
            result = tracker.update_inventory(item_id, request.form["item_name"], request.form["category"], form_int("quantity"), float(request.form["unit_price"]))
        except (ValueError, KeyError) as exc:
            flash(str(exc))
        else:
            flash(result[1])
            if result[0]:
                return redirect(url_for("dashboard"))
    body = """<section class="card"><h1>Edit inventory</h1><form method="post" class="form-grid"><div><label>Item name</label><input name="item_name" value="{{ item[1] }}" required></div><div><label>Category</label><input name="category" value="{{ item[2] }}" required></div><div><label>Quantity</label><input name="quantity" type="number" min="0" value="{{ item[3] }}" required></div><div><label>Unit price</label><input name="unit_price" type="number" min="0" step=".01" value="{{ item[4] }}" required></div><button>Save changes</button></form><p><a href="/dashboard">Cancel</a></p></section>"""
    return page("Edit inventory", body, item=current)


@app.post("/inventory/<int:item_id>/delete")
@admin_required
def delete_inventory(item_id):
    flash(TrackerController().delete_inventory(item_id)[1])
    return redirect(url_for("dashboard"))


@app.post("/inventory/<int:item_id>/hold")
@admin_required
def toggle_hold(item_id):
    current = next((row for row in TrackerController().fetch_all_inventory() if row[0] == item_id), None)
    if current:
        flash(TrackerController().set_inventory_hold(item_id, current[5] != "On Hold")[1])
    return redirect(url_for("dashboard"))


@app.post("/borrowers/<int:record_id>/status")
@admin_required
def update_borrower(record_id):
    flash(TrackerController().update_borrow_status(record_id, request.form["status"])[1])
    return redirect(url_for("dashboard"))


@app.post("/reservations/<int:reservation_id>/status")
@admin_required
def update_reservation(reservation_id):
    flash(TrackerController().update_reservation_status(reservation_id, request.form["status"])[1])
    return redirect(url_for("dashboard"))


@app.post("/accounts/<username>/password")
@admin_required
def change_account_password(username):
    flash(AuthController().admin_change_password(username, request.form["password"])[1])
    return redirect(url_for("dashboard"))


@app.get("/export.csv")
@admin_required
def export_csv():
    tracker = TrackerController()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Item Name", "Category", "Quantity", "Unit Price", "Total Value"])
    for item_id, name, category, quantity, price, _status in tracker.fetch_all_inventory():
        writer.writerow([item_id, name, category, quantity, f"{price:.2f}", f"{quantity * price:.2f}"])
    writer.writerow([])
    writer.writerow(["TOTAL ASSET VALUE", f"{tracker.get_total_asset_value():.2f}"])
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype="text/csv", as_attachment=True, download_name="inventory_report.csv")


@app.post("/borrow")
@login_required
def borrow():
    try:
        result = TrackerController().borrow_item(form_int("item_id"), session["user_id"], request.form["student_name"], request.form["student_id"], request.form["section"], request.form["course"], request.form["status"], form_int("quantity"))
    except (ValueError, KeyError) as exc:
        flash(str(exc))
    else:
        flash(result[1])
    return redirect(url_for("dashboard"))


@app.post("/reserve")
@login_required
def reserve():
    form = request.form
    try:
        result = TrackerController().create_reservation(form_int("item_id"), session["user_id"], form["student_name"], form["student_id"], form["section"], form["course"], form["reservation_date"], form["reservation_time"], form_int("quantity"))
    except (ValueError, KeyError) as exc:
        flash(str(exc))
    else:
        flash(result[1])
    return redirect(url_for("dashboard"))


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=False)
