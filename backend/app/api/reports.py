"""
Reports API endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from datetime import datetime, timedelta
import json

from app.core.simple_database import get_db
from app.models.contract import Contract
from app.models.obligation import Obligation
from app.models.alert import Alert
import structlog

logger = structlog.get_logger()
router = APIRouter()


@router.get("/quarterly-review")
async def generate_quarterly_review(
    quarter: Optional[str] = Query(None, description="Quarter: Q1, Q2, Q3, Q4"),
    year: Optional[int] = Query(None, description="Year"),
    db: Session = Depends(get_db)
):
    """Generate quarterly review report"""
    
    # Determine quarter dates
    now = datetime.now()
    if not year:
        year = now.year
    if not quarter:
        quarter = f"Q{(now.month - 1) // 3 + 1}"
    
    quarter_dates = _get_quarter_dates(year, quarter)
    
    # Get obligations for the quarter
    obligations = db.query(Obligation).filter(
        Obligation.status == "active",
        Obligation.deadline >= quarter_dates["start"],
        Obligation.deadline <= quarter_dates["end"]
    ).all()
    
    # Get alerts for the quarter
    alerts = db.query(Alert).filter(
        Alert.created_at >= quarter_dates["start"],
        Alert.created_at <= quarter_dates["end"]
    ).all()
    
    # Calculate metrics
    total_obligations = len(obligations)
    completed_obligations = len([o for o in obligations if o.status == "completed"])
    overdue_obligations = len([o for o in obligations if o.is_overdue()])
    
    # Risk analysis
    risk_distribution = {}
    for obligation in obligations:
        risk_level = obligation.risk_level
        risk_distribution[risk_level] = risk_distribution.get(risk_level, 0) + 1
    
    # Financial exposure
    total_penalty_exposure = sum(
        float(o.penalty_amount) for o in obligations 
        if o.penalty_amount and o.status == "active"
    )
    total_rebate_exposure = sum(
        float(o.rebate_amount) for o in obligations 
        if o.rebate_amount and o.status == "active"
    )
    
    # Alert analysis
    alert_types = {}
    alert_severities = {}
    for alert in alerts:
        alert_type = alert.alert_type
        alert_types[alert_type] = alert_types.get(alert_type, 0) + 1
        
        severity = alert.severity
        alert_severities[severity] = alert_severities.get(severity, 0) + 1
    
    # Compliance rate
    compliant_obligations = len([o for o in obligations if o.compliance_status == "compliant"])
    compliance_rate = (compliant_obligations / total_obligations * 100) if total_obligations > 0 else 0
    
    return {
        "report_type": "quarterly_review",
        "period": {
            "quarter": quarter,
            "year": year,
            "start_date": quarter_dates["start"].isoformat(),
            "end_date": quarter_dates["end"].isoformat()
        },
        "obligations": {
            "total": total_obligations,
            "completed": completed_obligations,
            "overdue": overdue_obligations,
            "compliance_rate": round(compliance_rate, 2)
        },
        "risk_analysis": {
            "risk_distribution": risk_distribution,
            "high_risk_count": risk_distribution.get("high", 0) + risk_distribution.get("critical", 0)
        },
        "financial_exposure": {
            "total_penalty_exposure": total_penalty_exposure,
            "total_rebate_exposure": total_rebate_exposure,
            "total_exposure": total_penalty_exposure + total_rebate_exposure
        },
        "alerts": {
            "total": len(alerts),
            "by_type": alert_types,
            "by_severity": alert_severities
        },
        "recommendations": _generate_quarterly_recommendations(
            obligations, alerts, compliance_rate
        )
    }


@router.get("/contracts-at-risk")
async def get_contracts_at_risk_report(
    risk_threshold: Optional[str] = Query("high", description="Risk threshold: low, medium, high, critical"),
    db: Session = Depends(get_db)
):
    """Generate contracts at risk report"""
    
    # Get contracts with high-risk obligations
    contracts = db.query(Contract).filter(Contract.status == "active").all()
    
    at_risk_contracts = []
    for contract in contracts:
        high_risk_obligations = [
            o for o in contract.obligations 
            if o.status == "active" and o.risk_level in ["high", "critical"]
        ]
        
        if high_risk_obligations:
            # Calculate risk score for contract
            total_risk_score = sum(o.get_risk_score() for o in high_risk_obligations)
            avg_risk_score = total_risk_score / len(high_risk_obligations)
            
            # Get recent alerts
            recent_alerts = db.query(Alert).filter(
                Alert.contract_id == contract.id,
                Alert.created_at >= datetime.now() - timedelta(days=30)
            ).all()
            
            at_risk_contracts.append({
                "contract": contract.to_dict(),
                "high_risk_obligations": [o.to_dict() for o in high_risk_obligations],
                "risk_score": round(avg_risk_score, 2),
                "recent_alerts": len(recent_alerts),
                "overdue_obligations": len([o for o in contract.obligations if o.is_overdue()])
            })
    
    # Sort by risk score
    at_risk_contracts.sort(key=lambda x: x["risk_score"], reverse=True)
    
    return {
        "report_type": "contracts_at_risk",
        "risk_threshold": risk_threshold,
        "contracts": at_risk_contracts,
        "total_contracts_at_risk": len(at_risk_contracts),
        "generated_at": datetime.now().isoformat()
    }


@router.get("/obligations-due")
async def get_obligations_due_report(
    timeframe: str = Query("month", description="Timeframe: week, month, quarter"),
    party: Optional[str] = Query(None, description="Filter by party"),
    db: Session = Depends(get_db)
):
    """Generate obligations due report"""
    
    # Calculate date range
    now = datetime.now()
    if timeframe == "week":
        end_date = now + timedelta(days=7)
    elif timeframe == "month":
        end_date = now + timedelta(days=30)
    elif timeframe == "quarter":
        end_date = now + timedelta(days=90)
    else:
        end_date = now + timedelta(days=30)
    
    # Get obligations due in timeframe
    query = db.query(Obligation).filter(
        Obligation.status == "active",
        Obligation.deadline.isnot(None),
        Obligation.deadline >= now,
        Obligation.deadline <= end_date
    )
    
    if party:
        query = query.filter(Obligation.party.ilike(f"%{party}%"))
    
    obligations = query.order_by(Obligation.deadline).all()
    
    # Group by deadline proximity
    urgent_obligations = []  # Due within 7 days
    upcoming_obligations = []  # Due within 30 days
    future_obligations = []  # Due later
    
    for obligation in obligations:
        days_until = obligation.days_until_deadline()
        obligation_dict = obligation.to_dict()
        obligation_dict["days_until_deadline"] = days_until
        
        if days_until <= 7:
            urgent_obligations.append(obligation_dict)
        elif days_until <= 30:
            upcoming_obligations.append(obligation_dict)
        else:
            future_obligations.append(obligation_dict)
    
    # Calculate financial exposure
    total_penalty_exposure = sum(
        float(o.penalty_amount) for o in obligations 
        if o.penalty_amount
    )
    
    return {
        "report_type": "obligations_due",
        "timeframe": timeframe,
        "period": {
            "start_date": now.isoformat(),
            "end_date": end_date.isoformat()
        },
        "obligations": {
            "total": len(obligations),
            "urgent": len(urgent_obligations),
            "upcoming": len(upcoming_obligations),
            "future": len(future_obligations)
        },
        "obligations_by_urgency": {
            "urgent": urgent_obligations,
            "upcoming": upcoming_obligations,
            "future": future_obligations
        },
        "financial_exposure": {
            "total_penalty_exposure": total_penalty_exposure
        },
        "filter": {"party": party},
        "generated_at": datetime.now().isoformat()
    }


@router.get("/compliance-audit")
async def get_compliance_audit_report(
    party: Optional[str] = Query(None, description="Filter by party"),
    db: Session = Depends(get_db)
):
    """Generate compliance audit report"""
    
    query = db.query(Obligation).filter(Obligation.status == "active")
    
    if party:
        query = query.filter(Obligation.party.ilike(f"%{party}%"))
    
    obligations = query.all()
    
    # Compliance analysis
    compliance_stats = {
        "compliant": 0,
        "non_compliant": 0,
        "at_risk": 0,
        "unknown": 0
    }
    
    breach_analysis = {
        "obligations_with_breaches": 0,
        "total_breaches": 0,
        "average_breaches_per_obligation": 0
    }
    
    party_compliance = {}
    
    for obligation in obligations:
        compliance_status = obligation.compliance_status
        compliance_stats[compliance_status] += 1
        
        if obligation.breach_count > 0:
            breach_analysis["obligations_with_breaches"] += 1
            breach_analysis["total_breaches"] += obligation.breach_count
        
        # Party-level compliance
        party_name = obligation.party
        if party_name not in party_compliance:
            party_compliance[party_name] = {
                "total_obligations": 0,
                "compliant": 0,
                "non_compliant": 0,
                "at_risk": 0,
                "unknown": 0,
                "breach_count": 0
            }
        
        party_compliance[party_name]["total_obligations"] += 1
        party_compliance[party_name][compliance_status] += 1
        party_compliance[party_name]["breach_count"] += obligation.breach_count
    
    # Calculate average breaches
    if breach_analysis["obligations_with_breaches"] > 0:
        breach_analysis["average_breaches_per_obligation"] = round(
            breach_analysis["total_breaches"] / breach_analysis["obligations_with_breaches"], 2
        )
    
    # Calculate compliance rates
    total_obligations = len(obligations)
    overall_compliance_rate = (compliance_stats["compliant"] / total_obligations * 100) if total_obligations > 0 else 0
    
    # Party compliance rates
    for party_name, stats in party_compliance.items():
        if stats["total_obligations"] > 0:
            stats["compliance_rate"] = round(
                stats["compliant"] / stats["total_obligations"] * 100, 2
            )
        else:
            stats["compliance_rate"] = 0
    
    return {
        "report_type": "compliance_audit",
        "overall_compliance_rate": round(overall_compliance_rate, 2),
        "compliance_stats": compliance_stats,
        "breach_analysis": breach_analysis,
        "party_compliance": party_compliance,
        "total_obligations": total_obligations,
        "filter": {"party": party},
        "generated_at": datetime.now().isoformat()
    }


@router.get("/financial-exposure")
async def get_financial_exposure_report(
    party: Optional[str] = Query(None, description="Filter by party"),
    db: Session = Depends(get_db)
):
    """Generate financial exposure report"""
    
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
    currency_exposures = {}
    
    for obligation in obligations:
        party_name = obligation.party
        
        if party_name not in party_exposures:
            party_exposures[party_name] = {
                "penalty_exposure": 0,
                "rebate_exposure": 0,
                "total_exposure": 0,
                "obligation_count": 0
            }
        
        # Penalty exposure
        if obligation.penalty_amount:
            penalty_amount = float(obligation.penalty_amount)
            penalty_currency = obligation.penalty_currency or "INR"
            
            total_penalty_exposure += penalty_amount
            party_exposures[party_name]["penalty_exposure"] += penalty_amount
            
            if penalty_currency not in currency_exposures:
                currency_exposures[penalty_currency] = {"penalty": 0, "rebate": 0}
            currency_exposures[penalty_currency]["penalty"] += penalty_amount
        
        # Rebate exposure
        if obligation.rebate_amount:
            rebate_amount = float(obligation.rebate_amount)
            rebate_currency = obligation.rebate_currency or "INR"
            
            total_rebate_exposure += rebate_amount
            party_exposures[party_name]["rebate_exposure"] += rebate_amount
            
            if rebate_currency not in currency_exposures:
                currency_exposures[rebate_currency] = {"penalty": 0, "rebate": 0}
            currency_exposures[rebate_currency]["rebate"] += rebate_amount
        
        party_exposures[party_name]["obligation_count"] += 1
        party_exposures[party_name]["total_exposure"] = (
            party_exposures[party_name]["penalty_exposure"] + 
            party_exposures[party_name]["rebate_exposure"]
        )
    
    # Sort parties by total exposure
    sorted_parties = sorted(
        party_exposures.items(),
        key=lambda x: x[1]["total_exposure"],
        reverse=True
    )
    
    return {
        "report_type": "financial_exposure",
        "total_exposure": {
            "penalty_exposure": total_penalty_exposure,
            "rebate_exposure": total_rebate_exposure,
            "total_financial_exposure": total_penalty_exposure + total_rebate_exposure
        },
        "party_exposures": dict(sorted_parties),
        "currency_exposures": currency_exposures,
        "obligation_count": len(obligations),
        "filter": {"party": party},
        "generated_at": datetime.now().isoformat()
    }


def _get_quarter_dates(year: int, quarter: str) -> dict:
    """Get start and end dates for a quarter"""
    quarter_months = {
        "Q1": (1, 3),
        "Q2": (4, 6),
        "Q3": (7, 9),
        "Q4": (10, 12)
    }
    
    start_month, end_month = quarter_months.get(quarter, (1, 3))
    
    start_date = datetime(year, start_month, 1)
    if end_month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(year, end_month + 1, 1) - timedelta(days=1)
    
    return {
        "start": start_date,
        "end": end_date
    }


def _generate_quarterly_recommendations(
    obligations: List[Obligation],
    alerts: List[Alert],
    compliance_rate: float
) -> List[str]:
    """Generate recommendations based on quarterly data"""
    
    recommendations = []
    
    # Compliance recommendations
    if compliance_rate < 80:
        recommendations.append("Focus on improving compliance rates - current rate is below 80%")
    
    # Risk recommendations
    high_risk_count = len([o for o in obligations if o.risk_level in ["high", "critical"]])
    if high_risk_count > len(obligations) * 0.3:
        recommendations.append("High number of high-risk obligations - consider risk mitigation strategies")
    
    # Alert recommendations
    critical_alerts = len([a for a in alerts if a.severity == "critical"])
    if critical_alerts > 0:
        recommendations.append(f"Address {critical_alerts} critical alerts immediately")
    
    # Overdue recommendations
    overdue_count = len([o for o in obligations if o.is_overdue()])
    if overdue_count > 0:
        recommendations.append(f"Resolve {overdue_count} overdue obligations to prevent penalties")
    
    # Financial recommendations
    total_penalty_exposure = sum(
        float(o.penalty_amount) for o in obligations 
        if o.penalty_amount and o.status == "active"
    )
    if total_penalty_exposure > 1000000:  # 10 lakh
        recommendations.append("High penalty exposure detected - review high-value obligations")
    
    return recommendations
