-- ============================================================================
-- ASSET MANAGEMENT SYSTEM
-- PHASE 1: DATABASE DESIGN & SQL IMPLEMENTATION  (MySQL / MySQL Workbench)
-- Target: MySQL 8.0+ (CHECK constraints are enforced from 8.0.16 onward)
-- ============================================================================
-- Open this file in MySQL Workbench and run it top-to-bottom as a script
-- (lightning-bolt icon), or via CLI:  mysql -u root -p < 01_mysql_schema_and_data.sql

DROP DATABASE IF EXISTS asset_management;
CREATE DATABASE asset_management CHARACTER SET utf8mb4;
USE asset_management;

-- ============================================================================
-- 1. DEPARTMENT
-- ============================================================================
CREATE TABLE Department (
    dept_id         INT             AUTO_INCREMENT PRIMARY KEY,
    dept_name       VARCHAR(100)    NOT NULL UNIQUE,
    dept_head       VARCHAR(100)    NOT NULL,
    created_on      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ============================================================================
-- 2. EMPLOYEE
-- ============================================================================
CREATE TABLE Employee (
    employee_id     INT             AUTO_INCREMENT PRIMARY KEY,
    employee_name   VARCHAR(100)    NOT NULL,
    dept_id         INT             NOT NULL,
    designation     VARCHAR(80)     NOT NULL,
    email           VARCHAR(120)    UNIQUE,
    created_on      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_emp_dept FOREIGN KEY (dept_id) REFERENCES Department(dept_id)
) ENGINE=InnoDB;

-- ============================================================================
-- 3. ASSET
-- ============================================================================
CREATE TABLE Asset (
    asset_id            INT             AUTO_INCREMENT PRIMARY KEY,
    asset_name          VARCHAR(120)    NOT NULL,
    category            VARCHAR(60)     NOT NULL,
    model               VARCHAR(100),
    serial_number       VARCHAR(100)    NOT NULL UNIQUE,
    purchase_date       DATE            NOT NULL,
    cost                DECIMAL(12,2)   NOT NULL CHECK (cost >= 0),
    warranty_expiry     DATE,
    status              VARCHAR(20)     NOT NULL DEFAULT 'AVAILABLE'
                            CHECK (status IN ('AVAILABLE','ALLOCATED','UNDER_MAINTENANCE','DISPOSED')),
    created_on          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_warranty_after_purchase
        CHECK (warranty_expiry IS NULL OR warranty_expiry >= purchase_date)
) ENGINE=InnoDB;

-- ============================================================================
-- 4. ASSET_ALLOCATION
-- ============================================================================
CREATE TABLE Asset_Allocation (
    allocation_id       INT             AUTO_INCREMENT PRIMARY KEY,
    asset_id            INT             NOT NULL,
    employee_id         INT             NOT NULL,
    dept_id             INT             NOT NULL,
    allocation_date     DATE            NOT NULL DEFAULT (CURRENT_DATE),
    return_date         DATE,
    status              VARCHAR(20)     NOT NULL DEFAULT 'ACTIVE'
                            CHECK (status IN ('ACTIVE','RETURNED')),
    CONSTRAINT fk_alloc_asset FOREIGN KEY (asset_id) REFERENCES Asset(asset_id),
    CONSTRAINT fk_alloc_emp   FOREIGN KEY (employee_id) REFERENCES Employee(employee_id),
    CONSTRAINT fk_alloc_dept  FOREIGN KEY (dept_id) REFERENCES Department(dept_id),
    CONSTRAINT chk_return_after_alloc
        CHECK (return_date IS NULL OR return_date >= allocation_date)
) ENGINE=InnoDB;

-- ============================================================================
-- 5. ASSET_MAINTENANCE
-- ============================================================================
CREATE TABLE Asset_Maintenance (
    maintenance_id      INT             AUTO_INCREMENT PRIMARY KEY,
    asset_id            INT             NOT NULL,
    maintenance_date    DATE            NOT NULL DEFAULT (CURRENT_DATE),
    provider            VARCHAR(120)    NOT NULL,
    cost                DECIMAL(10,2)   NOT NULL DEFAULT 0 CHECK (cost >= 0),
    next_service_date   DATE,
    status              VARCHAR(20)     NOT NULL DEFAULT 'IN_PROGRESS'
                            CHECK (status IN ('IN_PROGRESS','COMPLETED')),
    CONSTRAINT fk_maint_asset FOREIGN KEY (asset_id) REFERENCES Asset(asset_id),
    CONSTRAINT chk_next_service
        CHECK (next_service_date IS NULL OR next_service_date >= maintenance_date)
) ENGINE=InnoDB;

-- ============================================================================
-- 6. ASSET_DISPOSAL
-- ============================================================================
CREATE TABLE Asset_Disposal (
    disposal_id         INT             AUTO_INCREMENT PRIMARY KEY,
    asset_id            INT             NOT NULL UNIQUE,
    disposal_date       DATE            NOT NULL DEFAULT (CURRENT_DATE),
    method              VARCHAR(60)     NOT NULL
                            CHECK (method IN ('SOLD','SCRAPPED','DONATED','RECYCLED','LOST')),
    scrap_value         DECIMAL(10,2)   NOT NULL DEFAULT 0 CHECK (scrap_value >= 0),
    CONSTRAINT fk_disp_asset FOREIGN KEY (asset_id) REFERENCES Asset(asset_id)
) ENGINE=InnoDB;

-- ============================================================================
-- 7. USER_LOGIN
-- ============================================================================
CREATE TABLE User_Login (
    username        VARCHAR(50)     PRIMARY KEY,
    password_hash   VARCHAR(256)    NOT NULL,   -- SHA2 hash, never plaintext
    role            VARCHAR(20)     NOT NULL DEFAULT 'VIEWER'
                        CHECK (role IN ('ADMIN','MANAGER','VIEWER')),
    employee_id     INT,
    created_on      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_login_emp FOREIGN KEY (employee_id) REFERENCES Employee(employee_id)
) ENGINE=InnoDB;

-- ============================================================================
-- 8. WARRANTY_ALERT_LOG (supporting table for the warranty-expiry trigger)
-- ============================================================================
CREATE TABLE Warranty_Alert_Log (
    alert_id        INT             AUTO_INCREMENT PRIMARY KEY,
    asset_id        INT             NOT NULL,
    alert_message   VARCHAR(300)    NOT NULL,
    alert_date      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_alert_asset FOREIGN KEY (asset_id) REFERENCES Asset(asset_id)
) ENGINE=InnoDB;

-- Helpful indexes for frequent lookups
CREATE INDEX idx_alloc_asset  ON Asset_Allocation(asset_id);
CREATE INDEX idx_alloc_emp    ON Asset_Allocation(employee_id);
CREATE INDEX idx_maint_asset  ON Asset_Maintenance(asset_id);
CREATE INDEX idx_asset_status ON Asset(status);

-- ============================================================================
-- MOCK DATA (DML) -- 3-4 rows per table for testing
-- ============================================================================

INSERT INTO Department (dept_name, dept_head) VALUES
    ('Information Technology', 'Rina Kapoor'),
    ('Human Resources', 'Sameer Joshi'),
    ('Finance', 'Priya Nair'),
    ('Operations', 'Arjun Mehta');

INSERT INTO Employee (employee_name, dept_id, designation, email) VALUES
    ('Aditi Sharma', 1, 'Systems Engineer', 'aditi.sharma@company.com'),
    ('Rohan Verma', 1, 'Network Admin', 'rohan.verma@company.com'),
    ('Kavya Iyer', 2, 'HR Executive', 'kavya.iyer@company.com'),
    ('Vikram Rao', 3, 'Financial Analyst', 'vikram.rao@company.com');

INSERT INTO Asset (asset_name, category, model, serial_number, purchase_date, cost, warranty_expiry, status) VALUES
    ('Dell Latitude 5440', 'Laptop', 'Latitude 5440', 'SN-LAP-1001', '2024-01-15', 78000.00, '2026-08-10', 'AVAILABLE'),
    ('HP LaserJet Pro', 'Printer', 'LaserJet Pro M404', 'SN-PRN-2002', '2023-06-20', 22000.00, '2025-06-20', 'AVAILABLE'),
    ('Cisco Catalyst Switch', 'Networking', 'Catalyst 2960', 'SN-NET-3003', '2022-11-05', 55000.00, '2025-11-05', 'AVAILABLE'),
    ('Lenovo ThinkPad T14', 'Laptop', 'ThinkPad T14', 'SN-LAP-1004', '2024-03-01', 82000.00, '2027-03-01', 'AVAILABLE');

-- Password hashes use SHA2-256; plaintext passwords are shown in the docs for demo login.
INSERT INTO User_Login (username, password_hash, role, employee_id) VALUES
    ('admin',  SHA2('Admin@123', 256), 'ADMIN', NULL),
    ('rverma', SHA2('Rohan@123', 256), 'MANAGER', 2),
    ('kiyer',  SHA2('Kavya@123', 256), 'VIEWER', 3);
