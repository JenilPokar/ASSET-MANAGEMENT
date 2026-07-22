"""
main_app.py
ASSET MANAGEMENT SYSTEM - Python Tkinter Front-End (Phase 3 - Modern UI)

Connects to the MySQL database created by:
    01_mysql_schema_and_data.sql
    02_mysql_procedures_functions_triggers.sql
via db_connector.py, which wraps mysql-connector-python.

Run with:   python main_app.py
"""

import csv
import hashlib
import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk, filedialog

import db_connector as db

DATE_FMT = "%Y-%m-%d"

# --- Modern Color Theme ---
THEME = {
    "sidebar_bg": "#1E293B",      # Slate Dark
    "sidebar_fg": "#F8FAFC",      # Off-white
    "sidebar_active": "#3B82F6",  # Bright Blue
    "main_bg": "#F1F5F9",         # Light Gray/Blue
    "card_bg": "#FFFFFF",         # White
    "text_main": "#334155",       # Slate Gray
    "accent": "#0284C7",          # Ocean Blue
}

# ---------------------------------------------------------------------------
# Small reusable helpers
# ---------------------------------------------------------------------------

def sha256_hex(text: str) -> str:
    """Match MySQL's SHA2(text, 256) so login passwords compare correctly."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def fill_treeview(tree: ttk.Treeview, columns: list[str], rows: list[tuple]):
    tree.delete(*tree.get_children())
    tree["columns"] = columns
    tree["show"] = "headings"
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=120, anchor="center")
    for row in rows:
        tree.insert("", "end", values=row)

def export_treeview_to_csv(tree: ttk.Treeview):
    path = filedialog.asksaveasfilename(defaultextension=".csv",
                                         filetypes=[("CSV files", "*.csv")])
    if not path:
        return
    columns = tree["columns"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        for item in tree.get_children():
            writer.writerow(tree.item(item)["values"])
    messagebox.showinfo("Export complete", f"Report saved to:\n{path}")

def setup_modern_styles():
    """Configures global ttk styles for a modern look."""
    style = ttk.Style()
    style.theme_use('clam')

    # Treeview Styling
    style.configure("Treeview", 
                    background=THEME["card_bg"], 
                    foreground=THEME["text_main"], 
                    rowheight=30, 
                    fieldbackground=THEME["card_bg"],
                    bordercolor=THEME["main_bg"],
                    borderwidth=0,
                    font=("Segoe UI", 10))
    style.map('Treeview', background=[('selected', THEME["accent"])])
    style.configure("Treeview.Heading", 
                    background=THEME["sidebar_bg"], 
                    foreground=THEME["sidebar_fg"], 
                    font=("Segoe UI", 10, "bold"),
                    relief="flat")
    
    # Frames & Labels
    style.configure("TFrame", background=THEME["main_bg"])
    style.configure("Card.TFrame", background=THEME["card_bg"], relief="flat")
    style.configure("TLabel", background=THEME["main_bg"], foreground=THEME["text_main"], font=("Segoe UI", 10))
    style.configure("Card.TLabel", background=THEME["card_bg"], foreground=THEME["text_main"])
    style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"), background=THEME["main_bg"], foreground=THEME["accent"])
    
    # Buttons
    style.configure("TButton", 
                    font=("Segoe UI", 10, "bold"), 
                    background=THEME["accent"], 
                    foreground="white", 
                    borderwidth=0, 
                    focuscolor=THEME["accent"],
                    padding=6)
    style.map("TButton", background=[("active", THEME["sidebar_active"])])
    
    # Sidebar Buttons (Custom tk Buttons used instead for easier color mapping)
    style.configure("TLabelframe", background=THEME["main_bg"], foreground=THEME["text_main"], font=("Segoe UI", 10, "bold"))
    style.configure("TLabelframe.Label", background=THEME["main_bg"], foreground=THEME["accent"], font=("Segoe UI", 10, "bold"))

# ---------------------------------------------------------------------------
# LOGIN WINDOW
# ---------------------------------------------------------------------------

class LoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Asset Management System - Login")
        self.geometry("450x300")
        self.resizable(False, False)
        self.configure(bg=THEME["main_bg"])
        
        setup_modern_styles()

        ttk.Label(self, text="Asset Management System", style="Title.TLabel").pack(pady=(30, 20))

        form = ttk.Frame(self, style="Card.TFrame", padding=20)
        form.pack(pady=5, padx=40, fill="x")

        ttk.Label(form, text="Username:", style="Card.TLabel").grid(row=0, column=0, sticky="e", padx=5, pady=10)
        self.username_entry = ttk.Entry(form, font=("Segoe UI", 11))
        self.username_entry.grid(row=0, column=1, padx=5, pady=10, sticky="ew")

        ttk.Label(form, text="Password:", style="Card.TLabel").grid(row=1, column=0, sticky="e", padx=5, pady=10)
        self.password_entry = ttk.Entry(form, show="*", font=("Segoe UI", 11))
        self.password_entry.grid(row=1, column=1, padx=5, pady=10, sticky="ew")
        
        form.columnconfigure(1, weight=1)

        ttk.Button(self, text="Log In", command=self.attempt_login, width=20).pack(pady=20)
        self.bind("<Return>", lambda e: self.attempt_login())

    def attempt_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if not username or not password:
            messagebox.showwarning("Missing info", "Enter both username and password.")
            return

        try:
            columns, rows = db.run_query(
                "SELECT username, role FROM User_Login WHERE username=%s AND password_hash=%s",
                (username, sha256_hex(password)),
            )
        except Exception as exc:
            messagebox.showerror("Database error", str(exc))
            return

        if not rows:
            messagebox.showerror("Login failed", "Invalid username or password.")
            return

        role = rows[0][1]
        self.destroy()
        app = MainApp(username=username, role=role)
        app.mainloop()

# ---------------------------------------------------------------------------
# MAIN APPLICATION WINDOW (post-login)
# ---------------------------------------------------------------------------

class MainApp(tk.Tk):
    def __init__(self, username: str, role: str):
        super().__init__()
        self.username = username
        self.role = role
        self.title(f"Enterprise Asset Management - {username} ({role})")
        self.geometry("1100x700")
        self.configure(bg=THEME["main_bg"])
        setup_modern_styles()

        # Layout Setup
        self.sidebar = tk.Frame(self, bg=THEME["sidebar_bg"], width=200)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        
        self.main_container = ttk.Frame(self)
        self.main_container.pack(side="right", fill="both", expand=True)

        # Branding
        tk.Label(self.sidebar, text="EAM System", font=("Segoe UI", 16, "bold"), 
                 bg=THEME["sidebar_bg"], fg=THEME["sidebar_fg"]).pack(pady=20)
        
        # User Info
        tk.Label(self.sidebar, text=f"User: {username}", font=("Segoe UI", 10), 
                 bg=THEME["sidebar_bg"], fg="#94A3B8").pack(pady=(0, 20))

        # View Dictionary
        self.frames = {}
        self.nav_buttons = []

        self.setup_views()
        self.build_sidebar()
        
        # Default View
        self.show_frame("Dashboard")

    def setup_views(self):
        for F in (DashboardTab, AssetTab, DepartmentTab, EmployeeTab, AllocationTab, MaintenanceTab, DisposalTab, ReportsTab):
            page_name = F.__name__.replace("Tab", "")
            frame = F(parent=self.main_container)
            self.frames[page_name] = frame
            frame.place(relwidth=1, relheight=1)

    def build_sidebar(self):
        pages = ["Dashboard", "Asset", "Department", "Employee", "Allocation", "Maintenance", "Disposal", "Reports"]
        for page in pages:
            btn = tk.Button(self.sidebar, text=f"  {page}", font=("Segoe UI", 11, "bold"),
                            bg=THEME["sidebar_bg"], fg=THEME["sidebar_fg"],
                            activebackground=THEME["sidebar_active"], activeforeground="white",
                            bd=0, relief="flat", anchor="w", padx=20, pady=12,
                            command=lambda p=page: self.show_frame(p))
            btn.pack(fill="x")
            self.nav_buttons.append(btn)

    def show_frame(self, page_name):
        # Update Nav Styles
        for btn in self.nav_buttons:
            if btn.cget("text").strip() == page_name:
                btn.configure(bg=THEME["sidebar_active"])
            else:
                btn.configure(bg=THEME["sidebar_bg"])
                
        frame = self.frames[page_name]
        frame.tkraise()
        
        if hasattr(frame, "refresh"):
            frame.refresh()


# ---------------------------------------------------------------------------
# DASHBOARD TAB
# ---------------------------------------------------------------------------
class DashboardTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        
        header = ttk.Frame(self, padding=20)
        header.pack(fill="x")
        ttk.Label(header, text="Overview Dashboard", style="Title.TLabel").pack(side="left")
        ttk.Button(header, text="Refresh Data", command=self.refresh).pack(side="right")

        self.metrics_frame = ttk.Frame(self, padding=20)
        self.metrics_frame.pack(fill="x")

        ttk.Label(self, text="Warranty Alerts", style="Title.TLabel").pack(anchor="w", padx=20, pady=(10, 0))
        self.alerts_tree = ttk.Treeview(self, height=10)
        self.alerts_tree.pack(fill="both", expand=True, padx=20, pady=10)

    def refresh(self):
        for widget in self.metrics_frame.winfo_children():
            widget.destroy()
        try:
            _, rows = db.run_query("SELECT status, COUNT(*) FROM Asset GROUP BY status")
        except Exception as exc:
            messagebox.showerror("Database error", str(exc))
            return

        counts = {status: count for status, count in rows}
        total = sum(counts.values())
        labels = [
            ("Total Assets", total),
            ("Available", counts.get("AVAILABLE", 0)),
            ("Allocated", counts.get("ALLOCATED", 0)),
            ("Under Maintenance", counts.get("UNDER_MAINTENANCE", 0)),
            ("Disposed", counts.get("DISPOSED", 0)),
        ]
        
        for i, (label, value) in enumerate(labels):
            box = tk.Frame(self.metrics_frame, bg=THEME["card_bg"], padx=25, pady=20)
            box.grid(row=0, column=i, padx=10, sticky="nsew")
            tk.Label(box, text=str(value), font=("Segoe UI", 24, "bold"), bg=THEME["card_bg"], fg=THEME["accent"]).pack()
            tk.Label(box, text=label, font=("Segoe UI", 10), bg=THEME["card_bg"], fg=THEME["text_main"]).pack()
            
        self.metrics_frame.columnconfigure(list(range(len(labels))), weight=1)

        try:
            columns, alert_rows = db.run_query(
                "SELECT alert_id, asset_id, alert_message, alert_date "
                "FROM Warranty_Alert_Log ORDER BY alert_date DESC"
            )
            fill_treeview(self.alerts_tree, columns, alert_rows)
        except Exception as exc:
            messagebox.showerror("Database error", str(exc))


# ---------------------------------------------------------------------------
# ASSET MANAGEMENT TAB
# ---------------------------------------------------------------------------
class AssetTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        
        header = ttk.Frame(self, padding=20)
        header.pack(fill="x")
        ttk.Label(header, text="Asset Directory", style="Title.TLabel").pack(side="left")

        button_bar = ttk.Frame(self, padding=(20, 0))
        button_bar.pack(fill="x")
        ttk.Button(button_bar, text="+ Register New Asset", command=self.open_register_dialog).pack(side="left")
        ttk.Button(button_bar, text="Update Selected", command=self.open_update_dialog).pack(side="left", padx=10)
        ttk.Button(button_bar, text="Refresh", command=self.refresh).pack(side="right")

        self.tree = ttk.Treeview(self)
        self.tree.pack(fill="both", expand=True, padx=20, pady=15)

    def refresh(self):
        try:
            columns, rows = db.run_query("SELECT * FROM Asset ORDER BY asset_id")
            fill_treeview(self.tree, columns, rows)
        except Exception as exc:
            messagebox.showerror("Database error", str(exc))

    def open_register_dialog(self):
        dialog = AssetFormDialog(self, title="Register Asset")
        self.wait_window(dialog)
        if dialog.result:
            try:
                out_args = db.call_procedure(
                    "sp_register_asset",
                    [dialog.result["name"], dialog.result["category"], dialog.result["model"],
                     dialog.result["serial"], dialog.result["purchase_date"],
                     dialog.result["cost"], dialog.result["warranty"], 0],
                )
                messagebox.showinfo("Success", f"Asset registered with ID {out_args[-1]}.")
                self.refresh()
            except Exception as exc:
                messagebox.showerror("Database error", str(exc))

    def open_update_dialog(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Select an asset row first.")
            return
        values = self.tree.item(selected[0])["values"]
        asset_id = values[0]

        dialog = AssetFormDialog(self, title="Update Asset", prefill={
            "name": values[1], "category": values[2], "model": values[3],
            "serial": values[4], "purchase_date": str(values[5]),
            "cost": values[6], "warranty": str(values[7]),
        }, lock_serial=True)
        self.wait_window(dialog)
        if dialog.result:
            try:
                db.call_procedure(
                    "sp_update_asset_details",
                    [asset_id, dialog.result["name"], dialog.result["category"],
                     dialog.result["model"], dialog.result["warranty"]],
                )
                messagebox.showinfo("Success", f"Asset {asset_id} updated.")
                self.refresh()
            except Exception as exc:
                messagebox.showerror("Database error", str(exc))


class AssetFormDialog(tk.Toplevel):
    def __init__(self, parent, title, prefill=None, lock_serial=False):
        super().__init__(parent)
        self.title(title)
        self.geometry("400x380")
        self.configure(bg=THEME["main_bg"])
        self.result = None
        prefill = prefill or {}

        ttk.Label(self, text=title, style="Title.TLabel").pack(pady=15)
        
        form = ttk.Frame(self, style="Card.TFrame", padding=20)
        form.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        fields = [
            ("name", "Asset Name"), ("category", "Category"), ("model", "Model"),
            ("serial", "Serial Number"), ("purchase_date", "Purchase Date"),
            ("cost", "Cost"), ("warranty", "Warranty Expiry"),
        ]
        self.entries = {}
        for row, (key, label) in enumerate(fields):
            ttk.Label(form, text=label+":", style="Card.TLabel").grid(row=row, column=0, sticky="e", padx=5, pady=6)
            entry = ttk.Entry(form, width=30)
            entry.grid(row=row, column=1, padx=5, pady=6)
            if key in prefill:
                entry.insert(0, prefill[key])
            if key in ("serial", "purchase_date", "cost") and lock_serial:
                entry.configure(state="disabled")
            self.entries[key] = entry

        ttk.Button(form, text="Save Details", command=self.on_save).grid(row=len(fields), column=0, columnspan=2, pady=15)

    def on_save(self):
        try:
            self.result = {
                "name": self.entries["name"].get().strip(),
                "category": self.entries["category"].get().strip(),
                "model": self.entries["model"].get().strip(),
                "serial": self.entries["serial"].get().strip(),
                "purchase_date": self.entries["purchase_date"].get().strip() or str(date.today()),
                "cost": float(self.entries["cost"].get() or 0),
                "warranty": self.entries["warranty"].get().strip() or None,
            }
        except ValueError:
            messagebox.showerror("Invalid input", "Cost must be a number.")
            return
        self.destroy()


# ---------------------------------------------------------------------------
# DEPARTMENT TAB
# ---------------------------------------------------------------------------
class DepartmentTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        
        ttk.Label(self, text="Department Directory", style="Title.TLabel").pack(anchor="w", padx=20, pady=20)

        form = ttk.LabelFrame(self, text=" Add New Department ", padding=15)
        form.pack(fill="x", padx=20, pady=5)

        ttk.Label(form, text="Name:").grid(row=0, column=0, padx=5)
        self.name_entry = ttk.Entry(form, width=25)
        self.name_entry.grid(row=0, column=1, padx=10)

        ttk.Label(form, text="Head:").grid(row=0, column=2, padx=5)
        self.head_entry = ttk.Entry(form, width=25)
        self.head_entry.grid(row=0, column=3, padx=10)

        ttk.Button(form, text="Add Department", command=self.add_department).grid(row=0, column=4, padx=10)
        
        self.tree = ttk.Treeview(self)
        self.tree.pack(fill="both", expand=True, padx=20, pady=15)

    def refresh(self):
        try:
            columns, rows = db.run_query("SELECT * FROM Department ORDER BY dept_id")
            fill_treeview(self.tree, columns, rows)
        except Exception as exc:
            messagebox.showerror("Database error", str(exc))

    def add_department(self):
        name = self.name_entry.get().strip()
        head = self.head_entry.get().strip()
        if not name or not head:
            messagebox.showwarning("Missing info", "Enter both name and head.")
            return
        try:
            db.run_write("INSERT INTO Department (dept_name, dept_head) VALUES (%s, %s)", (name, head))
            self.name_entry.delete(0, tk.END)
            self.head_entry.delete(0, tk.END)
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Database error", str(exc))


# ---------------------------------------------------------------------------
# EMPLOYEE TAB
# ---------------------------------------------------------------------------
class EmployeeTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        
        ttk.Label(self, text="Employee Directory", style="Title.TLabel").pack(anchor="w", padx=20, pady=20)

        form = ttk.LabelFrame(self, text=" Add New Employee ", padding=15)
        form.pack(fill="x", padx=20, pady=5)

        ttk.Label(form, text="Name:").grid(row=0, column=0, pady=5)
        self.name_entry = ttk.Entry(form, width=25)
        self.name_entry.grid(row=0, column=1, padx=10, pady=5)

        ttk.Label(form, text="Department:").grid(row=0, column=2, pady=5)
        self.dept_combo = ttk.Combobox(form, width=25, state="readonly")
        self.dept_combo.grid(row=0, column=3, padx=10, pady=5)

        ttk.Label(form, text="Designation:").grid(row=1, column=0, pady=5)
        self.desig_entry = ttk.Entry(form, width=25)
        self.desig_entry.grid(row=1, column=1, padx=10, pady=5)

        ttk.Label(form, text="Email:").grid(row=1, column=2, pady=5)
        self.email_entry = ttk.Entry(form, width=25)
        self.email_entry.grid(row=1, column=3, padx=10, pady=5)

        ttk.Button(form, text="Register Employee", command=self.add_employee).grid(row=1, column=4, padx=15)

        self.tree = ttk.Treeview(self)
        self.tree.pack(fill="both", expand=True, padx=20, pady=15)

    def refresh(self):
        try:
            _, depts = db.run_query("SELECT dept_id, dept_name FROM Department ORDER BY dept_name")
            self._dept_lookup = {f"{did} - {name}": did for did, name in depts}
            self.dept_combo["values"] = list(self._dept_lookup.keys())

            columns, rows = db.run_query(
                """
                SELECT e.employee_id, e.employee_name, d.dept_name, e.designation, e.email
                FROM Employee e JOIN Department d ON d.dept_id = e.dept_id
                ORDER BY e.employee_id
                """
            )
            fill_treeview(self.tree, columns, rows)
        except Exception as exc:
            messagebox.showerror("Database error", str(exc))

    def add_employee(self):
        name = self.name_entry.get().strip()
        dept_choice = self.dept_combo.get()
        designation = self.desig_entry.get().strip()
        email = self.email_entry.get().strip() or None

        if not name or not dept_choice or not designation:
            messagebox.showwarning("Missing info", "Fill in name, department, and designation.")
            return

        dept_id = self._dept_lookup[dept_choice]
        try:
            db.run_write(
                "INSERT INTO Employee (employee_name, dept_id, designation, email) VALUES (%s, %s, %s, %s)",
                (name, dept_id, designation, email),
            )
            self.name_entry.delete(0, tk.END)
            self.desig_entry.delete(0, tk.END)
            self.email_entry.delete(0, tk.END)
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Database error", str(exc))


# ---------------------------------------------------------------------------
# ALLOCATION TAB
# ---------------------------------------------------------------------------
class AllocationTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        
        ttk.Label(self, text="Asset Allocation Management", style="Title.TLabel").pack(anchor="w", padx=20, pady=20)

        allocate_frame = ttk.LabelFrame(self, text=" Allocate Asset ", padding=15)
        allocate_frame.pack(fill="x", padx=20, pady=5)

        ttk.Label(allocate_frame, text="Asset:").grid(row=0, column=0)
        self.asset_combo = ttk.Combobox(allocate_frame, width=25, state="readonly")
        self.asset_combo.grid(row=0, column=1, padx=10)

        ttk.Label(allocate_frame, text="Employee:").grid(row=0, column=2)
        self.emp_combo = ttk.Combobox(allocate_frame, width=25, state="readonly")
        self.emp_combo.grid(row=0, column=3, padx=10)

        ttk.Label(allocate_frame, text="Department:").grid(row=0, column=4)
        self.dept_combo = ttk.Combobox(allocate_frame, width=20, state="readonly")
        self.dept_combo.grid(row=0, column=5, padx=10)

        ttk.Button(allocate_frame, text="Confirm Allocation", command=self.allocate).grid(row=0, column=6, padx=10)

        return_frame = ttk.LabelFrame(self, text=" Return Asset ", padding=15)
        return_frame.pack(fill="x", padx=20, pady=(10, 5))

        ttk.Label(return_frame, text="Active Allocation:").grid(row=0, column=0)
        self.active_combo = ttk.Combobox(return_frame, width=50, state="readonly")
        self.active_combo.grid(row=0, column=1, padx=15)
        ttk.Button(return_frame, text="Process Return", command=self.return_asset).grid(row=0, column=2)

        self.tree = ttk.Treeview(self)
        self.tree.pack(fill="both", expand=True, padx=20, pady=15)

    def refresh(self):
        try:
            _, assets = db.run_query("SELECT asset_id, asset_name FROM Asset WHERE status='AVAILABLE' ORDER BY asset_id")
            self._asset_lookup = {f"{aid} - {name}": aid for aid, name in assets}
            self.asset_combo["values"] = list(self._asset_lookup.keys())

            _, emps = db.run_query("SELECT employee_id, employee_name FROM Employee ORDER BY employee_id")
            self._emp_lookup = {f"{eid} - {name}": eid for eid, name in emps}
            self.emp_combo["values"] = list(self._emp_lookup.keys())

            _, depts = db.run_query("SELECT dept_id, dept_name FROM Department ORDER BY dept_id")
            self._dept_lookup = {f"{did} - {name}": did for did, name in depts}
            self.dept_combo["values"] = list(self._dept_lookup.keys())

            _, active = db.run_query("SELECT allocation_id, asset_id FROM Asset_Allocation WHERE status='ACTIVE'")
            self._active_lookup = {f"{aid} (Asset {asset})": aid for aid, asset in active}
            self.active_combo["values"] = list(self._active_lookup.keys())

            columns, rows = db.run_query(
                """
                SELECT al.allocation_id, a.asset_name, e.employee_name, d.dept_name,
                       al.allocation_date, al.status
                FROM Asset_Allocation al
                JOIN Asset a ON a.asset_id = al.asset_id
                JOIN Employee e ON e.employee_id = al.employee_id
                JOIN Department d ON d.dept_id = al.dept_id
                ORDER BY al.allocation_date DESC
                """
            )
            fill_treeview(self.tree, columns, rows)
        except Exception as exc:
            messagebox.showerror("Database error", str(exc))

    def allocate(self):
        if not (self.asset_combo.get() and self.emp_combo.get() and self.dept_combo.get()):
            messagebox.showwarning("Missing info", "Select asset, employee, and department.")
            return
        try:
            out_args = db.call_procedure(
                "sp_allocate_asset",
                [self._asset_lookup[self.asset_combo.get()],
                 self._emp_lookup[self.emp_combo.get()],
                 self._dept_lookup[self.dept_combo.get()], 0],
            )
            messagebox.showinfo("Success", f"Allocated. Allocation ID: {out_args[-1]}")
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Database error", str(exc))

    def return_asset(self):
        if not self.active_combo.get():
            messagebox.showwarning("Missing info", "Select an active allocation.")
            return
        try:
            alloc_id = self._active_lookup[self.active_combo.get()]
            db.call_procedure("sp_return_asset", [alloc_id])
            messagebox.showinfo("Success", f"Allocation {alloc_id} returned.")
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Database error", str(exc))


# ---------------------------------------------------------------------------
# MAINTENANCE TAB
# ---------------------------------------------------------------------------
class MaintenanceTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        
        ttk.Label(self, text="Maintenance Log", style="Title.TLabel").pack(anchor="w", padx=20, pady=20)

        form = ttk.LabelFrame(self, text=" Schedule Service ", padding=15)
        form.pack(fill="x", padx=20, pady=5)

        ttk.Label(form, text="Asset:").grid(row=0, column=0, pady=5)
        self.asset_combo = ttk.Combobox(form, width=25, state="readonly")
        self.asset_combo.grid(row=0, column=1, padx=10, pady=5)

        ttk.Label(form, text="Provider:").grid(row=0, column=2, pady=5)
        self.provider_entry = ttk.Entry(form, width=20)
        self.provider_entry.grid(row=0, column=3, padx=10, pady=5)

        ttk.Label(form, text="Cost ($):").grid(row=0, column=4, pady=5)
        self.cost_entry = ttk.Entry(form, width=15)
        self.cost_entry.grid(row=0, column=5, padx=10, pady=5)

        ttk.Label(form, text="Next Service (YYYY-MM-DD):").grid(row=1, column=0, columnspan=2, pady=5)
        self.next_service_entry = ttk.Entry(form, width=20)
        self.next_service_entry.grid(row=1, column=2, padx=10, pady=5)

        ttk.Button(form, text="Schedule Task", command=self.schedule).grid(row=1, column=4, columnspan=2)

        self.tree = ttk.Treeview(self)
        self.tree.pack(fill="both", expand=True, padx=20, pady=15)

    def refresh(self):
        try:
            _, assets = db.run_query("SELECT asset_id, asset_name FROM Asset ORDER BY asset_id")
            self._asset_lookup = {f"{aid} - {name}": aid for aid, name in assets}
            self.asset_combo["values"] = list(self._asset_lookup.keys())

            columns, rows = db.run_query(
                """
                SELECT m.maintenance_id, a.asset_name, m.maintenance_date, m.provider,
                       m.cost, m.next_service_date, m.status
                FROM Asset_Maintenance m JOIN Asset a ON a.asset_id = m.asset_id
                ORDER BY m.maintenance_date DESC
                """
            )
            fill_treeview(self.tree, columns, rows)
        except Exception as exc:
            messagebox.showerror("Database error", str(exc))

    def schedule(self):
        if not (self.asset_combo.get() and self.provider_entry.get().strip()):
            messagebox.showwarning("Missing info", "Select an asset and enter a provider.")
            return
        try:
            asset_id = self._asset_lookup[self.asset_combo.get()]
            cost = float(self.cost_entry.get() or 0)
            next_service = self.next_service_entry.get().strip() or None
            out_args = db.call_procedure(
                "sp_schedule_maintenance",
                [asset_id, self.provider_entry.get().strip(), cost, next_service, 0],
            )
            messagebox.showinfo("Success", f"Maintenance scheduled. ID: {out_args[-1]}")
            self.provider_entry.delete(0, tk.END)
            self.cost_entry.delete(0, tk.END)
            self.refresh()
        except ValueError:
            messagebox.showerror("Invalid input", "Cost must be a number.")
        except Exception as exc:
            messagebox.showerror("Database error", str(exc))


# ---------------------------------------------------------------------------
# DISPOSAL TAB
# ---------------------------------------------------------------------------
class DisposalTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        
        ttk.Label(self, text="Asset Disposal Processing", style="Title.TLabel").pack(anchor="w", padx=20, pady=20)

        form = ttk.LabelFrame(self, text=" Record Disposal ", padding=15)
        form.pack(fill="x", padx=20, pady=5)

        ttk.Label(form, text="Asset:").grid(row=0, column=0)
        self.asset_combo = ttk.Combobox(form, width=30, state="readonly")
        self.asset_combo.grid(row=0, column=1, padx=10)

        ttk.Label(form, text="Method:").grid(row=0, column=2)
        self.method_combo = ttk.Combobox(form, width=20, state="readonly",
                                          values=["SOLD", "SCRAPPED", "DONATED", "RECYCLED", "LOST"])
        self.method_combo.grid(row=0, column=3, padx=10)

        ttk.Label(form, text="Scrap Value ($):").grid(row=0, column=4)
        self.scrap_entry = ttk.Entry(form, width=15)
        self.scrap_entry.grid(row=0, column=5, padx=10)

        ttk.Button(form, text="Execute Disposal", command=self.dispose).grid(row=0, column=6, padx=15)

        self.tree = ttk.Treeview(self)
        self.tree.pack(fill="both", expand=True, padx=20, pady=15)

    def refresh(self):
        try:
            _, assets = db.run_query(
                "SELECT asset_id, asset_name FROM Asset WHERE status != 'DISPOSED' ORDER BY asset_id"
            )
            self._asset_lookup = {f"{aid} - {name}": aid for aid, name in assets}
            self.asset_combo["values"] = list(self._asset_lookup.keys())

            columns, rows = db.run_query(
                """
                SELECT dp.disposal_id, a.asset_name, dp.disposal_date, dp.method, dp.scrap_value
                FROM Asset_Disposal dp JOIN Asset a ON a.asset_id = dp.asset_id
                ORDER BY dp.disposal_date DESC
                """
            )
            fill_treeview(self.tree, columns, rows)
        except Exception as exc:
            messagebox.showerror("Database error", str(exc))

    def dispose(self):
        if not (self.asset_combo.get() and self.method_combo.get()):
            messagebox.showwarning("Missing info", "Select an asset and a disposal method.")
            return
        try:
            asset_id = self._asset_lookup[self.asset_combo.get()]
            scrap_value = float(self.scrap_entry.get() or 0)
            out_args = db.call_procedure(
                "sp_dispose_asset",
                [asset_id, self.method_combo.get(), scrap_value, 0],
            )
            messagebox.showinfo("Success", f"Asset disposed. Disposal ID: {out_args[-1]}")
            self.refresh()
        except ValueError:
            messagebox.showerror("Invalid input", "Scrap value must be a number.")
        except Exception as exc:
            messagebox.showerror("Database error", str(exc))


# ---------------------------------------------------------------------------
# REPORTS TAB
# ---------------------------------------------------------------------------
class ReportsTab(ttk.Frame):
    REPORTS = [
        "Asset Inventory Report",
        "Department-wise Asset Report",
        "Maintenance Schedule Report",
        "Asset Depreciation Report",
        "Allocated Assets (Cursor Report)",
    ]

    def __init__(self, parent):
        super().__init__(parent)
        
        ttk.Label(self, text="System Reporting & Analytics", style="Title.TLabel").pack(anchor="w", padx=20, pady=20)

        bar = ttk.Frame(self, padding=10, style="Card.TFrame")
        bar.pack(fill="x", padx=20, pady=5)

        ttk.Label(bar, text="Select Report:", style="Card.TLabel").grid(row=0, column=0, padx=(0, 10))
        
        self.report_combo = ttk.Combobox(bar, values=self.REPORTS, width=40, state="readonly")
        self.report_combo.current(0)
        self.report_combo.grid(row=0, column=1, padx=10)

        ttk.Button(bar, text="Generate Report", command=self.run_report).grid(row=0, column=2, padx=10)
        ttk.Button(bar, text="Export Data to CSV", command=lambda: export_treeview_to_csv(self.tree)).grid(row=0, column=3, padx=10)

        self.tree = ttk.Treeview(self)
        self.tree.pack(fill="both", expand=True, padx=20, pady=15)

    def run_report(self):
        choice = self.report_combo.get()
        try:
            if choice == "Asset Inventory Report":
                columns, rows = db.run_query("SELECT * FROM Asset ORDER BY asset_id")

            elif choice == "Department-wise Asset Report":
                columns, rows = db.run_query(
                    """
                    SELECT d.dept_name, a.category, COUNT(*) AS asset_count, SUM(a.cost) AS total_cost
                    FROM Asset_Allocation al
                    JOIN Asset a ON a.asset_id = al.asset_id
                    JOIN Department d ON d.dept_id = al.dept_id
                    WHERE al.status = 'ACTIVE'
                    GROUP BY d.dept_name, a.category
                    ORDER BY d.dept_name
                    """
                )

            elif choice == "Maintenance Schedule Report":
                columns, rows = db.run_query(
                    """
                    SELECT a.asset_name, m.provider, m.maintenance_date, m.next_service_date,
                           m.cost, m.status,
                           CASE WHEN m.next_service_date < CURDATE() THEN 'YES' ELSE 'NO' END AS overdue
                    FROM Asset_Maintenance m JOIN Asset a ON a.asset_id = m.asset_id
                    ORDER BY m.next_service_date
                    """
                )

            elif choice == "Asset Depreciation Report":
                _, assets = db.run_query("SELECT asset_id, asset_name, cost FROM Asset ORDER BY asset_id")
                columns = ["asset_id", "asset_name", "cost", "current_value", "depreciation_pct"]
                rows = []
                for asset_id, name, cost in assets:
                    current_value = db.call_function("fn_calculate_depreciation", (asset_id, 5))
                    pct = round(100 * (float(cost) - float(current_value)) / float(cost), 1) if cost else 0
                    rows.append((asset_id, name, cost, current_value, f"{pct}%"))

            else:  # Allocated Assets (Cursor Report)
                columns, rows = db.call_procedure_with_result_set("sp_list_allocated_assets")

            fill_treeview(self.tree, columns, rows)
        except Exception as exc:
            messagebox.showerror("Database error", str(exc))

# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    login = LoginWindow()
    login.mainloop()