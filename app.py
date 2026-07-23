"""
app.py
SECTION 1: PYTHON WEB APP GUI (Flask)
Developed by Jenil Pokar | Roll No. 46 | SY AI-DS
Developed by MANAV SHAH | Roll No. 55 | SY AI-DS
Multi-tenant Asset Management System. Two portals share one codebase:
  - Super Admin portal    (role == 'SUPER_ADMIN', company_id is NULL)
  - Client Company portal (role in ADMIN / STORE_MANAGER / DEPT_USER,
    always scoped to session['company_id'])

Every database call that touches company data passes company_id explicitly
(see db_connector.py + the stored procedures in
02_mysql_multitenant_procedures_functions_triggers.sql) so tenants can never
see or modify each other's records, even if a form field were tampered with.

Run locally:
    pip install -r requirements.txt
    python app.py

Deploy on Render: see requirements.txt notes / README.
"""

import hashlib
import os
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash

import db_connector as db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
os.makedirs(TEMPLATE_DIR, exist_ok=True)

app = Flask(__name__, template_folder=TEMPLATE_DIR)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")


def sha256_hex(text):
    """Matches MySQL's SHA2(text, 256) so stored hashes compare correctly."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Access-control decorators
# ---------------------------------------------------------------------------

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


def company_user_required(f):
    """Blocks the Super Admin from client-only routes, and vice versa."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("role") == "SUPER_ADMIN":
            return redirect(url_for("super_admin"))
        return f(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# AUTH
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def home():
    if "username" not in session:
        return redirect(url_for("login"))
    if session.get("role") == "SUPER_ADMIN":
        return redirect(url_for("super_admin"))
    return redirect(url_for("dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        try:
            columns, rows = db.run_query(
                """
                SELECT ul.username, ul.role, ul.company_id, c.company_name
                FROM User_Login ul
                LEFT JOIN Company c ON c.company_id = ul.company_id
                WHERE ul.username = %s AND ul.password_hash = %s
                """,
                (username, sha256_hex(password)),
            )
        except Exception as exc:
            flash(db.friendly_db_error(exc), "error")
            return render_template("login.html")

        if not rows:
            flash("Invalid username or password.", "error")
            return render_template("login.html")

        _, role, company_id, company_name = rows[0]
        session["username"] = username
        session["role"] = role
        session["company_id"] = company_id
        session["company_name"] = company_name
        return redirect(url_for("home"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# SUPER ADMIN PORTAL
# ---------------------------------------------------------------------------

@app.route("/super-admin")
@login_required
def super_admin():
    if session.get("role") != "SUPER_ADMIN":
        return redirect(url_for("dashboard"))

    columns, rows = db.call_procedure_with_result_set("sp_super_admin_company_overview")

    _, totals = db.run_query(
        """
        SELECT
            (SELECT COUNT(*) FROM Company) AS total_companies,
            (SELECT COUNT(*) FROM Asset) AS total_assets,
            (SELECT COUNT(*) FROM Company WHERE subscription_status = 'ACTIVE') AS active_subs
        """
    )
    total_companies, total_assets, active_subs = totals[0]

    return render_template(
        "super_admin.html", active="super_admin",
        columns=columns, rows=rows,
        total_companies=total_companies, total_assets=total_assets, active_subs=active_subs,
    )


# ---------------------------------------------------------------------------
# CLIENT COMPANY PORTAL: DASHBOARD
# ---------------------------------------------------------------------------

@app.route("/dashboard")
@login_required
@company_user_required
def dashboard():
    company_id = session["company_id"]

    _, status_rows = db.run_query(
        "SELECT status, COUNT(*) FROM Asset WHERE company_id = %s GROUP BY status", (company_id,)
    )
    counts = {status: count for status, count in status_rows}
    total = sum(counts.values())

    alert_columns, alert_rows = db.run_query(
        """
        SELECT alert_id, asset_id, alert_message, alert_date
        FROM Warranty_Alert_Log WHERE company_id = %s ORDER BY alert_date DESC
        """,
        (company_id,),
    )

    return render_template(
        "dashboard.html", active="dashboard",
        counts=counts, total=total,
        alert_columns=alert_columns, alert_rows=alert_rows,
    )


# ---------------------------------------------------------------------------
# ASSET MANAGEMENT
# ---------------------------------------------------------------------------

@app.route("/assets", methods=["GET", "POST"])
@login_required
@company_user_required
def assets():
    company_id = session["company_id"]

    if request.method == "POST":
        form_action = request.form.get("form_action")
        try:
            if form_action == "register":
                out_args = db.call_procedure(
                    "sp_register_asset",
                    [company_id, request.form["asset_name"], request.form["category"],
                     request.form.get("model", ""), request.form["serial_number"],
                     request.form["purchase_date"], float(request.form["cost"]),
                     int(request.form["warranty_years"]), 0],
                )
                flash(f"Asset registered with ID {out_args[-1]}.", "success")

            elif form_action == "update":
                db.call_procedure(
                    "sp_update_asset_details",
                    [company_id, int(request.form["asset_id"]), request.form["asset_name"],
                     request.form["category"], request.form.get("model", ""),
                     int(request.form["warranty_years"])],
                )
                flash("Asset updated.", "success")
        except Exception as exc:
            flash(db.friendly_db_error(exc), "error")

    columns, rows = db.run_query(
        "SELECT asset_id, asset_name, category, model, serial_number, purchase_date, "
        "cost, warranty_years, warranty_expiry_date, status FROM Asset "
        "WHERE company_id = %s ORDER BY asset_id",
        (company_id,),
    )
    _, asset_options_raw = db.run_query(
        "SELECT asset_id, asset_name FROM Asset WHERE company_id = %s ORDER BY asset_id", (company_id,)
    )

    return render_template(
        "assets.html", active="assets",
        columns=columns, rows=rows, asset_options=asset_options_raw,
    )


# ---------------------------------------------------------------------------
# DEPARTMENTS & STAFF
# ---------------------------------------------------------------------------

@app.route("/org", methods=["GET", "POST"])
@login_required
@company_user_required
def org():
    company_id = session["company_id"]

    if request.method == "POST":
        form_action = request.form.get("form_action")
        try:
            if form_action == "add_department":
                db.run_write(
                    "INSERT INTO Department (company_id, dept_name, dept_head) VALUES (%s, %s, %s)",
                    (company_id, request.form["dept_name"], request.form["dept_head"]),
                )
                flash("Department added.", "success")

            elif form_action == "add_employee":
                db.run_write(
                    "INSERT INTO Employee (company_id, employee_name, dept_id, designation, email) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (company_id, request.form["employee_name"], int(request.form["dept_id"]),
                     request.form["designation"], request.form.get("email") or None),
                )
                flash("Staff member added.", "success")
        except Exception as exc:
            flash(db.friendly_db_error(exc), "error")

    dept_columns, dept_rows = db.run_query(
        "SELECT dept_id, dept_name, dept_head FROM Department WHERE company_id = %s ORDER BY dept_id",
        (company_id,),
    )
    emp_columns, emp_rows = db.run_query(
        """
        SELECT e.employee_id, e.employee_name, d.dept_name, e.designation, e.email
        FROM Employee e JOIN Department d ON d.dept_id = e.dept_id
        WHERE e.company_id = %s ORDER BY e.employee_id
        """,
        (company_id,),
    )
    dept_options = [(row[0], row[1]) for row in dept_rows]

    return render_template(
        "org.html", active="org",
        dept_columns=dept_columns, dept_rows=dept_rows,
        emp_columns=emp_columns, emp_rows=emp_rows,
        dept_options=dept_options,
    )


# ---------------------------------------------------------------------------
# ALLOCATION
# ---------------------------------------------------------------------------

@app.route("/allocation", methods=["GET", "POST"])
@login_required
@company_user_required
def allocation():
    company_id = session["company_id"]

    if request.method == "POST":
        form_action = request.form.get("form_action")
        try:
            if form_action == "allocate":
                out_args = db.call_procedure(
                    "sp_allocate_asset",
                    [company_id, int(request.form["asset_id"]), int(request.form["employee_id"]),
                     int(request.form["dept_id"]), 0],
                )
                flash(f"Allocated. Allocation ID {out_args[-1]}.", "success")

            elif form_action == "return":
                db.call_procedure("sp_return_asset", [company_id, int(request.form["allocation_id"])])
                flash("Asset returned.", "success")
        except Exception as exc:
            flash(db.friendly_db_error(exc), "error")

    _, asset_options = db.run_query(
        "SELECT asset_id, asset_name FROM Asset WHERE company_id = %s AND status = 'AVAILABLE' ORDER BY asset_id",
        (company_id,),
    )
    _, emp_options = db.run_query(
        "SELECT employee_id, employee_name FROM Employee WHERE company_id = %s ORDER BY employee_id",
        (company_id,),
    )
    _, dept_options = db.run_query(
        "SELECT dept_id, dept_name FROM Department WHERE company_id = %s ORDER BY dept_id",
        (company_id,),
    )
    _, active_options = db.run_query(
        "SELECT allocation_id, asset_id FROM Asset_Allocation WHERE company_id = %s AND status = 'ACTIVE'",
        (company_id,),
    )
    columns, rows = db.run_query(
        """
        SELECT al.allocation_id, a.asset_name, e.employee_name, d.dept_name,
               al.allocation_date, al.status
        FROM Asset_Allocation al
        JOIN Asset a ON a.asset_id = al.asset_id
        JOIN Employee e ON e.employee_id = al.employee_id
        JOIN Department d ON d.dept_id = al.dept_id
        WHERE al.company_id = %s
        ORDER BY al.allocation_date DESC
        """,
        (company_id,),
    )

    return render_template(
        "allocation.html", active="allocation",
        asset_options=asset_options, emp_options=emp_options,
        dept_options=dept_options, active_options=active_options,
        columns=columns, rows=rows,
    )


# ---------------------------------------------------------------------------
# MAINTENANCE
# ---------------------------------------------------------------------------

@app.route("/maintenance", methods=["GET", "POST"])
@login_required
@company_user_required
def maintenance():
    company_id = session["company_id"]

    if request.method == "POST":
        try:
            out_args = db.call_procedure(
                "sp_schedule_maintenance",
                [company_id, int(request.form["asset_id"]), request.form["provider"],
                 float(request.form["cost"]), request.form.get("next_service_date") or None, 0],
            )
            flash(f"Maintenance scheduled. ID {out_args[-1]}.", "success")
        except Exception as exc:
            flash(db.friendly_db_error(exc), "error")

    _, asset_options = db.run_query(
        "SELECT asset_id, asset_name FROM Asset WHERE company_id = %s ORDER BY asset_id", (company_id,)
    )
    columns, rows = db.run_query(
        """
        SELECT m.maintenance_id, a.asset_name, m.maintenance_date, m.provider,
               m.cost, m.next_service_date, m.status
        FROM Asset_Maintenance m JOIN Asset a ON a.asset_id = m.asset_id
        WHERE m.company_id = %s ORDER BY m.maintenance_date DESC
        """,
        (company_id,),
    )

    return render_template("maintenance.html", active="maintenance",
                           asset_options=asset_options, columns=columns, rows=rows)


# ---------------------------------------------------------------------------
# DISPOSAL
# ---------------------------------------------------------------------------

@app.route("/disposal", methods=["GET", "POST"])
@login_required
@company_user_required
def disposal():
    company_id = session["company_id"]

    if request.method == "POST":
        try:
            out_args = db.call_procedure(
                "sp_dispose_asset",
                [company_id, int(request.form["asset_id"]), request.form["method"],
                 float(request.form.get("scrap_value") or 0), 0],
            )
            flash(f"Asset disposed. Disposal ID {out_args[-1]}.", "success")
        except Exception as exc:
            flash(db.friendly_db_error(exc), "error")

    _, asset_options = db.run_query(
        "SELECT asset_id, asset_name FROM Asset WHERE company_id = %s AND status != 'DISPOSED' ORDER BY asset_id",
        (company_id,),
    )
    columns, rows = db.run_query(
        """
        SELECT dp.disposal_id, a.asset_name, dp.disposal_date, dp.method, dp.scrap_value
        FROM Asset_Disposal dp JOIN Asset a ON a.asset_id = dp.asset_id
        WHERE dp.company_id = %s ORDER BY dp.disposal_date DESC
        """,
        (company_id,),
    )

    return render_template("disposal.html", active="disposal",
                           asset_options=asset_options, columns=columns, rows=rows)


# ---------------------------------------------------------------------------
# REPORTS
# ---------------------------------------------------------------------------

REPORT_OPTIONS = [
    "Asset Inventory Report",
    "Department-wise Asset Report",
    "Maintenance Schedule Report",
    "Asset Depreciation Report",
    "Allocated Assets (Cursor Report)",
]


@app.route("/reports")
@login_required
@company_user_required
def reports():
    company_id = session["company_id"]
    selected = request.args.get("report", REPORT_OPTIONS[0])

    if selected == "Asset Inventory Report":
        columns, rows = db.run_query(
            "SELECT * FROM Asset WHERE company_id = %s ORDER BY asset_id", (company_id,)
        )

    elif selected == "Department-wise Asset Report":
        columns, rows = db.run_query(
            """
            SELECT d.dept_name, a.category, COUNT(*) AS asset_count, SUM(a.cost) AS total_cost
            FROM Asset_Allocation al
            JOIN Asset a ON a.asset_id = al.asset_id
            JOIN Department d ON d.dept_id = al.dept_id
            WHERE al.company_id = %s AND al.status = 'ACTIVE'
            GROUP BY d.dept_name, a.category
            ORDER BY d.dept_name
            """,
            (company_id,),
        )

    elif selected == "Maintenance Schedule Report":
        columns, rows = db.run_query(
            """
            SELECT a.asset_name, m.provider, m.maintenance_date, m.next_service_date, m.cost, m.status,
                   CASE WHEN m.next_service_date < CURDATE() THEN 'YES' ELSE 'NO' END AS overdue
            FROM Asset_Maintenance m JOIN Asset a ON a.asset_id = m.asset_id
            WHERE m.company_id = %s ORDER BY m.next_service_date
            """,
            (company_id,),
        )

    elif selected == "Asset Depreciation Report":
        _, base_assets = db.run_query(
            "SELECT asset_id, asset_name, cost FROM Asset WHERE company_id = %s ORDER BY asset_id",
            (company_id,),
        )
        columns = ["asset_id", "asset_name", "cost", "current_value", "depreciation_pct"]
        rows = []
        for asset_id, name, cost in base_assets:
            current_value = db.call_function("fn_calculate_depreciation", (asset_id, 5))
            pct = round(100 * (float(cost) - float(current_value)) / float(cost), 1) if cost else 0
            rows.append((asset_id, name, cost, current_value, pct))

    else:  # Allocated Assets (Cursor Report)
        columns, rows = db.call_procedure_with_result_set("sp_list_allocated_assets", (company_id,))

    return render_template(
        "reports.html", active="reports",
        report_options=REPORT_OPTIONS, selected_report=selected,
        columns=columns, rows=rows,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
