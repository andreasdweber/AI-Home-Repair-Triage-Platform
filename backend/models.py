"""
Fix-It AI - Database Models
SQLAlchemy models for tickets and unit baselines
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Enum
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()


class TicketStatus(str, enum.Enum):
    """Status options for maintenance tickets."""
    OPEN = "Open"
    DEFLECTED = "Deflected"
    ESCALATED = "Escalated"


class RiskLevel(str, enum.Enum):
    """Risk level classification for tickets."""
    GREEN = "Green"
    YELLOW = "Yellow"
    RED = "Red"


class Ticket(Base):
    """
    Maintenance ticket model.
    Stores conversation history, AI analysis, and customer contact info.
    """
    __tablename__ = "tickets"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Customer information
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    postal_code = Column(String, nullable=False)
    unit_id = Column(String, nullable=True)
    
    # Issue details
    issue_category = Column(String, nullable=True)
    issue_title = Column(String, nullable=True)
    issue_description = Column(Text, nullable=True)
    
    # AI analysis results
    ai_estimated_cost = Column(String, nullable=True)
    ai_diagnosis = Column(Text, nullable=True)
    ai_recommended_action = Column(Text, nullable=True)
    
    # Conversation and status tracking
    conversation_history = Column(JSON, default=list)
    status = Column(String, default=TicketStatus.OPEN.value)
    risk_level = Column(String, default=RiskLevel.GREEN.value)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UnitBaseline(Base):
    """
    Unit baseline model for move-in/move-out video audits.
    Stores AI-generated descriptions of unit condition.
    """
    __tablename__ = "unit_baselines"
    
    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(String, nullable=False, unique=True, index=True)
    
    # AI-generated baseline description from move-in video
    move_in_video_summary = Column(Text, nullable=True)
    
    # Audit tracking
    last_audit_date = Column(DateTime, default=datetime.utcnow)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
