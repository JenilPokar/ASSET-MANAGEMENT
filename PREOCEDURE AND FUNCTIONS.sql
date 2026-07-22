-- ============================================================================
-- ASSET MANAGEMENT SYSTEM
-- PHASE 2: STORED PROCEDURES, FUNCTIONS, TRIGGERS, CURSOR  (MySQL 8.0+)
-- Run this AFTER 01_mysql_schema_and_data.sql in the same Workbench connection.
-- ============================================================================

USE asset_management;

-- MySQL needs a temporary delimiter so semicolons INSIDE routine bodies
-- don't end the statement early.

-- ============================================================================
-- PROCEDURE 1: sp_register_asset
-- ============================================================================
DELIMITER $$

CREATE PROCEDURE sp_register_asset (
    IN  p_asset_name      VARCHAR(120),
    IN  p_category        VARCHAR(60),
    IN  p_model           VARCHAR(100),
    IN  p_serial_number   VARCHAR(100),
    IN  p_purchase_date   DATE,
    IN  p_cost            DECIMAL(12,2),
    IN  p_warranty_expiry DATE,
    OUT p_new_asset_id    INT
)
proc_block: BEGIN
    DECLARE v_dup_count INT DEFAULT 0;

    SELECT COUNT(*) INTO v_dup_count FROM Asset WHERE serial_number = p_serial_number;

    IF v_dup_count > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Duplicate serial number for this asset.';
    END IF;

    INSERT INTO Asset (asset_name, category, model, serial_number,
                        purchase_date, cost, warranty_expiry, status)
    VALUES (p_asset_name, p_category, p_model, p_serial_number,
            p_purchase_date, p_cost, p_warranty_expiry, 'AVAILABLE');

    SET p_new_asset_id = LAST_INSERT_ID();
END $$

DELIMITER ;

-- ============================================================================
-- PROCEDURE 2: sp_allocate_asset
-- ============================================================================
DELIMITER $$

CREATE PROCEDURE sp_allocate_asset (
    IN  p_asset_id     INT,
    IN  p_employee_id  INT,
    IN  p_dept_id      INT,
    OUT p_alloc_id     INT
)
proc_block: BEGIN
    DECLARE v_status    VARCHAR(20);
    DECLARE v_emp_count INT DEFAULT 0;

    IF NOT EXISTS (SELECT 1 FROM Asset WHERE asset_id = p_asset_id) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid asset ID.';
    END IF;

    SELECT status INTO v_status FROM Asset WHERE asset_id = p_asset_id;

    SELECT COUNT(*) INTO v_emp_count FROM Employee WHERE employee_id = p_employee_id;
    IF v_emp_count = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid employee ID.';
    END IF;

    IF v_status = 'UNDER_MAINTENANCE' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Asset is under maintenance.';
    ELSEIF v_status = 'DISPOSED' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Asset has been disposed.';
    ELSEIF v_status = 'ALLOCATED' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Asset is already allocated.';
    END IF;

    -- The BEFORE/AFTER INSERT triggers on Asset_Allocation (below) also
    -- re-validate and flip Asset.status, so this stays correct even if a
    -- caller inserts directly instead of going through this procedure.
    INSERT INTO Asset_Allocation (asset_id, employee_id, dept_id, allocation_date, status)
    VALUES (p_asset_id, p_employee_id, p_dept_id, CURDATE(), 'ACTIVE');

    SET p_alloc_id = LAST_INSERT_ID();
END $$

DELIMITER ;

-- ============================================================================
-- PROCEDURE 3: sp_return_asset
-- ============================================================================
DELIMITER $$

CREATE PROCEDURE sp_return_asset (
    IN p_allocation_id INT
)
proc_block: BEGIN
    DECLARE v_asset_id INT;
    DECLARE v_status   VARCHAR(20);

    IF NOT EXISTS (SELECT 1 FROM Asset_Allocation WHERE allocation_id = p_allocation_id) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid allocation ID.';
    END IF;

    SELECT asset_id, status INTO v_asset_id, v_status
    FROM Asset_Allocation WHERE allocation_id = p_allocation_id;

    IF v_status = 'RETURNED' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'This allocation was already returned.';
    END IF;

    UPDATE Asset_Allocation
       SET return_date = CURDATE(), status = 'RETURNED'
     WHERE allocation_id = p_allocation_id;
END $$

DELIMITER ;

-- ============================================================================
-- PROCEDURE 4: sp_schedule_maintenance
-- ============================================================================
DELIMITER $$

