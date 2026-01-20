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
    DISPATCHED = "Dispatched"


class RiskLevel(str, enum.Enum):
    """Risk level / priority classification for tickets."""
    GREEN = "Green"
    YELLOW = "Yellow"
    RED = "Red"


class IssueCategory(str, enum.Enum):
    """Categories for maintenance issues."""
    PLUMBING = "Plumbing"
    ELECTRICAL = "Electrical"
    HVAC = "HVAC"
    APPLIANCE = "Appliance"
    STRUCTURAL = "Structural"
    PEST = "Pest Control"
    LOCKSMITH = "Locksmith"
    OTHER = "Other"


class Ticket(Base):
    """
    Maintenance ticket model.
    Stores conversation history, AI analysis, and customer contact info.
    The "Golden Ticket" summary is generated when escalating to a vendor.
    """
    __tablename__ = "tickets"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Customer information
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    postal_code = Column(String, nullable=False)
    unit_id = Column(String, nullable=True)
    
    # Contact/access info collected during escalation (JSON)
    # e.g., {"phone": "555-1234", "access_code": "Key #123", "availability": "M-F 9-5"}
    contact_info = Column(JSON, default=dict)
    
    # Issue details
    category = Column(String, default=IssueCategory.OTHER.value)  # Plumbing, Electrical, etc.
    issue_title = Column(String, nullable=True)
    issue_description = Column(Text, nullable=True)
    
    # AI analysis results
    ai_estimated_cost = Column(String, nullable=True)
    ai_diagnosis = Column(Text, nullable=True)
    ai_recommended_action = Column(Text, nullable=True)
    
    # "Golden Ticket" vendor summary - concise dispatch info
    # e.g., "Issue: Leaking Toilet. DIY Failed. Parts: Fill Valve likely. Access: Key #123"
    summary = Column(Text, nullable=True)
    
    # Conversation and status tracking
    conversation_history = Column(JSON, default=list)
    status = Column(String, default=TicketStatus.OPEN.value)
    priority = Column(String, default=RiskLevel.GREEN.value)  # Green/Yellow/Red
    risk_level = Column(String, default=RiskLevel.GREEN.value)  # Alias for compatibility
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UnitBaseline(Base):
    """
    Unit baseline model for move-in/move-out video audits.
    Stores AI-generated JSON descriptions of unit condition.
    """
    __tablename__ = "unit_baselines"
    
    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(String, nullable=False, unique=True, index=True)
    
    # AI-generated baseline description from move-in video (legacy text)
    move_in_video_summary = Column(Text, nullable=True)
    
    # Structured baseline JSON for item-by-item comparison
    # Format: [{"item": "Wall", "condition": "Good", "room": "Living Room", "timestamp": "0:15"}, ...]
    baseline_json = Column(JSON, default=list)
    
    # Audit tracking
    last_audit_date = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
