import os
import sqlite3
import uuid

# Define the path for the SQLite database
# This path goes up three directories from `mcp/` to the project root, then into `data/`
DB_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "live_data.db")

# Define a consistent, known UUID for our test contract
# This allows other scripts to reference the same contract
TEST_CONTRACT_ID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"

def setup_database():
    """Create and populate the dummy SQLite database."""
    # Ensure the data directory exists
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)

    # Connect to the database (this will create the file if it doesn't exist)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Drop the table if it already exists to ensure a clean setup
    cursor.execute("DROP TABLE IF EXISTS transactions")

    # Create the transactions table with the new contract_id column
    print("Creating 'transactions' table with 'contract_id'...")
    cursor.execute("""
    CREATE TABLE transactions (
        transaction_id TEXT PRIMARY KEY,
        contract_id TEXT NOT NULL,
        customer_id TEXT NOT NULL,
        amount REAL NOT NULL,
        transaction_date TEXT NOT NULL,
        transaction_type TEXT,
        discount_percentage REAL DEFAULT 0,
        discount_amount REAL DEFAULT 0
    )
    """)

    # Insert some sample data, now including the contract_id
    print(f"Inserting transactions linked to TEST_CONTRACT_ID: {TEST_CONTRACT_ID}...")
    transactions = [
        # Normal transactions for CUST-001, linked to our test contract
        ('TXN-001', TEST_CONTRACT_ID, 'CUST-001', 1500.00, '2024-09-27', 'payment', 5.0, 75.0),
        ('TXN-002', TEST_CONTRACT_ID, 'CUST-001', 750.00, '2024-09-26', 'refund', 0.0, 0.0),
        
        # A transaction that BREACHES a 10% discount cap for CUST-001
        ('TXN-003', TEST_CONTRACT_ID, 'CUST-001', 2000.00, '2024-09-25', 'payment', 15.0, 300.0),
        
        # Transactions for a different customer, linked to a different contract
        ('TXN-004', 'ce59e68e-5323-4138-9854-15c7112a5139', 'CUST-002', 500.00, '2024-09-27', 'payment', 2.0, 10.0),
        ('TXN-005', 'ce59e68e-5323-4138-9854-15c7112a5139', 'CUST-002', 1000.00, '2024-09-28', 'payment', 0.0, 0.0),
        
        # Transaction to test volume rebates for a different contract
        ('TXN-006', 'd6b7a5a8-4c3e-4b1a-8f9a-2b3c4d5e6f7g', 'CUST-003', 1200000.00, '2024-09-29', 'payment', 1.0, 12000.0)
    ]

    cursor.executemany("INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?, ?)", transactions)

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

    print(f"Database '{DB_FILE}' created and populated successfully.")
    print("The 'transactions' table now includes a 'contract_id' column.")

if __name__ == "__main__":
    setup_database()