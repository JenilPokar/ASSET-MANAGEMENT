# Asset Management System — Multi-Tenant SaaS Edition (Documentation)

**Developed by Jenil Pokar | Roll No. 46 | FY AI-DS**

## 1. Architecture

- **Database (primary deliverable):** MySQL 8.0+, built in MySQL Workbench.
  - `01_mysql_multitenant_schema_and_data.sql` — schema, constraints, mock data
    for 3 tenant companies
  - `02_mysql_multitenant_procedures_functions_triggers.sql` — procedures,
    functions, triggers, cursor, and the Super Admin overview procedure
- **Web front-end:** Flask (Python), server-rendered with Jinja templates
  - `app.py` — routing and page logic
  - `db_connector.py` — MySQL connection pool + procedure/function wrappers
  - `templates/` — HTML pages (login, dashboard, assets, org, allocation,
    maintenance, disposal, reports, super admin)
- **Deployment target:** Render web service (`requirements.txt` + `Procfile`)

## 2. Local Setup

### Step 1 — Database (MySQL Workbench)
1. Connect Workbench to your MySQL server.
2. Run `01_mysql_multitenant_schema_and_data.sql` in full.
3. Run `02_mysql_multitenant_procedures_functions_triggers.sql` in full.
4. Confirm no error icons under `asset_management_saas` → Stored Procedures / Functions.

### Step 2 — Python environment
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 3 — Configure the connection
Set these as environment variables (or edit the defaults in `db_connector.py`):
```bash
export DB_HOST=localhost
export DB_PORT=3306
export DB_USER=root
export DB_PASSWORD=YourPassword123
export DB_NAME=asset_management_saas
export SECRET_KEY=some-random-string
```

### Step 4 — Run
```bash
python app.py
```
Visit `http://localhost:5000`.

## 3. Seeded Logins

| Username | Role | Password | Company |
|---|---|---|---|
| `superadmin` | SUPER_ADMIN | `Super@123` | — (platform-wide) |
| `gf_admin` | ADMIN | `Green@123` | Greenfield Public School |
| `sr_admin` | ADMIN | `Sunrise@123` | Sunrise Multispecialty Hospital |
| `ap_admin` | ADMIN | `Apex@123` | Apex Precision Industries |
| `gf_store` | STORE_MANAGER | `Store@123` | Greenfield Public School |
| `sr_dept` | DEPT_USER | `Dept@123` | Sunrise Multispecialty Hospital |

Log in as `superadmin` to see the Platform Overview (all 3 companies, their
asset counts, and billing status). Log in as any company account to see that
portal's assets only — try `gf_admin` then `sr_admin` back-to-back to confirm
neither sees the other's data.

## 4. Deploying to Render

1. Push this project to a Git repository.
2. In Render: **New → Web Service**, connect the repo.
3. Render auto-detects Python; confirm:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app` (also set in `Procfile`)
4. Under **Environment**, add: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`,
   `DB_NAME`, `SECRET_KEY`. Point these at a MySQL instance reachable from
   Render (e.g. Render's own managed MySQL/PlanetScale/Aiven — Render does
   not host MySQL directly, so use an external managed MySQL provider or a
   Render PostgreSQL-compatible alternative if you adapt the SQL).
5. Deploy. Render builds the container and runs the app on the assigned port
   automatically (the app reads `PORT` from the environment).

## 5. Multi-Tenancy & Security Notes

- Every table except `Company`, `Subscription_Billing`, and `User_Login`
  (for the Super Admin row) carries a `company_id` column.
- Every stored procedure takes `company_id` as an explicit parameter and
  re-validates that the asset/employee/department it's given actually
  belongs to that company — a forged ID for another tenant is rejected with
  a clean error, not silently allowed.
- Triggers add a second layer of the same check directly at the database
  level, independent of the application code.
- Passwords are stored as `SHA2(password, 256)` hashes; the Flask app hashes
  the login attempt the same way before comparing — plaintext passwords are
  never stored or transmitted to the database.

## 6. Warranty Dropdown & Live Clock

- The asset warranty field is a `<select>` with options **1 / 2 / 3 / 4
  years** (see `templates/assets.html`), not a manual date. The database
  stores `warranty_years` and derives `warranty_expiry_date` automatically
  via a MySQL **generated column**, so the 30-day warranty-alert trigger
  keeps working without the user ever typing a date.
- The header clock (`templates/base.html`) updates every second client-side
  via JavaScript (`setInterval` + `Date().toLocaleString()`) — no server
  round-trip needed for "real-time" display.

## 7. Business Logic Reference

| Object | Purpose |
|---|---|
| `sp_register_asset` | Registers an asset scoped to a company; rejects duplicate serials *within that company* |
| `sp_allocate_asset` | Allocates an asset after validating asset/employee/dept all belong to the same company |
| `sp_return_asset` | Returns an active allocation |
| `sp_schedule_maintenance` | Logs maintenance; blocks disposed assets / past-dated schedules |
| `sp_dispose_asset` | Disposes an asset; blocks if still allocated |
| `sp_update_asset_details` | Updates editable asset fields, including warranty years |
| `fn_calculate_depreciation` | Straight-line depreciation, 10% residual floor |
| `fn_check_availability` | Y/N allocation eligibility check |
| `fn_total_maintenance_cost` | Total maintenance spend for an asset |
| `fn_count_assets_by_dept` | Active allocation count per department |
| `trg_alloc_before_insert` / `_after_insert` / `_after_update` | Tenant + status guard, status sync |
| `trg_maint_after_insert` / `_after_update` | Maintenance status sync |
| `trg_disposal_before_insert` / `_after_insert` | Disposal guard + status sync |
| `trg_warranty_alert_insert` / `_update` | 30-day warranty expiry alerts |
| `sp_list_allocated_assets` | Cursor-driven per-company allocation report with live depreciation |
| `sp_super_admin_company_overview` | Powers the Super Admin dashboard (all companies + billing) |

## 8. Known Limitations / Next Steps

- Render does not provide managed MySQL directly — pair with an external
  provider (PlanetScale, Aiven, Railway, or your own MySQL host) for a live
  deployment.
- Company self-registration (a public sign-up form that inserts into
  `Company` + creates the first `ADMIN` login) isn't wired up yet — companies
  are currently seeded via the mock data script. Add a `/register` route if
  self-service onboarding is required.
- Add rate limiting / login lockout for production use beyond a class demo.
