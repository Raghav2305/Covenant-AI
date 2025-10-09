"""
Contract API endpoints
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models.contract import Contract
from app.models.obligation import Obligation
from app.services.contract_processor import ContractProcessor
from app.utils.ocr_processor import OCRProcessor
import structlog

logger = structlog.get_logger()
router = APIRouter()


@router.post("/upload")
async def upload_contract(
    file: UploadFile = File(...),
    title: str = Form(...),
    party_a: str = Form(...),
    party_b: str = Form(...),
    contract_type: Optional[str] = Form(None),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Upload and process a contract file"""
    
    logger.info("Contract upload request", 
               filename=file.filename, 
               title=title,
               party_a=party_a,
               party_b=party_b)
    
    try:
        # Save uploaded file to a temporary path
        import os
        upload_dir = "data/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Use a unique filename to avoid conflicts
        file_path = os.path.join(upload_dir, f"{uuid.uuid4()}_{file.filename}")
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Validate the saved file
        ocr_processor = OCRProcessor()
        if not ocr_processor.validate_file(file_path):
            raise HTTPException(status_code=400, detail="Invalid file type or size")
        
        # Prepare contract data
        contract_data = {
            "title": title,
            "party_a": party_a,
            "party_b": party_b,
            "contract_type": contract_type,
            "start_date": start_date,
            "end_date": end_date
        }
        
        # Process contract
        processor = ContractProcessor()
        contract = await processor.process_contract(file_path, contract_data, db)
        
        logger.info("Contract processed successfully", 
                   contract_id=str(contract.id),
                   obligation_count=len(contract.obligations))
        
        return {
            "contract_id": str(contract.id),
            "title": contract.title,
            "status": contract.processing_status,
            "obligation_count": len(contract.obligations),
            "obligations": [obligation.to_dict() for obligation in contract.obligations]
        }
        
    except Exception as e:
        logger.error("Contract upload failed", error=repr(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Contract processing failed: {repr(e)}")


@router.get("/")
async def list_contracts(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    contract_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all contracts with optional filtering"""
    
    query = db.query(Contract)
    
    if status:
        query = query.filter(Contract.status == status)
    
    if contract_type:
        query = query.filter(Contract.contract_type == contract_type)
    
    contracts = query.order_by(desc(Contract.created_at)).offset(skip).limit(limit).all()
    
    return {
        "contracts": [contract.to_dict() for contract in contracts],
        "total": len(contracts),
        "skip": skip,
        "limit": limit
    }


@router.get("/{contract_id}")
async def get_contract(
    contract_id: str,
    db: Session = Depends(get_db)
):
    """Get contract details with obligations"""
    
    try:
        contract_uuid = uuid.UUID(contract_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid contract ID")
    
    contract = db.query(Contract).filter(Contract.id == contract_uuid).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    return {
        "contract": contract.to_dict(),
        "obligations": [obligation.to_dict() for obligation in contract.obligations],
        "alerts": [alert.to_dict() for alert in contract.alerts]
    }


@router.post("/{contract_id}/reprocess")
async def reprocess_contract(
    contract_id: str,
    db: Session = Depends(get_db)
):
    """Reprocess an existing contract"""
    
    try:
        contract_uuid = uuid.UUID(contract_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid contract ID")
    
    contract = db.query(Contract).filter(Contract.id == contract_uuid).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    try:
        processor = ContractProcessor()
        updated_contract = await processor.reprocess_contract(contract_uuid, db)
        
        logger.info("Contract reprocessed successfully", 
                   contract_id=contract_id,
                   obligation_count=len(updated_contract.obligations))
        
        return {
            "contract_id": str(updated_contract.id),
            "status": updated_contract.processing_status,
            "obligation_count": len(updated_contract.obligations),
            "obligations": [obligation.to_dict() for obligation in updated_contract.obligations]
        }
        
    except Exception as e:
        logger.error("Contract reprocessing failed", 
                   contract_id=contract_id, 
                   error=str(e))
        raise HTTPException(status_code=500, detail=f"Contract reprocessing failed: {str(e)}")


@router.delete("/{contract_id}")
async def delete_contract(
    contract_id: str,
    db: Session = Depends(get_db)
):
    """Delete a contract and all associated data"""
    
    try:
        contract_uuid = uuid.UUID(contract_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid contract ID")
    
    contract = db.query(Contract).filter(Contract.id == contract_uuid).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    try:
        # Delete file if it exists
        if contract.file_path:
            import os
            if os.path.exists(contract.file_path):
                os.remove(contract.file_path)
        
        # Delete from database (cascade will handle obligations and alerts)
        db.delete(contract)
        db.commit()
        
        logger.info("Contract deleted successfully", contract_id=contract_id)
        
        return {"message": "Contract deleted successfully"}
        
    except Exception as e:
        logger.error("Contract deletion failed", 
                   contract_id=contract_id, 
                   error=str(e))
        raise HTTPException(status_code=500, detail=f"Contract deletion failed: {str(e)}")


@router.get("/{contract_id}/summary")
async def get_contract_summary(
    contract_id: str,
    db: Session = Depends(get_db)
):
    """Get contract summary with key metrics"""
    
    try:
        contract_uuid = uuid.UUID(contract_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid contract ID")
    
    contract = db.query(Contract).filter(Contract.id == contract_uuid).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    obligations = contract.obligations
    
    # Calculate summary metrics
    total_obligations = len(obligations)
    active_obligations = len([o for o in obligations if o.status == "active"])
    overdue_obligations = len([o for o in obligations if o.is_overdue()])
    
    risk_distribution = {}
    for obligation in obligations:
        risk_level = obligation.risk_level
        risk_distribution[risk_level] = risk_distribution.get(risk_level, 0) + 1
    
    total_penalty_exposure = sum(
        float(o.penalty_amount) for o in obligations 
        if o.penalty_amount and o.status == "active"
    )
    
    total_rebate_exposure = sum(
        float(o.rebate_amount) for o in obligations 
        if o.rebate_amount and o.status == "active"
    )
    
    return {
        "contract_id": str(contract.id),
        "title": contract.title,
        "parties": {
            "party_a": contract.party_a,
            "party_b": contract.party_b
        },
        "summary": {
            "total_obligations": total_obligations,
            "active_obligations": active_obligations,
            "overdue_obligations": overdue_obligations,
            "risk_distribution": risk_distribution,
            "total_penalty_exposure": total_penalty_exposure,
            "total_rebate_exposure": total_rebate_exposure
        },
        "status": contract.processing_status,
        "created_at": contract.created_at.isoformat() if contract.created_at else None
    }
