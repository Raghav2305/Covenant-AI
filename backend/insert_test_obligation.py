import os
import sys
import uuid
from datetime import datetime, timedelta

# Add the project root to the sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base # Import Base from your project
from app.models.contract import Contract
from app.models.obligation import Obligation

# Assume default local PostgreSQL credentials for testing
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/contract_ai")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def insert_data():
    db = next(get_db())
    try:
        # Define the same TEST_CONTRACT_ID as in setup_dummy_db.py
        TEST_CONTRACT_ID = uuid.UUID("3fa85f64-5717-4562-b3fc-2c963f66afa6")

        # 1. Create a dummy Contract
        contract = db.query(Contract).filter(Contract.id == TEST_CONTRACT_ID).first()
        if not contract:
            print("Creating a new test contract...")
            contract = Contract(
                id=TEST_CONTRACT_ID,
                title="Test Contract for Discount Cap Monitoring (Client Alpha)",
                party_a="Client Alpha",
                party_b="Covenant AI",
                contract_type="Service Agreement",
                start_date=datetime.now() - timedelta(days=365),
                end_date=datetime.now() + timedelta(days=365),
                status="active",
                file_path="/data/sample_contracts/test_contract_client_alpha.pdf"
            )
            db.add(contract)
            db.commit()
            db.refresh(contract)
            print(f"Created Contract: {contract.id}")
        else:
            print(f"Using existing Contract: {contract.id}")

        # 2. Create a dummy Obligation for discount cap monitoring
        # This obligation will be linked directly via contract_id
        obligation_id = uuid.uuid4()
        obligation_description = "Adhere to a maximum 10% discount cap for Client Alpha"
        obligation = db.query(Obligation).filter(
            Obligation.description == obligation_description,
            Obligation.contract_id == TEST_CONTRACT_ID
        ).first()

        if not obligation:
            print("Creating a new test obligation...")
            obligation = Obligation(
                id=obligation_id,
                contract_id=TEST_CONTRACT_ID, # Direct link to the contract
                obligation_id_external="OBL-DISCOUNT-CAP-001", # External ID if applicable
                party="Client Alpha", # Simpler party name now that link is via contract_id
                obligation_type="Discount Cap Compliance",
                description=obligation_description,
                deadline=datetime.now() + timedelta(days=30), # A future deadline
                frequency="continuous",
                condition="Maximum discount percentage must not exceed 10%",
                penalty_amount=10000.00,
                penalty_currency="USD",
                status="active",
                risk_level="high",
                compliance_status="unknown" # Will be updated by MonitoringEngine
            )
            db.add(obligation)
            db.commit()
            db.refresh(obligation)
            print(f"Created Obligation: {obligation.id}")
        else:
            print(f"Using existing Obligation: {obligation.id}")
            # Ensure it's active and compliance_status is unknown for re-testing
            obligation.status = "active"
            obligation.compliance_status = "unknown"
            db.commit()


        print("\nTest data insertion complete.")
        print("Now you can run the monitoring check via API: POST /api/v1/monitoring/check-all")

    except Exception as e:
        db.rollback()
        print(f"An error occurred: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    insert_data()
