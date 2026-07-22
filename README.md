# ASSET-MANAGEMENT
This project is a complete Asset Management System featuring a custom-themed, interactive Python Tkinter front-end for intuitive user navigation and data management.  It is powered by a robust MySQL backend that handles all core business logic securely through stored procedures, functions, and automated triggers.
# Asset Management System — Technical Documentation (MySQL + Tkinter Edition)

## 1. Project Overview

The database is the core deliverable: a normalized MySQL schema with stored
procedures, functions, triggers, and a cursor-driven report, built and run in
**MySQL Workbench**. The Python side is a thin **Tkinter** desktop front-end
that calls those database objects — it holds no business logic of its own.

- **Back-end (primary):** MySQL 8.0+, authored/run in MySQL Workbench
  - `01_mysql_schema_and_data.sql` — schema + constraints + mock data
  - `02_mysql_procedures_functions_triggers.sql` — procedures, functions,
    triggers, and the cursor-based report
- **Front-end:** Python + Tkinter, connecting via `mysql-connector-python`
  - `db_connector.py` — all database plumbing (connection, query/procedure calls)
  - `main_app.py` — the Tkinter GUI (login window + tabbed main window)

## 2. Setting Up the Database in MySQL Workbench

1. Open MySQL Workbench and connect to your MySQL server (local or remote).
2. Open `01_mysql_schema_and_data.sql` as a new SQL tab and execute the whole
   script (the lightning-bolt "Execute" icon, or Ctrl+Shift+Enter). This
   creates the `asset_management` database, all 8 tables, indexes, and seed data.
3. Open `02_mysql_procedures_functions_triggers.sql` in a new tab (same
   connection) and execute it in full. This creates:
   - 6 stored procedures (register, allocate, return, schedule maintenance,
     dispose, update asset)
   - 4 stored functions (depreciation, availability check, maintenance cost
     total, department asset count)
   - 9 triggers (allocation guard + status sync, maintenance status sync,
     disposal guard + status sync, warranty alerts on insert/update)
   - 1 cursor-driven procedure, `sp_list_allocated_assets`
4. Confirm everything compiled: in the Workbench schema browser, expand
   `asset_management` → **Stored Procedures** and **Functions** — you should
   see all of the objects above with no error markers.
5. Quick sanity check straight in Workbench:
   ```sql
   USE asset_management;
   CALL sp_list_allocated_assets();
   ```
   (Returns no rows until you've allocated at least one asset — see Section 5.)

## 3. Python Environment Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install mysql-connector-python
```

Tkinter ships with standard Python installations on Windows/macOS; on Linux
you may need `sudo apt install python3-tk` if it isn't already present.

Edit the `DB_CONFIG` dictionary at the top of `db_connector.py` with your
actual MySQL host, port, username, and password:

```python
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "YourPassword123",
    "database": "asset_management",
}
```

## 4. Running the Application

```bash
python main_app.py
```

A login window appears first. Use one of the seeded accounts:

| Username | Role | Password |
|---|---|---|
| `admin` | ADMIN | `Admin@123` |
| `rverma` | MANAGER | `Rohan@123` |
| `kiyer` | VIEWER | `Kavya@123` |

After login, the main window opens with tabs: **Dashboard, Asset Management,
Departments, Employees, Allocation, Maintenance, Disposal, Reports.**

## 5. Suggested Demo Flow

1. **Asset Management** → confirm the 4 seeded assets show up.
2. **Allocation** → allocate one asset to an employee/department, confirm its
   status flips to `ALLOCATED` in the Asset Management tab (proves the
   trigger fired).
3. Try allocating the same asset again — the stored procedure raises an
   error ("Asset is already allocated"), which the GUI surfaces via a message box.
4. **Maintenance** → schedule maintenance on a different asset; confirm its
   status becomes `UNDER_MAINTENANCE`.
5. **Reports** → run "Allocated Assets (Cursor Report)" to see
   `sp_list_allocated_assets` in action (depreciation value computed live by
   `fn_calculate_depreciation`).
6. **Disposal** → try disposing the still-allocated asset from step 2 — the
   `trg_disposal_before_insert` trigger blocks it; return it first, then dispose.

## 6. Relational Schema (ER Diagram Mapping — text form)

```
DEPARTMENT (dept_id PK, dept_name, dept_head, created_on)
      │ 1
      │ N
