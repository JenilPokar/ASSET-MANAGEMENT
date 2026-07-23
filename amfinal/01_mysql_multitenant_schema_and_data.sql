-- ============================================================================
-- ASSET MANAGEMENT SYSTEM -- MULTI-TENANT SAAS EDITION
-- SECTION 3: DATABASE DESIGN & SQL IMPLEMENTATION  (MySQL 8.0+ / Workbench)
-- Developed by Jenil Pokar | Roll No. 46 | FY AI-DS
-- ============================================================================
-- Every operational table carries a company_id column so that each
-- registered organization (school, hospital, industry, etc.) only ever
-- sees its own rows. Isolation is enforced at two levels:
--   1. Every application query is scoped with "WHERE company_id = %s"
--      (see db_connector.py / app.py).
--   2. Every stored procedure re-validates that the asset/employee/
--      department referenced actually belongs to the calling company_id,
--      so a forged ID from another tenant is rejected at the DB layer too.
-- ============================================================================

DROP DATABASE IF EXISTS asset_management_saas;
CREATE DATABASE asset_management_saas CHARACTER SET utf8mb4;
USE asset_management_saas;

-- ============================================================================
-- 1. COMPANY  (the tenant itself -- schools, hospitals, industries, etc.)
-- ============================================================================
CREATE TABLE Company (
    company_id          INT             AUTO_INCREMENT PRIMARY KEY,
    company_name        VARCHAR(150)    NOT NULL UNIQUE,
    industry_type       VARCHAR(30)     NOT NULL DEFAULT 'OTHER'
                            CHECK (industry_type IN ('EDUCATION','HEALTHCARE','INDUSTRY','OTHER')),
    contact_email       VARCHAR(120)    NOT NULL UNIQUE,
    contact_phone       VARCHAR(20),
    subscription_status VARCHAR(20)     NOT NULL DEFAULT 'TRIAL'
                            CHECK (subscription_status IN ('TRIAL','ACTIVE','SUSPENDED','CANCELLED')),
    registered_on       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ============================================================================
-- 2. SUBSCRIPTION_BILLING  (feeds the Super Admin billing dashboard)
-- ============================================================================
CREATE TABLE Subscription_Billing (
    billing_id      INT             AUTO_INCREMENT PRIMARY KEY,
    company_id      INT             NOT NULL,
    plan_name       VARCHAR(50)     NOT NULL DEFAULT 'BASIC'
                        CHECK (plan_name IN ('BASIC','STANDARD','PREMIUM')),
    amount          DECIMAL(10,2)   NOT NULL CHECK (amount >= 0),
    billing_date    DATE            NOT NULL DEFAULT (CURRENT_DATE),
    status          VARCHAR(20)     NOT NULL DEFAULT 'PENDING'
                        CHECK (status IN ('PAID','PENDING','OVERDUE')),
    CONSTRAINT fk_billing_company FOREIGN KEY (company_id) REFERENCES Company(company_id)
) ENGINE=InnoDB;

-- ============================================================================
-- 3. DEPARTMENT (scoped per company)
-- ============================================================================
CREATE TABLE Department (
    dept_id         INT             AUTO_INCREMENT PRIMARY KEY,
    company_id      INT             NOT NULL,
    dept_name       VARCHAR(100)    NOT NULL,
    dept_head       VARCHAR(100)    NOT NULL,
    created_on      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_dept_company FOREIGN KEY (company_id) REFERENCES Company(company_id),
    CONSTRAINT uq_dept_per_company UNIQUE (company_id, dept_name)
) ENGINE=InnoDB;

-- ============================================================================
-- 4. EMPLOYEE (scoped per company)
-- ============================================================================
CREATE TABLE Employee (
    employee_id     INT             AUTO_INCREMENT PRIMARY KEY,
    company_id      INT             NOT NULL,
    employee_name   VARCHAR(100)    NOT NULL,
    dept_id         INT             NOT NULL,
    designation     VARCHAR(80)     NOT NULL,
    email           VARCHAR(120),
    created_on      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_emp_company FOREIGN KEY (company_id) REFERENCES Company(company_id),
    CONSTRAINT fk_emp_dept    FOREIGN KEY (dept_id) REFERENCES Department(dept_id),
    CONSTRAINT uq_emp_email_per_company UNIQUE (company_id, email)
) ENGINE=InnoDB;

-- ============================================================================
-- 5. ASSET (scoped per company)
-- warranty_years is the dropdown value (1/2/3/4); warranty_expiry_date is
-- derived automatically so the 30-day warranty trigger keeps working.
-- ============================================================================
CREATE TABLE Asset (
    asset_id            INT             AUTO_INCREMENT PRIMARY KEY,
    company_id          INT             NOT NULL,
    asset_name          VARCHAR(120)    NOT NULL,
    category            VARCHAR(60)     NOT NULL,
    model               VARCHAR(100),
    serial_number       VARCHAR(100)    NOT NULL,
    purchase_date       DATE            NOT NULL,
    cost                DECIMAL(12,2)   NOT NULL CHECK (cost >= 0),
    warranty_years       TINYINT        NOT NULL DEFAULT 1 CHECK (warranty_years IN (1,2,3,4)),
    warranty_expiry_date DATE GENERATED ALWAYS AS
                            (DATE_ADD(purchase_date, INTERVAL warranty_years YEAR)) STORED,
    status              VARCHAR(20)     NOT NULL DEFAULT 'AVAILABLE'
                            CHECK (status IN ('AVAILABLE','ALLOCATED','UNDER_MAINTENANCE','DISPOSED')),
    created_on          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_asset_company FOREIGN KEY (company_id) REFERENCES Company(company_id),
    CONSTRAINT uq_serial_per_company UNIQUE (company_id, serial_number)
) ENGINE=InnoDB;

-- ============================================================================
-- 6. ASSET_ALLOCATION
-- ============================================================================
CREATE TABLE Asset_Allocation (
    allocation_id       INT             AUTO_INCREMENT PRIMARY KEY,
    company_id          INT             NOT NULL,
    asset_id            INT             NOT NULL,
    employee_id         INT             NOT NULL,
    dept_id             INT             NOT NULL,
    allocation_date     DATE            NOT NULL DEFAULT (CURRENT_DATE),
    return_date         DATE,
    status              VARCHAR(20)     NOT NULL DEFAULT 'ACTIVE'
                            CHECK (status IN ('ACTIVE','RETURNED')),
    CONSTRAINT fk_alloc_company FOREIGN KEY (company_id) REFERENCES Company(company_id),
    CONSTRAINT fk_alloc_asset   FOREIGN KEY (asset_id) REFERENCES Asset(asset_id),
    CONSTRAINT fk_alloc_emp     FOREIGN KEY (employee_id) REFERENCES Employee(employee_id),
    CONSTRAINT fk_alloc_dept    FOREIGN KEY (dept_id) REFERENCES Department(dept_id),
    CONSTRAINT chk_return_after_alloc CHECK (return_date IS NULL OR return_date >= allocation_date)
) ENGINE=InnoDB;

-- ============================================================================
-- 7. ASSET_MAINTENANCE
-- ============================================================================
CREATE TABLE Asset_Maintenance (
    maintenance_id      INT             AUTO_INCREMENT PRIMARY KEY,
    company_id          INT             NOT NULL,
    asset_id            INT             NOT NULL,
    maintenance_date    DATE            NOT NULL DEFAULT (CURRENT_DATE),
    provider             VARCHAR(120)   NOT NULL,
    cost                 DECIMAL(10,2)  NOT NULL DEFAULT 0 CHECK (cost >= 0),
    next_service_date    DATE,
    status               VARCHAR(20)    NOT NULL DEFAULT 'IN_PROGRESS'
                            CHECK (status IN ('IN_PROGRESS','COMPLETED')),
    CONSTRAINT fk_maint_company FOREIGN KEY (company_id) REFERENCES Company(company_id),
    CONSTRAINT fk_maint_asset   FOREIGN KEY (asset_id) REFERENCES Asset(asset_id),
    CONSTRAINT chk_next_service CHECK (next_service_date IS NULL OR next_service_date >= maintenance_date)
) ENGINE=InnoDB;

-- ============================================================================
-- 8. ASSET_DISPOSAL
-- ============================================================================
CREATE TABLE Asset_Disposal (
    disposal_id     INT             AUTO_INCREMENT PRIMARY KEY,
    company_id      INT             NOT NULL,
    asset_id        INT             NOT NULL UNIQUE,
    disposal_date   DATE            NOT NULL DEFAULT (CURRENT_DATE),
    method          VARCHAR(60)     NOT NULL
                        CHECK (method IN ('SOLD','SCRAPPED','DONATED','RECYCLED','LOST')),
    scrap_value     DECIMAL(10,2)   NOT NULL DEFAULT 0 CHECK (scrap_value >= 0),
    CONSTRAINT fk_disp_company FOREIGN KEY (company_id) REFERENCES Company(company_id),
    CONSTRAINT fk_disp_asset   FOREIGN KEY (asset_id) REFERENCES Asset(asset_id)
) ENGINE=InnoDB;

-- ============================================================================
-- 9. USER_LOGIN
-- Two-tier: SUPER_ADMIN rows have company_id = NULL (platform owner);
-- every other role must belong to exactly one company.
-- ============================================================================
CREATE TABLE User_Login (
    username        VARCHAR(50)     PRIMARY KEY,
    password_hash   VARCHAR(256)    NOT NULL,
    role            VARCHAR(20)     NOT NULL DEFAULT 'DEPT_USER'
                        CHECK (role IN ('SUPER_ADMIN','ADMIN','STORE_MANAGER','DEPT_USER')),
    company_id      INT,
    employee_id     INT,
    created_on      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_login_company  FOREIGN KEY (company_id) REFERENCES Company(company_id),
    CONSTRAINT fk_login_emp      FOREIGN KEY (employee_id) REFERENCES Employee(employee_id),
    CONSTRAINT chk_super_admin_no_company
        CHECK ( (role = 'SUPER_ADMIN' AND company_id IS NULL)
             OR (role <> 'SUPER_ADMIN' AND company_id IS NOT NULL) )
) ENGINE=InnoDB;

-- ============================================================================
-- 10. WARRANTY_ALERT_LOG
-- ============================================================================
CREATE TABLE Warranty_Alert_Log (
    alert_id        INT             AUTO_INCREMENT PRIMARY KEY,
    company_id      INT             NOT NULL,
    asset_id        INT             NOT NULL,
    alert_message   VARCHAR(300)    NOT NULL,
    alert_date      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_alert_company FOREIGN KEY (company_id) REFERENCES Company(company_id),
    CONSTRAINT fk_alert_asset   FOREIGN KEY (asset_id) REFERENCES Asset(asset_id)
) ENGINE=InnoDB;

-- Helpful indexes
CREATE INDEX idx_asset_company        ON Asset(company_id);
CREATE INDEX idx_asset_status         ON Asset(status);
CREATE INDEX idx_alloc_company_asset  ON Asset_Allocation(company_id, asset_id);
CREATE INDEX idx_maint_company_asset  ON Asset_Maintenance(company_id, asset_id);
CREATE INDEX idx_employee_company     ON Employee(company_id);
CREATE INDEX idx_department_company   ON Department(company_id);

-- ============================================================================
-- MOCK DATA -- two tenant companies, so isolation is visibly testable
-- ============================================================================

-- --- Companies -------------------------------------------------------------
INSERT INTO Company (company_name, industry_type, contact_email, contact_phone, subscription_status) VALUES
    ('Greenfield Public School', 'EDUCATION', 'admin@greenfieldschool.edu', '9820011122', 'ACTIVE'),
    ('Sunrise Multispecialty Hospital', 'HEALTHCARE', 'it@sunrisehospital.in', '9820033344', 'TRIAL'),
    ('Apex Precision Industries', 'INDUSTRY', 'ops@apexprecision.com', '9820055566', 'ACTIVE');

INSERT INTO Subscription_Billing (company_id, plan_name, amount, billing_date, status) VALUES
    (1, 'STANDARD', 4999.00, '2026-07-01', 'PAID'),
    (2, 'BASIC',    1999.00, '2026-07-10', 'PENDING'),
    (3, 'PREMIUM',  9999.00, '2026-07-05', 'PAID'),
    (1, 'STANDARD', 4999.00, '2026-06-01', 'PAID');

-- --- Departments -------------------------------------------------------------
INSERT INTO Department (company_id, dept_name, dept_head) VALUES
    (1, 'Computer Lab', 'Mrs. Deshmukh'),
    (1, 'Administration', 'Mr. Kulkarni'),
    (2, 'Radiology', 'Dr. Anjali Menon'),
    (2, 'ICU', 'Dr. Faisal Shaikh'),
    (3, 'Production Floor', 'Mr. Sanjay Patil');

-- --- Employees -------------------------------------------------------------
INSERT INTO Employee (company_id, employee_name, dept_id, designation, email) VALUES
    (1, 'Neha Joshi', 1, 'Lab Assistant', 'neha.joshi@greenfieldschool.edu'),
    (1, 'Ramesh Iyer', 2, 'Office Clerk', 'ramesh.iyer@greenfieldschool.edu'),
    (2, 'Dr. Anjali Menon', 3, 'Radiologist', 'anjali.menon@sunrisehospital.in'),
    (2, 'Suresh Nair', 4, 'ICU Technician', 'suresh.nair@sunrisehospital.in'),
    (3, 'Pooja Salunkhe', 5, 'Machine Operator', 'pooja.salunkhe@apexprecision.com');

-- --- Assets ------------------------------------------------------------------
INSERT INTO Asset (company_id, asset_name, category, model, serial_number, purchase_date, cost, warranty_years, status) VALUES
    (1, 'Dell OptiPlex Desktop', 'Computer', 'OptiPlex 3090', 'GF-PC-001', '2024-06-01', 45000.00, 2, 'AVAILABLE'),
    (1, 'Epson Projector', 'Projector', 'EB-X05', 'GF-PRJ-002', '2023-08-15', 32000.00, 1, 'AVAILABLE'),
    (2, 'GE Ultrasound Machine', 'Machinery', 'Voluson E8', 'SR-USG-101', '2022-02-10', 1250000.00, 4, 'AVAILABLE'),
    (2, 'HP LaserJet Printer', 'Printer', 'LaserJet Pro M404', 'SR-PRN-102', '2023-11-01', 21000.00, 1, 'AVAILABLE'),
    (3, 'CNC Milling Machine', 'Machinery', 'Haas VF-2', 'AP-CNC-201', '2021-05-20', 3200000.00, 3, 'AVAILABLE'),
    (3, 'Lenovo ThinkPad Laptop', 'Laptop', 'ThinkPad T14', 'AP-LAP-202', '2024-01-15', 82000.00, 2, 'AVAILABLE');

-- --- User logins ---------------------------------------------------------
-- Plaintext passwords shown here for demo/grading only; the app stores SHA-256 hashes.
INSERT INTO User_Login (username, password_hash, role, company_id, employee_id) VALUES
    ('superadmin', SHA2('Super@123', 256), 'SUPER_ADMIN', NULL, NULL),
    ('gf_admin',   SHA2('Green@123', 256), 'ADMIN',         1, NULL),
    ('sr_admin',   SHA2('Sunrise@123', 256), 'ADMIN',       2, NULL),
    ('ap_admin',   SHA2('Apex@123', 256), 'ADMIN',          3, NULL),
    ('gf_store',   SHA2('Store@123', 256), 'STORE_MANAGER', 1, 1),
    ('sr_dept',    SHA2('Dept@123', 256), 'DEPT_USER',      2, 3);
