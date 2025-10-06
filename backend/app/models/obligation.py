"""
Obligation database model
"""

from sqlalchemy import Column, String, DateTime, Text, Integer, Boolean, ForeignKey, Numeric
# from sqlalchemy.dialects.postgresql import UUID, JSONB  # Not needed for SQLite
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class Obligation(Base):
    """Obligation model"""
    __tablename__ = "obligations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    contract_id = Column(String, ForeignKey("contracts.id"), nullable=False)
    obligation_id = Column(String(100), unique=True, nullable=False)
    
    # Obligation details
    party = Column(String(255), nullable=False)
    obligation_type = Column(String(100), nullable=False)  # Report Submission, Payment, SLA, etc.
    description = Column(Text)
    deadline = Column(DateTime)
    frequency = Column(String(50))  # Daily, Weekly, Monthly, Quarterly, Annually
    
    # Financial terms
    penalty_amount = Column(Numeric(15, 2))
    penalty_currency = Column(String(10), default="INR")
    rebate_amount = Column(Numeric(15, 2))
    rebate_currency = Column(String(10), default="INR")
    
    # Conditions and triggers
    condition = Column(Text)  # JSON string of conditions
    trigger_conditions = Column(Text)  # Structured trigger conditions (JSON as text)
    
    # Status and monitoring
    status = Column(String(50), default="active")  # active, completed, breached, cancelled
    risk_level = Column(String(20), default="medium")  # low, medium, high, critical
    last_checked = Column(DateTime)
    next_check = Column(DateTime)
    
    # Compliance tracking
    compliance_status = Column(String(50), default="unknown")  # compliant, non_compliant, unknown
    compliance_evidence = Column(Text)  # Evidence of compliance/non-compliance (JSON as text)
    breach_count = Column(Integer, default=0)
    last_breach_date = Column(DateTime)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    contract = relationship("Contract", back_populates="obligations")
    alerts = relationship("Alert", back_populates="obligation", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Obligation(id={self.id}, type='{self.obligation_type}', party='{self.party}')>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "contract_id": str(self.contract_id),
            "obligation_id": self.obligation_id,
            "party": self.party,
            "obligation_type": self.obligation_type,
            "description": self.description,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "frequency": self.frequency,
            "penalty_amount": float(self.penalty_amount) if self.penalty_amount else None,
            "penalty_currency": self.penalty_currency,
            "rebate_amount": float(self.rebate_amount) if self.rebate_amount else None,
            "rebate_currency": self.rebate_currency,
            "condition": self.condition,
            "trigger_conditions": self.trigger_conditions,
            "status": self.status,
            "risk_level": self.risk_level,
            "last_checked": self.last_checked.isoformat() if self.last_checked else None,
            "next_check": self.next_check.isoformat() if self.next_check else None,
            "compliance_status": self.compliance_status,
            "compliance_evidence": self.compliance_evidence,
            "breach_count": self.breach_count,
            "last_breach_date": self.last_breach_date.isoformat() if self.last_breach_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def is_overdue(self):
        """Check if obligation is overdue"""
        if not self.deadline:
            return False
        from datetime import datetime
        return datetime.now() > self.deadline and self.status == "active"
    
    def days_until_deadline(self):
        """Calculate days until deadline"""
        if not self.deadline:
            return None
        from datetime import datetime
        delta = self.deadline - datetime.now()
        return delta.days
    
    def get_risk_score(self):
        """Calculate risk score based on various factors"""
        score = 0
        
        # Deadline proximity
        days_until = self.days_until_deadline()
        if days_until is not None:
            if days_until < 0:  # Overdue
                score += 50
            elif days_until <= 7:  # Due within a week
                score += 30
            elif days_until <= 30:  # Due within a month
                score += 15
        
        # Breach history
        score += self.breach_count * 10
        
        # Penalty amount
        if self.penalty_amount:
            if self.penalty_amount > 1000000:  # > 10 lakh
                score += 20
            elif self.penalty_amount > 100000:  # > 1 lakh
                score += 10
        
        # Risk level
        risk_multipliers = {"low": 0.5, "medium": 1.0, "high": 1.5, "critical": 2.0}
        score *= risk_multipliers.get(self.risk_level, 1.0)
        
        return min(score, 100)  # Cap at 100
