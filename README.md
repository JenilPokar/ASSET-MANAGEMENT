# Multi-Tenant Asset Management System 🏢💻

A comprehensive, multi-tenant web application designed to automate and streamline the management of valuable organizational assets. Built with a modern Python front-end and powered by a robust MySQL back-end, this system ensures data integrity, role-based access control, and efficient lifecycle tracking for multiple registered organizations.

## 🎓 Academic Details
* **Author:** Jenil Pokar
* **Roll Number:** 46
* **Program:** First-Year Artificial Intelligence and Data Science

---

## 🚀 Project Overview
Educational institutions, industries, and hospitals own valuable assets (computers, machinery, laboratory equipment) that are often mismanaged through manual tracking. This system automates asset registration, department-wise allocation, maintenance scheduling, depreciation tracking, and disposal. 

It features a strict **multi-tenant architecture**, allowing multiple companies to use the platform while keeping their data completely isolated.

### Key Features
* **Multi-Tenancy:** Separate workspaces for different registered institutes/companies.
* **Two-Tier Portal System:**
  * **Super Admin Dashboard:** Oversees all registered client companies, tracks platform usage, total asset counts, and manages subscription/payment records.
  * **Client Company Portal:** Role-based access (Admin, Store Manager, Department User) for organizations to manage their specific inventory.
* **Smart Data Entry:** Streamlined UI featuring dynamic real-time date/time synchronization and automated warranty tracking (dropdown selections for 1, 2, 3, or 4-year terms).
* **Database-Driven Logic:** Heavy lifting is handled via MySQL PL/SQL (Procedures, Functions, Triggers, and Cursors) to ensure maximum data integrity and performance.

---

## 🛠️ Tech Stack
* **Front-end:** Python (Flask / Streamlit)
* **Back-end/Database:** MySQL 8.0+ (SQL & PL/SQL)
* **Deployment:** Render (Deployment-ready via `requirements.txt`)

---

## 🌍 Sustainable Development Goals (SDGs) Mapping
This project actively aligns with global sustainability initiatives:
* **SDG 9 (Industry, Innovation, and Infrastructure):** Promotes efficient management of organizational infrastructure and improves operational efficiency through digital transformation.
* **SDG 12 (Responsible Consumption and Production):** Encourages optimal asset utilization, reduces unnecessary purchasing through strict tracking, and supports responsible equipment lifecycle management.
* **SDG 13 (Climate Action):** Extends asset lifespans through automated maintenance scheduling and reduces electronic waste via planned, responsible disposal tracking.

---

## ⚙️ Installation and Setup

### 1. Database Configuration (MySQL Workbench)
1. Open MySQL Workbench.
2. Execute the provided SQL DDL/DML script to generate the normalized schema, mock data, and constraints.
3. Execute the PL/SQL script to load all stored procedures, functions, triggers, and cursors.

### 2. Python Environment Setup
Ensure you have Python 3.8+ installed. 

Clone the repository and install the required dependencies:
```bash
git clone [https://github.com/yourusername/asset-management-system.git](https://github.com/yourusername/asset-management-system.git)
cd asset-management-system
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -r requirements.txt
FOR DB CONNECTOR
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=asset_management
