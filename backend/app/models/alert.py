"""
Alert database model
"""

from sqlalchemy import Column, String, DateTime, Text, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class Alert(Base):
    """Alert model"""
    __tablename__ = "alerts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id = Column(UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=True)
    obligation_id = Column(UUID(as_uuid=True), ForeignKey("obligations.id"), nullable=True)
    
    # Alert details
    alert_type = Column(String(100), nullable=False)  # deadline_reminder, breach_detected, compliance_check, etc.
    severity = Column(String(20), nullable=False)  # low, medium, high, critical
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    
    # Status and handling
    status = Column(String(50), default="active")  # active, acknowledged, resolved, dismissed
    acknowledged_by = Column(String(255))
    acknowledged_at = Column(DateTime)
    resolved_by = Column(String(255))
    resolved_at = Column(DateTime)
    
    # Timing
    triggered_at = Column(DateTime, default=func.now())
    scheduled_for = Column(DateTime)  # For scheduled alerts
    
    # Evidence and context
    evidence_data = Column(Text)  # Supporting data for the alert (JSON as text)
    related_transactions = Column(Text)  # Related transaction IDs (JSON as text)
    compliance_data = Column(Text)  # Compliance check results (JSON as text)
    
    # Notification
    notification_sent = Column(Boolean, default=False)
    notification_channels = Column(Text)  # email, slack, teams, etc. (JSON as text)
    notification_attempts = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    contract = relationship("Contract", back_populates="alerts")
    obligation = relationship("Obligation", back_populates="alerts")
    
    def __repr__(self):
        return f"<Alert(id={self.id}, type='{self.alert_type}', severity='{self.severity}')>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "contract_id": str(self.contract_id) if self.contract_id else None,
            "obligation_id": str(self.obligation_id) if self.obligation_id else None,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "title": self.title,
            "message": self.message,
            "status": self.status,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "scheduled_for": self.scheduled_for.isoformat() if self.scheduled_for else None,
            "evidence_data": self.evidence_data,
            "related_transactions": self.related_transactions,
            "compliance_data": self.compliance_data,
            "notification_sent": self.notification_sent,
            "notification_channels": self.notification_channels,
            "notification_attempts": self.notification_attempts,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def is_urgent(self):
        """Check if alert is urgent based on severity and age"""
        urgent_severities = ["high", "critical"]
        if self.severity in urgent_severities:
            return True
        
        # Check if alert is old and unresolved
        from datetime import datetime, timedelta
        if self.status == "active" and self.triggered_at:
            age_hours = (datetime.now() - self.triggered_at).total_seconds() / 3600
            return age_hours > 24  # More than 24 hours old
        
        return False
    
    def get_priority_score(self):
        """Calculate priority score for alert sorting"""
        score = 0
        
        # Severity scoring
        severity_scores = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        score += severity_scores.get(self.severity, 1) * 10
        
        # Age factor
        if self.status == "active" and self.triggered_at:
            from datetime import datetime
            age_hours = (datetime.now() - self.triggered_at).total_seconds() / 3600
            score += min(age_hours / 2, 20)  # Up to 20 points for age
        
        # Type-specific scoring
        urgent_types = ["breach_detected", "compliance_failure", "deadline_overdue"]
        if self.alert_type in urgent_types:
            score += 15
        
        return score