EMPLOYEE (employee_id PK, employee_name, dept_id FK -> DEPARTMENT, designation, email, created_on)
      │ 1                                   │ 1
      │ N                                   │ N
ASSET_ALLOCATION (allocation_id PK,         │
   asset_id FK -> ASSET,                    │
   employee_id FK -> EMPLOYEE,              │
   dept_id FK -> DEPARTMENT,                │
   allocation_date, return_date, status)    │
      │ N                                   │
      │ 1                                   │
ASSET (asset_id PK, asset_name, category, model, serial_number UNIQUE,
       purchase_date, cost, warranty_expiry, status, created_on)
      │ 1
      ├────────────< ASSET_MAINTENANCE (maintenance_id PK, asset_id FK, maintenance_date,
      │                                 provider, cost, next_service_date, status)
      ├────────────< ASSET_DISPOSAL (disposal_id PK, asset_id FK UNIQUE, disposal_date,
      │                              method, scrap_value)
      └────────────< WARRANTY_ALERT_LOG (alert_id PK, asset_id FK, alert_message, alert_date)

USER_LOGIN (username PK, password_hash, role, employee_id FK -> EMPLOYEE, created_on)
```

**Cardinality summary**
- Department 1 : N Employee
- Department 1 : N Asset_Allocation
- Employee 1 : N Asset_Allocation
- Asset 1 : N Asset_Allocation / Asset_Maintenance / Warranty_Alert_Log
- Asset 1 : 1 Asset_Disposal (disposed at most once)
- Employee 1 : 0..1 User_Login

## 7. Business Logic Reference

| Object | Purpose |
|---|---|
| `sp_register_asset` | Insert a new asset; rejects duplicate serial numbers |
| `sp_allocate_asset` | Allocate an available asset; blocks if allocated/under maintenance/disposed |
| `sp_return_asset` | Marks allocation RETURNED, frees the asset |
| `sp_schedule_maintenance` | Logs maintenance; blocks disposed assets and past-dated schedules |
| `sp_dispose_asset` | Disposes an asset; blocks if currently allocated |
| `sp_update_asset_details` | Updates editable asset fields |
| `fn_calculate_depreciation` | Straight-line depreciation with a 10% residual floor |
| `fn_check_availability` | Returns Y/N for allocation eligibility |
| `fn_total_maintenance_cost` | Sums maintenance spend for an asset |
| `fn_count_assets_by_dept` | Counts active allocations per department |
| `trg_alloc_before_insert` / `_after_insert` / `_after_update` | Guards + syncs Asset.status on allocation/return |
| `trg_maint_after_insert` / `_after_update` | Syncs Asset.status on maintenance start/completion |
| `trg_disposal_before_insert` / `_after_insert` | Blocks disposal of allocated assets; marks DISPOSED |
| `trg_warranty_alert_insert` / `_update` | Logs an alert when warranty expiry is within 30 days |
| `sp_list_allocated_assets` | Cursor-driven procedure joining allocation + employee + dept + latest maintenance status + live depreciation |

## 8. Why MySQL Instead of SQLite for This Project

SQLite is file-based, single-user, and has no native stored
procedure/function/trigger language — it can't host the PL/SQL-style business
logic (`sp_*`, `fn_*`, triggers) this rubric asks for. MySQL (via Workbench)
supports all of that plus proper multi-user access control (`User_Login` +
roles), which is why it's the primary DBMS here. `mysql-connector-python`
is the official, actively maintained driver — no separate Oracle/SQLite
client libraries are needed.

## 9. Known Limitations / Next Steps

- Password storage uses `SHA2(..., 256)`; a production system should add
  per-user salting (e.g. via `bcrypt` in Python before insert).
- `db_connector.py` keeps a single shared connection; a heavier multi-user
  deployment should use `mysql.connector.pooling.MySQLConnectionPool`.
- Date fields are plain-text `YYYY-MM-DD` entries in the Tkinter forms; swap
  in a calendar widget (e.g. `tkcalendar.DateEntry`) if you want a picker.