CREATE PROCEDURE sp_schedule_maintenance (
    IN  p_asset_id          INT,
    IN  p_provider          VARCHAR(120),
    IN  p_cost              DECIMAL(10,2),
    IN  p_next_service_date DATE,
    OUT p_maintenance_id    INT
)
proc_block: BEGIN
    DECLARE v_status VARCHAR(20);

    IF NOT EXISTS (SELECT 1 FROM Asset WHERE asset_id = p_asset_id) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid asset ID.';
    END IF;

    SELECT status INTO v_status FROM Asset WHERE asset_id = p_asset_id;

    IF v_status = 'DISPOSED' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Cannot schedule maintenance: asset is disposed.';
    END IF;

    IF p_next_service_date IS NOT NULL AND p_next_service_date < CURDATE() THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Next service date cannot be in the past.';
    END IF;

    INSERT INTO Asset_Maintenance (asset_id, maintenance_date, provider, cost, next_service_date, status)
    VALUES (p_asset_id, CURDATE(), p_provider, p_cost, p_next_service_date, 'IN_PROGRESS');

    SET p_maintenance_id = LAST_INSERT_ID();
END $$

DELIMITER ;

-- ============================================================================
-- PROCEDURE 5: sp_dispose_asset
-- ============================================================================
DELIMITER $$

CREATE PROCEDURE sp_dispose_asset (
    IN  p_asset_id     INT,
    IN  p_method       VARCHAR(60),
    IN  p_scrap_value  DECIMAL(10,2),
    OUT p_disposal_id  INT
)
proc_block: BEGIN
    DECLARE v_status VARCHAR(20);

    IF NOT EXISTS (SELECT 1 FROM Asset WHERE asset_id = p_asset_id) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid asset ID.';
    END IF;

    SELECT status INTO v_status FROM Asset WHERE asset_id = p_asset_id;

    IF v_status = 'ALLOCATED' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Cannot dispose: asset is currently allocated.';
    ELSEIF v_status = 'DISPOSED' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Asset is already disposed.';
    END IF;

    INSERT INTO Asset_Disposal (asset_id, disposal_date, method, scrap_value)
    VALUES (p_asset_id, CURDATE(), p_method, p_scrap_value);

    SET p_disposal_id = LAST_INSERT_ID();
END $$

DELIMITER ;

-- ============================================================================
-- PROCEDURE 6: sp_update_asset_details
-- ============================================================================
DELIMITER $$

CREATE PROCEDURE sp_update_asset_details (
    IN p_asset_id          INT,
    IN p_asset_name        VARCHAR(120),
    IN p_category          VARCHAR(60),
    IN p_model             VARCHAR(100),
    IN p_warranty_expiry   DATE
)
proc_block: BEGIN
    IF NOT EXISTS (SELECT 1 FROM Asset WHERE asset_id = p_asset_id) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid asset ID.';
    END IF;

    UPDATE Asset
       SET asset_name      = p_asset_name,
           category        = p_category,
           model           = p_model,
           warranty_expiry = p_warranty_expiry
     WHERE asset_id = p_asset_id;
END $$

DELIMITER ;

-- ============================================================================
-- FUNCTION 1: fn_calculate_depreciation
-- Straight-line depreciation, floored at a 10% residual value.
-- ============================================================================
DELIMITER $$

CREATE FUNCTION fn_calculate_depreciation (
    p_asset_id    INT,
    p_useful_life INT   -- years; pass 5 for the standard assumption
)
RETURNS DECIMAL(12,2)
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE v_cost          DECIMAL(12,2);
    DECLARE v_purchase_date DATE;
    DECLARE v_years_used    DECIMAL(10,4);
    DECLARE v_residual      DECIMAL(12,2);
    DECLARE v_annual_dep    DECIMAL(12,2);
    DECLARE v_current_value DECIMAL(12,2);

    SELECT cost, purchase_date INTO v_cost, v_purchase_date
    FROM Asset WHERE asset_id = p_asset_id;

    SET v_years_used    = DATEDIFF(CURDATE(), v_purchase_date) / 365.25;
    SET v_residual       = v_cost * 0.10;
    SET v_annual_dep     = (v_cost - v_residual) / p_useful_life;
    SET v_current_value  = v_cost - (v_annual_dep * v_years_used);

    IF v_current_value < v_residual THEN
        SET v_current_value = v_residual;
    END IF;

    RETURN ROUND(v_current_value, 2);
END $$

DELIMITER ;

-- ============================================================================
-- FUNCTION 2: fn_check_availability
-- ============================================================================
DELIMITER $$

CREATE FUNCTION fn_check_availability (p_asset_id INT)
RETURNS CHAR(1)
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE v_status VARCHAR(20);

    SELECT status INTO v_status FROM Asset WHERE asset_id = p_asset_id;

    IF v_status = 'AVAILABLE' THEN
        RETURN 'Y';
    ELSE
        RETURN 'N';
    END IF;
END $$

