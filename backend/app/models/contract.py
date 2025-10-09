"""
Contract database model
"""

from sqlalchemy import Column, String, DateTime, Text, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class Contract(Base):
    """Contract model"""
    __tablename__ = "contracts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    party_a = Column(String(255), nullable=False)
    party_b = Column(String(255), nullable=False)
    contract_type = Column(String(100))
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    status = Column(String(50), default="active")
    file_path = Column(Text)
    extracted_text = Column(Text)
    processing_status = Column(String(50), default="pending")
    processing_error = Column(Text)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    obligations = relationship("Obligation", back_populates="contract", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="contract", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Contract(id={self.id}, title='{self.title}', status='{self.status}')>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "title": self.title,
            "party_a": self.party_a,
            "party_b": self.party_b,
            "contract_type": self.contract_type,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "status": self.status,
            "file_path": self.file_path,
            "processing_status": self.processing_status,
            "processing_error": self.processing_error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "obligation_count": len(self.obligations) if self.obligations else 0
        }
