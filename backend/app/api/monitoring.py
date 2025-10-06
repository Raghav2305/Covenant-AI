"""
Monitoring API endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from app.core.simple_database import get_db
from app.models.obligation import Obligation
from app.models.alert import Alert
from app.services.monitoring_engine import MonitoringEngine
import structlog

logger = structlog.get_logger()
router = APIRouter()


@router.post("/check-all")
async def check_all_obligations(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Trigger comprehensive compliance check for all obligations"""
    
    logger.info("Starting comprehensive obligation check")
    
    try:
        monitoring_engine = MonitoringEngine()
        await monitoring_engine.initialize()
        
        # Run in background for large datasets
        background_tasks.add_task(
            _run_comprehensive_check,
            monitoring_engine,
            db
        )
        
        return {
            "message": "Comprehensive compliance check started",
            "status": "running",
            "note": "Check is running in background. Use /monitoring/status to check progress."
        }
        
    except Exception as e:
        logger.error("Failed to start comprehensive check", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to start check: {str(e)}")


@router.get("/status")
async def get_monitoring_status(
    db: Session = Depends(get_db)
):
    """Get current monitoring status and statistics"""
    
    try:
        # Get obligation statistics
        total_obligations = db.query(Obligation).count()
        active_obligations = db.query(Obligation).filter(Obligation.status == "active").count()
        overdue_obligations = len([o for o in db.query(Obligation).filter(Obligation.status == "active").all() if o.is_overdue()])
        
        # Get alert statistics
        total_alerts = db.query(Alert).count()
        active_alerts = db.query(Alert).filter(Alert.status == "active").count()
        urgent_alerts = len([a for a in db.query(Alert).filter(Alert.status == "active").all() if a.is_urgent()])
        
        # Get compliance statistics
        compliant_obligations = db.query(Obligation).filter(Obligation.compliance_status == "compliant").count()
        non_compliant_obligations = db.query(Obligation).filter(Obligation.compliance_status == "non_compliant").count()
        unknown_compliance = db.query(Obligation).filter(Obligation.compliance_status == "unknown").count()
        
        # Get recent activity
        recent_alerts = db.query(Alert).order_by(desc(Alert.created_at)).limit(10).all()
        
        return {
            "obligations": {
                "total": total_obligations,
                "active": active_obligations,
                "overdue": overdue_obligations,
                "compliant": compliant_obligations,
                "non_compliant": non_compliant_obligations,
                "unknown_compliance": unknown_compliance
            },
            "alerts": {
                "total": total_alerts,
                "active": active_alerts,
                "urgent": urgent_alerts
            },
            "recent_alerts": [alert.to_dict() for alert in recent_alerts],
            "status": "operational"
        }
        
    except Exception as e:
        logger.error("Failed to get monitoring status", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.post("/deadline-check")
async def check_deadline_alerts(
    db: Session = Depends(get_db)
):
    """Check for upcoming deadlines and create alerts"""
    
    logger.info("Starting deadline check")
    
    try:
        monitoring_engine = MonitoringEngine()
        await monitoring_engine.initialize()
        
        alerts_created = await monitoring_engine.check_deadline_alerts(db)
        
        logger.info("Deadline check completed", alerts_created=len(alerts_created))
        
        return {
            "message": "Deadline check completed",
            "alerts_created": len(alerts_created),
            "alerts": [alert.to_dict() for alert in alerts_created]
        }
        
    except Exception as e:
        logger.error("Deadline check failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Deadline check failed: {str(e)}")


@router.get("/alerts")
async def list_alerts(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    alert_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List alerts with optional filtering"""
    
    query = db.query(Alert)
    
    if status:
        query = query.filter(Alert.status == status)
    
    if severity:
        query = query.filter(Alert.severity == severity)
    
    if alert_type:
        query = query.filter(Alert.alert_type == alert_type)
    
    alerts = query.order_by(desc(Alert.created_at)).offset(skip).limit(limit).all()
    
    return {
        "alerts": [alert.to_dict() for alert in alerts],
        "total": len(alerts),
        "skip": skip,
        "limit": limit,
        "filters": {
            "status": status,
            "severity": severity,
            "alert_type": alert_type
        }
    }


@router.get("/alerts/urgent")
async def get_urgent_alerts(
    db: Session = Depends(get_db)
):
    """Get all urgent alerts"""
    
    alerts = db.query(Alert).filter(Alert.status == "active").all()
    urgent_alerts = [alert for alert in alerts if alert.is_urgent()]
    
    # Sort by priority score
    urgent_alerts.sort(key=lambda x: x.get_priority_score(), reverse=True)
    
    return {
        "alerts": [alert.to_dict() for alert in urgent_alerts],
        "count": len(urgent_alerts),
        "criteria": "High severity, critical alerts, or alerts older than 24 hours"
    }


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    acknowledged_by: str,
    db: Session = Depends(get_db)
):
    """Acknowledge an alert"""
    
    import uuid
    try:
        alert_uuid = uuid.UUID(alert_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid alert ID")
    
    alert = db.query(Alert).filter(Alert.id == alert_uuid).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    if alert.status != "active":
        raise HTTPException(status_code=400, detail="Alert is not active")
    
    alert.status = "acknowledged"
    alert.acknowledged_by = acknowledged_by
    alert.acknowledged_at = db.query(Alert).filter(Alert.id == alert_uuid).first().created_at
    
    db.commit()
    
    logger.info("Alert acknowledged", alert_id=alert_id, acknowledged_by=acknowledged_by)
    
    return {
        "message": "Alert acknowledged successfully",
        "alert_id": alert_id,
        "acknowledged_by": acknowledged_by
    }


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    resolved_by: str,
    db: Session = Depends(get_db)
):
    """Resolve an alert"""
    
    import uuid
    try:
        alert_uuid = uuid.UUID(alert_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid alert ID")
    
    alert = db.query(Alert).filter(Alert.id == alert_uuid).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.status = "resolved"
    alert.resolved_by = resolved_by
    alert.resolved_at = db.query(Alert).filter(Alert.id == alert_uuid).first().created_at
    
    db.commit()
    
    logger.info("Alert resolved", alert_id=alert_id, resolved_by=resolved_by)
    
    return {
        "message": "Alert resolved successfully",
        "alert_id": alert_id,
        "resolved_by": resolved_by
    }


@router.get("/compliance/summary")
async def get_compliance_summary(
    party: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get compliance summary across all obligations"""
    
    query = db.query(Obligation).filter(Obligation.status == "active")
    
    if party:
        query = query.filter(Obligation.party.ilike(f"%{party}%"))
    
    obligations = query.all()
    
    # Calculate compliance metrics
    total_obligations = len(obligations)
    compliant_count = len([o for o in obligations if o.compliance_status == "compliant"])
    non_compliant_count = len([o for o in obligations if o.compliance_status == "non_compliant"])
    at_risk_count = len([o for o in obligations if o.compliance_status == "at_risk"])
    unknown_count = len([o for o in obligations if o.compliance_status == "unknown"])
    
    # Calculate compliance rate
    compliance_rate = (compliant_count / total_obligations * 100) if total_obligations > 0 else 0
    
    # Risk distribution
    risk_distribution = {}
    for obligation in obligations:
        risk_level = obligation.risk_level
        risk_distribution[risk_level] = risk_distribution.get(risk_level, 0) + 1
    
    # Breach statistics
    total_breaches = sum(o.breach_count for o in obligations)
    obligations_with_breaches = len([o for o in obligations if o.breach_count > 0])
    
    return {
        "total_obligations": total_obligations,
        "compliance_rate": round(compliance_rate, 2),
        "compliance_breakdown": {
            "compliant": compliant_count,
            "non_compliant": non_compliant_count,
            "at_risk": at_risk_count,
            "unknown": unknown_count
        },
        "risk_distribution": risk_distribution,
        "breach_statistics": {
            "total_breaches": total_breaches,
            "obligations_with_breaches": obligations_with_breaches,
            "average_breaches_per_obligation": round(total_breaches / total_obligations, 2) if total_obligations > 0 else 0
        },
        "filter": {"party": party}
    }


async def _run_comprehensive_check(monitoring_engine: MonitoringEngine, db: Session):
    """Background task for comprehensive compliance check"""
    try:
        logger.info("Starting background comprehensive check")
        result = await monitoring_engine.check_all_obligations(db)
        logger.info("Background comprehensive check completed", **result)
    except Exception as e:
        logger.error("Background comprehensive check failed", error=str(e))