DELIMITER ;

-- ============================================================================
-- FUNCTION 3: fn_total_maintenance_cost
-- ============================================================================
DELIMITER $$

CREATE FUNCTION fn_total_maintenance_cost (p_asset_id INT)
RETURNS DECIMAL(12,2)
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE v_total DECIMAL(12,2);

    SELECT IFNULL(SUM(cost), 0) INTO v_total
    FROM Asset_Maintenance WHERE asset_id = p_asset_id;

    RETURN v_total;
END $$

DELIMITER ;

-- ============================================================================
-- FUNCTION 4: fn_count_assets_by_dept
-- ============================================================================
DELIMITER $$

CREATE FUNCTION fn_count_assets_by_dept (p_dept_id INT)
RETURNS INT
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE v_count INT;

    SELECT COUNT(*) INTO v_count
    FROM Asset_Allocation
    WHERE dept_id = p_dept_id AND status = 'ACTIVE';

    RETURN v_count;
END $$

DELIMITER ;

-- ============================================================================
-- TRIGGERS
-- MySQL requires one trigger per (table, timing, event) combination, so
-- INSERT and UPDATE logic that Oracle would combine into one trigger is
-- split into separate CREATE TRIGGER statements below.
-- ============================================================================

-- 1) Guard against invalid allocations, then flip Asset -> ALLOCATED
DELIMITER $$

CREATE TRIGGER trg_alloc_before_insert
BEFORE INSERT ON Asset_Allocation
FOR EACH ROW
BEGIN
    DECLARE v_status VARCHAR(20);

    SELECT status INTO v_status FROM Asset WHERE asset_id = NEW.asset_id;

    IF v_status = 'ALLOCATED' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Asset already allocated.';
    ELSEIF v_status = 'UNDER_MAINTENANCE' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Asset is under maintenance.';
    ELSEIF v_status = 'DISPOSED' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Asset has been disposed.';
    END IF;
END $$

CREATE TRIGGER trg_alloc_after_insert
AFTER INSERT ON Asset_Allocation
FOR EACH ROW
BEGIN
    UPDATE Asset SET status = 'ALLOCATED' WHERE asset_id = NEW.asset_id;
END $$

CREATE TRIGGER trg_alloc_after_update
AFTER UPDATE ON Asset_Allocation
FOR EACH ROW
BEGIN
    IF NEW.status = 'RETURNED' AND OLD.status = 'ACTIVE' THEN
        UPDATE Asset SET status = 'AVAILABLE' WHERE asset_id = NEW.asset_id;
    END IF;
END $$

DELIMITER ;

-- 2) Maintenance lifecycle: UNDER_MAINTENANCE on log, AVAILABLE on completion
DELIMITER $$

CREATE TRIGGER trg_maint_after_insert
AFTER INSERT ON Asset_Maintenance
FOR EACH ROW
BEGIN
    UPDATE Asset SET status = 'UNDER_MAINTENANCE' WHERE asset_id = NEW.asset_id;
END $$

CREATE TRIGGER trg_maint_after_update
AFTER UPDATE ON Asset_Maintenance
FOR EACH ROW
BEGIN
    IF NEW.status = 'COMPLETED' AND OLD.status = 'IN_PROGRESS' THEN
        UPDATE Asset SET status = 'AVAILABLE' WHERE asset_id = NEW.asset_id;
    END IF;
END $$

DELIMITER ;

-- 3) Disposal: block if allocated, then mark DISPOSED
DELIMITER $$

CREATE TRIGGER trg_disposal_before_insert
BEFORE INSERT ON Asset_Disposal
FOR EACH ROW
BEGIN
    DECLARE v_status VARCHAR(20);

    SELECT status INTO v_status FROM Asset WHERE asset_id = NEW.asset_id;

    IF v_status = 'ALLOCATED' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Cannot dispose an allocated asset.';
    END IF;
END $$

CREATE TRIGGER trg_disposal_after_insert
AFTER INSERT ON Asset_Disposal
FOR EACH ROW
BEGIN
    UPDATE Asset SET status = 'DISPOSED' WHERE asset_id = NEW.asset_id;
END $$

DELIMITER ;

-- 4) Warranty expiry alert: log when warranty_expiry falls within 30 days
DELIMITER $$

CREATE TRIGGER trg_warranty_alert_insert
AFTER INSERT ON Asset
FOR EACH ROW
BEGIN
    IF NEW.warranty_expiry IS NOT NULL
       AND DATEDIFF(NEW.warranty_expiry, CURDATE()) BETWEEN 0 AND 30 THEN
        INSERT INTO Warranty_Alert_Log (asset_id, alert_message)
        VALUES (NEW.asset_id,
                CONCAT('Warranty for asset ID ', NEW.asset_id, ' expires in ',
                       DATEDIFF(NEW.warranty_expiry, CURDATE()), ' day(s) on ',
                       DATE_FORMAT(NEW.warranty_expiry, '%d-%b-%Y'), '.'));
    END IF;
