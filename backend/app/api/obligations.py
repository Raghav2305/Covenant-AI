"""
Obligation API endpoints
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.obligation import Obligation
from app.models.contract import Contract
from app.services.monitoring_engine import MonitoringEngine
import structlog

logger = structlog.get_logger()
router = APIRouter()


@router.get("/")
async def list_obligations(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    obligation_type: Optional[str] = None,
    party: Optional[str] = None,
    risk_level: Optional[str] = None,
    contract_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List obligations with optional filtering"""
    
    query = db.query(Obligation)
    
    if status:
        query = query.filter(Obligation.status == status)
    
    if obligation_type:
        query = query.filter(Obligation.obligation_type == obligation_type)
    
    if party:
        query = query.filter(Obligation.party.ilike(f"%{party}%"))
    
    if risk_level:
        query = query.filter(Obligation.risk_level == risk_level)
    
    if contract_id:
        try:
            contract_uuid = uuid.UUID(contract_id)
            query = query.filter(Obligation.contract_id == contract_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid contract ID")
    
    obligations = query.order_by(desc(Obligation.created_at)).offset(skip).limit(limit).all()
    
    return {
        "obligations": [obligation.to_dict() for obligation in obligations],
        "total": len(obligations),
        "skip": skip,
        "limit": limit,
        "filters": {
            "status": status,
            "obligation_type": obligation_type,
            "party": party,
            "risk_level": risk_level,
            "contract_id": contract_id
        }
    }


@router.get("/{obligation_id}")
async def get_obligation(
    obligation_id: str,
    db: Session = Depends(get_db)
):
    """Get obligation details"""
    
    try:
        obligation_uuid = uuid.UUID(obligation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid obligation ID")
    
    obligation = db.query(Obligation).filter(Obligation.id == obligation_uuid).first()
    if not obligation:
        raise HTTPException(status_code=404, detail="Obligation not found")
    
    return {
        "obligation": obligation.to_dict(),
        "contract": obligation.contract.to_dict() if obligation.contract else None,
        "alerts": [alert.to_dict() for alert in obligation.alerts]
    }


@router.post("/{obligation_id}/check-compliance")
async def check_obligation_compliance(
    obligation_id: str,
    db: Session = Depends(get_db)
):
    """Manually trigger compliance check for an obligation"""
    
    try:
        obligation_uuid = uuid.UUID(obligation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid obligation ID")
    
    obligation = db.query(Obligation).filter(Obligation.id == obligation_uuid).first()
    if not obligation:
        raise HTTPException(status_code=404, detail="Obligation not found")
    
    try:
        monitoring_engine = MonitoringEngine()
        await monitoring_engine.initialize()
        
        result = await monitoring_engine.check_obligation_compliance(obligation, db)
        
        logger.info("Manual compliance check completed", 
                   obligation_id=obligation_id,
                   compliance_status=result.get("compliance_status"))
        
        return result
        
    except Exception as e:
        logger.error("Compliance check failed", 
                   obligation_id=obligation_id, 
                   error=str(e))
        raise HTTPException(status_code=500, detail=f"Compliance check failed: {str(e)}")


@router.get("/due/upcoming")
async def get_upcoming_obligations(
    days_ahead: int = Query(30, description="Days ahead to check"),
    party: Optional[str] = Query(None, description="Filter by party"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    db: Session = Depends(get_db)
):
    """Get obligations due within specified days"""
    
    end_date = datetime.now() + timedelta(days=days_ahead)
    
    query = db.query(Obligation).filter(
        Obligation.status == "active",
        Obligation.deadline.isnot(None),
        Obligation.deadline >= datetime.now(),
        Obligation.deadline <= end_date
    )
    
    if party:
        query = query.filter(Obligation.party.ilike(f"%{party}%"))
    
    if risk_level:
        query = query.filter(Obligation.risk_level == risk_level)
    
    obligations = query.order_by(Obligation.deadline).all()
    
    # Group by days until deadline
    grouped_obligations = {}
    for obligation in obligations:
        days_until = obligation.days_until_deadline()
        if days_until is not None:
            if days_until <= 7:
                group = "within_week"
            elif days_until <= 30:
                group = "within_month"
            else:
                group = "beyond_month"
            
            if group not in grouped_obligations:
                grouped_obligations[group] = []
            grouped_obligations[group].append(obligation.to_dict())
    
    return {
        "days_ahead": days_ahead,
        "obligations": [obligation.to_dict() for obligation in obligations],
        "grouped_obligations": grouped_obligations,
        "count": len(obligations),
        "filters": {
            "party": party,
            "risk_level": risk_level
        }
    }


@router.get("/overdue")
async def get_overdue_obligations(
    party: Optional[str] = Query(None, description="Filter by party"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    db: Session = Depends(get_db)
):
    """Get all overdue obligations"""
    
    query = db.query(Obligation).filter(
        Obligation.status == "active",
        Obligation.deadline.isnot(None),
        Obligation.deadline < datetime.now()
    )
    
    if party:
        query = query.filter(Obligation.party.ilike(f"%{party}%"))
    
    if risk_level:
        query = query.filter(Obligation.risk_level == risk_level)
    
    obligations = query.order_by(Obligation.deadline).all()
    
    # Calculate overdue days
    overdue_data = []
    for obligation in obligations:
        overdue_days = (datetime.now() - obligation.deadline).days
        obligation_dict = obligation.to_dict()
        obligation_dict["overdue_days"] = overdue_days
        overdue_data.append(obligation_dict)
    
    return {
        "obligations": overdue_data,
        "count": len(obligations),
        "filters": {
            "party": party,
            "risk_level": risk_level
        }
    }


@router.get("/risk/high")
async def get_high_risk_obligations(
    db: Session = Depends(get_db)
):
    """Get all high-risk obligations"""
    
    obligations = db.query(Obligation).filter(
        Obligation.status == "active",
        Obligation.risk_level.in_(["high", "critical"])
    ).order_by(Obligation.deadline).all()
    
    # Calculate risk scores
    risk_data = []
    for obligation in obligations:
        obligation_dict = obligation.to_dict()
        obligation_dict["risk_score"] = obligation.get_risk_score()
        risk_data.append(obligation_dict)
    
    # Sort by risk score
    risk_data.sort(key=lambda x: x["risk_score"], reverse=True)
    
    return {
        "obligations": risk_data,
        "count": len(obligations),
        "risk_levels": ["high", "critical"]
    }


@router.get("/financial/exposure")
async def get_financial_exposure(
    party: Optional[str] = Query(None, description="Filter by party"),
    db: Session = Depends(get_db)
):
    """Get financial exposure from penalties and rebates"""
    
    query = db.query(Obligation).filter(
        Obligation.status == "active",
        or_(
            Obligation.penalty_amount.isnot(None),
            Obligation.rebate_amount.isnot(None)
        )
    )
    
    if party:
        query = query.filter(Obligation.party.ilike(f"%{party}%"))
    
    obligations = query.all()
    
    # Calculate exposures
    total_penalty_exposure = 0
    total_rebate_exposure = 0
    party_exposures = {}
    
    for obligation in obligations:
        party_name = obligation.party
        
        if party_name not in party_exposures:
            party_exposures[party_name] = {
                "penalty_exposure": 0,
                "rebate_exposure": 0,
                "obligation_count": 0
            }
        
        if obligation.penalty_amount:
            penalty_amount = float(obligation.penalty_amount)
            total_penalty_exposure += penalty_amount
            party_exposures[party_name]["penalty_exposure"] += penalty_amount
        
        if obligation.rebate_amount:
            rebate_amount = float(obligation.rebate_amount)
            total_rebate_exposure += rebate_amount
            party_exposures[party_name]["rebate_exposure"] += rebate_amount
        
        party_exposures[party_name]["obligation_count"] += 1
    
    return {
        "total_penalty_exposure": total_penalty_exposure,
        "total_rebate_exposure": total_rebate_exposure,
        "total_financial_exposure": total_penalty_exposure + total_rebate_exposure,
        "party_exposures": party_exposures,
        "obligation_count": len(obligations),
        "filter": {"party": party}
    }


@router.get("/stats/summary")
async def get_obligations_summary(
    db: Session = Depends(get_db)
):
    """Get summary statistics for obligations"""
    
    obligations = db.query(Obligation).all()
    
    # Status distribution
    status_distribution = {}
    for obligation in obligations:
        status = obligation.status
        status_distribution[status] = status_distribution.get(status, 0) + 1
    
    # Type distribution
    type_distribution = {}
    for obligation in obligations:
        obligation_type = obligation.obligation_type
        type_distribution[obligation_type] = type_distribution.get(obligation_type, 0) + 1
    
    # Risk distribution
    risk_distribution = {}
    for obligation in obligations:
        risk_level = obligation.risk_level
        risk_distribution[risk_level] = risk_distribution.get(risk_level, 0) + 1
    
    # Party distribution
    party_distribution = {}
    for obligation in obligations:
        party = obligation.party
        party_distribution[party] = party_distribution.get(party, 0) + 1
    
    # Compliance status
    compliance_distribution = {}
    for obligation in obligations:
        compliance_status = obligation.compliance_status
        compliance_distribution[compliance_status] = compliance_distribution.get(compliance_status, 0) + 1
    
    # Overdue count
    overdue_count = len([o for o in obligations if o.is_overdue()])
    
    return {
        "total_obligations": len(obligations),
        "overdue_obligations": overdue_count,
        "status_distribution": status_distribution,
        "type_distribution": type_distribution,
        "risk_distribution": risk_distribution,
        "party_distribution": party_distribution,
        "compliance_distribution": compliance_distribution
    }
