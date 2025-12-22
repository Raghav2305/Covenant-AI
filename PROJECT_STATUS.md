## Alerts and Notifications Feature

### What the Alerts & Notifications System Does

The goal is to automatically warn users about important events in the contract lifecycle so they don't have to track them manually. Based on the documentation, the system is designed to generate alerts for three primary reasons:

1.  **Upcoming Deadlines:** The system should proactively create alerts for obligations that are due soon (e.g., in 7 days, 30 days).
2.  **SLA Breaches:** When the `MonitoringEngine` detects that a live operational metric has violated a contractual rule (e.g., a discount cap is exceeded), it should generate a high-priority alert.
3.  **Financial Triggers:** When a condition for a financial event is met (e.g., a sales volume is reached that triggers a rebate), an alert should be created to notify the finance team.

When one of these events occurs, the backend is designed to create a record in the `alerts` database table with a severity level (low, medium, high, critical), a descriptive message, and a link back to the specific contract and obligation.

### How Users Interact with It

The `AlertsPage.tsx` is intended to be the central hub for managing these alerts. On this page, users should be able to:
*   View a list of all active alerts.
*   Filter and sort them by severity, date, or status.
*   Click on an alert to see its details and navigate to the relevant contract.
*   **Acknowledge** an alert to show they are aware of it.
*   **Resolve** an alert once the underlying issue has been handled.

---

### The Implementation Plan

The backend API already has the necessary endpoints for fetching and managing alerts. The missing piece is the frontend UI. I will now build out the `AlertsPage`.

1.  **Fetch and Display Alerts:** I will implement the logic to call the `/api/v1/monitoring/alerts` endpoint and display the alerts in a professional `DataGrid`, similar to the other pages we've built.
2.  **Style the Grid:** The grid will use color-coded chips for severity and status, making it easy to scan for critical issues.
3.  **Implement Actions:** I will add "Acknowledge" and "Resolve" buttons to each row. These buttons will call the corresponding backend APIs to update the alert's status, and the UI will update in real-time.

This will create a fully functional and professional alert management dashboard.







---
### Detailed MCP and Alerting Workflow

Here is a detailed breakdown of how MCP is used for the Alerts and Notifications functionality.

#### 1. The Goal
The system needs to automatically detect when a real-world event violates a rule in a contract and create an alert. For example, if a contract says "discounts must not exceed 10%," the system should create an alert if a transaction with a 12% discount is found.

#### 2. The Components
*   **`Obligation` (in PostgreSQL):** This is the rule extracted from the contract (e.g., "Discount cap of 10% for Client A").
*   **`mcp-database-server` (`database_server.py`):** This is a dedicated microservice that acts as a secure gateway to the live operational database (where transactions, customer data, etc., are stored). It exposes simple, high-level queries like `get_discount_data` or `get_customer_volume`. It **does not** have direct access to the contract obligations.
*   **`MCPClientManager` (`mcp_client.py`):** This is a client library within the main backend application. It knows how to connect to and query the `mcp-database-server`.
*   **`MonitoringEngine` (`monitoring_engine.py`):** This is the core logic that orchestrates the process. It runs periodically (e.g., every hour) to check for violations.

#### 3. The Workflow for a Single Check
a.  The `MonitoringEngine` wakes up and fetches an active `Obligation` from its own database (e.g., the "Discount cap of 10%" rule).
b.  It determines what kind of live data it needs. For a discount rule, it needs recent discount data for the relevant customer.
c.  It uses the `MCPClientManager` to call the `get_discount_data` function on the `mcp-database-server`.
d.  The `mcp-database-server` receives the request, queries the **live operational database** for the customer's recent discounts, and returns the data (e.g., `{"max_discount_percentage": 12.0, "cap_breach": true}`).
e.  The `MonitoringEngine` receives this live data from the MCP server.
f.  It then compares the contractual rule ("10% cap") with the live data ("12% found"). The `DEVELOPMENT_PLAN.md` suggests using an LLM to do this comparison (`analyze_obligation_compliance`), which makes the logic flexible.
g.  If the comparison shows a violation, the `MonitoringEngine` creates a new `Alert` record in the PostgreSQL database with a "high" severity, a descriptive message, and the evidence (the live data it received).

#### 4. Summary of Component Responsibilities

| Component | Responsibility |
| :--- | :--- |
| **Contract `Obligation`** | Defines the **rule** (e.g., "Discount cap is 10%"). |
| **`mcp-database-server`** | Provides **live data** from operational systems (e.g., "The latest discount was 12%"). |
| **`MonitoringEngine`** | **Compares** the rule to the live data and **creates an alert** if there is a mismatch. |
| **`AlertsPage.tsx` (Frontend)** | **Displays** the created alerts to the user. |

#### 5. Next Steps for Implementation
Based on the analysis, the backend is well-equipped for alert generation. The `MonitoringEngine` has the core logic, and the `mcp-database-server` provides mock data for testing.

The next steps are to test the backend and then build the frontend:

1.  **Test Backend Alert Generation:** An API endpoint, `POST /api/v1/monitoring/check-all`, already exists to trigger the `MonitoringEngine`'s `check_all_obligations` method. We will use this endpoint to run a compliance check, which should generate alerts based on the mock data from the MCP server.
2.  **Implement the `AlertsPage.tsx`:** Once we confirm that alerts are being generated correctly in the backend, we will proceed with building the frontend UI. This involves fetching the alerts using the `/api/v1/monitoring/alerts` endpoint and displaying them in a professional `DataGrid` with features for filtering, acknowledging, and resolving them.





---
### Requirement for a Dummy 'Live' Database

For realistic end-to-end testing of the alerting functionality, we need a source of "live" operational data for the `MonitoringEngine` to check against.

#### Current Situation: Two Databases
1.  **Application Database (PostgreSQL):** This database is part of our Docker setup and correctly stores contracts, obligations, and alerts.
2.  **"Live" Operational Database (Missing):** This database, which should contain real-world data like customer transactions and discounts, does not yet exist.

#### The Problem with Mock Data
Currently, the `mcp-database-server` does not connect to any database. Instead, it fakes its responses by returning hardcoded, static mock data. For example, the `get_discount_data` function in `backend/app/mcp/database_server.py` is hardcoded to always return `"cap_breach": False`. This makes it impossible to test scenarios where a contract rule is actually violated, as the mock data will never trigger a real alert.

#### Proposed Solution: Create a Dummy "Live" Database
To enable proper testing, we will create a dummy "live" database.

1.  **Create a Dummy Database:** We will create a simple, file-based **SQLite** database (e.g., `live_data.db`) to act as our "live" operational database. This is lightweight and ideal for development.
2.  **Add Dummy Data:** I will add a `transactions` table to this SQLite database and populate it with sample transactions. Crucially, this will include data designed to violate a contract rule (e.g., a transaction with a 15% discount to test a 10% cap).
3.  **Update the MCP Server:** I will modify the `mcp-database-server` to connect to this new SQLite database and execute real queries against it, rather than returning hardcoded mock data.

This will provide a realistic end-to-end testing environment, allowing the `MonitoringEngine` to query the MCP server, receive real data from the dummy database, and generate alerts as designed.