END $$

CREATE TRIGGER trg_warranty_alert_update
AFTER UPDATE ON Asset
FOR EACH ROW
BEGIN
    IF NEW.warranty_expiry IS NOT NULL
       AND (OLD.warranty_expiry IS NULL OR NEW.warranty_expiry <> OLD.warranty_expiry)
       AND DATEDIFF(NEW.warranty_expiry, CURDATE()) BETWEEN 0 AND 30 THEN
        INSERT INTO Warranty_Alert_Log (asset_id, alert_message)
        VALUES (NEW.asset_id,
                CONCAT('Warranty for asset ID ', NEW.asset_id, ' expires in ',
                       DATEDIFF(NEW.warranty_expiry, CURDATE()), ' day(s) on ',
                       DATE_FORMAT(NEW.warranty_expiry, '%d-%b-%Y'), '.'));
    END IF;
END $$

DELIMITER ;

-- ============================================================================
-- CURSOR BLOCK: sp_list_allocated_assets
-- Fetches every actively-allocated asset alongside employee, department,
-- latest maintenance status, computed depreciation, and warranty expiry.
-- MySQL stored procedures can't "print" like PL/SQL's DBMS_OUTPUT, so this
-- procedure loops through a cursor, builds a temporary results table row by
-- row (demonstrating explicit cursor use), then returns it with a final
-- SELECT -- which is what the Python/Tkinter front-end calls and displays.
-- ============================================================================
DELIMITER $$

CREATE PROCEDURE sp_list_allocated_assets()
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE v_asset_id INT;
    DECLARE v_asset_name VARCHAR(120);
    DECLARE v_employee_name VARCHAR(100);
    DECLARE v_dept_name VARCHAR(100);
    DECLARE v_allocation_date DATE;
    DECLARE v_warranty_expiry DATE;
    DECLARE v_maint_status VARCHAR(20);
    DECLARE v_dep_value DECIMAL(12,2);

    DECLARE cur_allocated CURSOR FOR
        SELECT a.asset_id, a.asset_name, e.employee_name, d.dept_name,
               al.allocation_date, a.warranty_expiry
        FROM Asset_Allocation al
        JOIN Asset a      ON a.asset_id = al.asset_id
        JOIN Employee e   ON e.employee_id = al.employee_id
        JOIN Department d ON d.dept_id = al.dept_id
        WHERE al.status = 'ACTIVE'
        ORDER BY al.allocation_date DESC;

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;

    DROP TEMPORARY TABLE IF EXISTS tmp_allocated_report;
    CREATE TEMPORARY TABLE tmp_allocated_report (
        asset_id          INT,
        asset_name        VARCHAR(120),
        employee_name     VARCHAR(100),
        dept_name         VARCHAR(100),
        allocation_date   DATE,
        maintenance_status VARCHAR(20),
        depreciation_value DECIMAL(12,2),
        warranty_expiry   DATE
    );

    OPEN cur_allocated;

    read_loop: LOOP
        FETCH cur_allocated INTO v_asset_id, v_asset_name, v_employee_name,
                                  v_dept_name, v_allocation_date, v_warranty_expiry;
        IF done THEN
            LEAVE read_loop;
        END IF;

        -- NOTE: a plain "SELECT ... INTO" here would share the same NOT FOUND
        -- handler as the cursor FETCH above and could end the loop early if an
        -- asset has no maintenance rows. A scalar subquery sidesteps that: it
        -- simply evaluates to NULL when there are no matching rows.
        SET v_maint_status = (
            SELECT status FROM Asset_Maintenance
            WHERE asset_id = v_asset_id
            ORDER BY maintenance_date DESC
            LIMIT 1
        );

        IF v_maint_status IS NULL THEN
            SET v_maint_status = 'NONE';
        END IF;

        SET v_dep_value = fn_calculate_depreciation(v_asset_id, 5);

        INSERT INTO tmp_allocated_report VALUES (
            v_asset_id, v_asset_name, v_employee_name, v_dept_name,
            v_allocation_date, v_maint_status, v_dep_value, v_warranty_expiry
        );

        -- reset for next loop iteration so a missing maintenance row on the
        -- next asset doesn't accidentally reuse this iteration's value
        SET v_maint_status = NULL;
    END LOOP;

    CLOSE cur_allocated;

    SELECT * FROM tmp_allocated_report;
    DROP TEMPORARY TABLE IF EXISTS tmp_allocated_report;
END $$

DELIMITER ;
