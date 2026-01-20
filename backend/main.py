"""
Fix-It AI - Home Repair Triage Backend
FastAPI backend with Google Gemini AI integration for conversational triage and video audits
"""

import os
import json
from datetime import datetime
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# SQLAlchemy imports for PostgreSQL support
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import models and agent
from models import Base, Ticket, UnitBaseline, TicketStatus, RiskLevel
from agent import MaintenanceAgent

# Load environment variables
load_dotenv()

# Database configuration - supports both PostgreSQL (production) and SQLite (local)
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Production: Use PostgreSQL
    # Fix Render's postgres:// URL to postgresql:// for SQLAlchemy
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(DATABASE_URL)
else:
    # Local development: Use SQLite
    engine = create_engine("sqlite:///./fixit.db", connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Admin key for accessing tickets (MVP security)
ADMIN_KEY = os.getenv("ADMIN_KEY", "secret123")


def init_db():
    """Initialize the database and create tables if they don't exist."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        return db
    except:
        db.close()
        raise


# Pydantic models for API requests/responses
class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    ticket_id: Optional[int] = None
    message: str
    conversation_history: Optional[List[Dict[str, Any]]] = []


class TicketCreate(BaseModel):
    name: str
    phone: str
    postal_code: str
    unit_id: Optional[str] = None
    issue_category: Optional[str] = None
    issue_title: Optional[str] = None
    issue_description: Optional[str] = None
    conversation_history: Optional[List[Dict[str, Any]]] = []
    status: Optional[str] = TicketStatus.OPEN.value
    risk_level: Optional[str] = RiskLevel.GREEN.value
    ai_estimated_cost: Optional[str] = None
    ai_diagnosis: Optional[str] = None
    ai_recommended_action: Optional[str] = None


class TicketUpdate(BaseModel):
    status: Optional[str] = None
    risk_level: Optional[str] = None
    conversation_history: Optional[List[Dict[str, Any]]] = None
    ai_diagnosis: Optional[str] = None
    ai_recommended_action: Optional[str] = None


# Initialize FastAPI app
app = FastAPI(
    title="Fix-It AI Backend",
    description="AI-powered home repair triage system",
    version="1.0.0"
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()

# Configure CORS for local development and production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Fix-It AI Backend is running"}


@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "features": ["chat", "video-audit", "triage"],
        "api_configured": bool(os.getenv("GEMINI_API_KEY"))
    }


# ==================== CHAT ENDPOINT ====================

@app.post("/chat")
async def chat(
    image: UploadFile = File(None),
    message: str = Form(""),
    conversation_history: str = Form("[]"),
    ticket_id: Optional[int] = Form(None)
):
    """
    Conversational chat endpoint for maintenance triage.
    
    Accepts an optional image, message, and conversation history.
    The AI agent will either ask for more information or provide a diagnosis.
    
    Returns:
        - response: AI's message to the user
        - diagnosis: Full diagnosis object (if ready)
        - risk_level: Green/Yellow/Red (if diagnosis ready)
        - needs_more_info: Whether more info is needed
        - conversation_history: Updated conversation with AI response
    """
    
    # Parse conversation history
    try:
        history = json.loads(conversation_history) if conversation_history else []
    except json.JSONDecodeError:
        history = []
    
    # Add current message to history
    if message:
        history.append({"role": "user", "content": message})
    
    # Process image if provided
    image_data = None
    image_mime_type = None
    if image and image.filename:
        allowed_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
        if image.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid image type. Allowed types: {', '.join(allowed_types)}"
            )
        image_data = await image.read()
        image_mime_type = image.content_type
        
        # Note in history that an image was provided
        if not any("image" in msg.get("content", "").lower() for msg in history[-3:]):
            history.append({"role": "user", "content": "[User uploaded an image of the issue]"})
    
    try:
        # Initialize agent and run triage
        agent = MaintenanceAgent()
        result = agent.triage_with_image_bytes(history, image_data, image_mime_type)
        
        # Add AI response to history
        if result.get("text"):
            history.append({"role": "assistant", "content": result["text"]})
        
        # Update ticket if ID provided
        if ticket_id:
            db = get_db()
            try:
                ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
                if ticket:
                    ticket.conversation_history = history
                    if result.get("risk"):
                        ticket.risk_level = result["risk"]
                    if result.get("action") == "Escalate":
                        ticket.status = TicketStatus.ESCALATED.value
                    db.commit()
            finally:
                db.close()
        
        return {
            "success": True,
            "response": result.get("text"),
            "risk_level": result.get("risk"),
            "action": result.get("action"),
            "needs_more_info": result.get("action") == "Info",
            "conversation_history": history
        }
        
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")


# ==================== VIDEO AUDIT ENDPOINTS ====================

@app.post("/audit/move-in")
async def audit_move_in(
    video: UploadFile = File(...),
    unit_id: str = Form(...)
):
    """
    Process a move-in video to create a baseline condition report.
    
    Accepts a video file and unit ID. Uses Gemini's native video capabilities
    to analyze the walkthrough and document the unit's condition.
    
    The baseline is saved to the database for future move-out comparison.
    """
    
    # Validate video type
    allowed_types = ["video/mp4", "video/quicktime", "video/x-msvideo", "video/webm", "video/mpeg"]
    if video.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid video type. Allowed types: {', '.join(allowed_types)}"
        )
    
    try:
        # Read video data
        video_data = await video.read()
        
        # Initialize agent and run audit
        agent = MaintenanceAgent()
        result = agent.audit_video_bytes(
            video_data=video_data,
            video_mime_type=video.content_type,
            mode="move-in"
        )
        
        if result.get("success") and result.get("summary"):
            # Save or update baseline in database
            db = get_db()
            try:
                existing = db.query(UnitBaseline).filter(UnitBaseline.unit_id == unit_id).first()
                
                if existing:
                    existing.move_in_video_summary = result["summary"]
                    existing.last_audit_date = datetime.utcnow()
                    existing.updated_at = datetime.utcnow()
                else:
                    baseline = UnitBaseline(
                        unit_id=unit_id,
                        move_in_video_summary=result["summary"],
                        last_audit_date=datetime.utcnow()
                    )
                    db.add(baseline)
                
                db.commit()
                result["saved_to_database"] = True
            except Exception as db_error:
                result["saved_to_database"] = False
                result["database_error"] = str(db_error)
            finally:
                db.close()
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing move-in audit: {str(e)}")


@app.post("/audit/move-out")
async def audit_move_out(
    video: UploadFile = File(...),
    unit_id: str = Form(...)
):
    """
    Process a move-out video and compare against the move-in baseline.
    
    Retrieves the baseline for the unit and uses Gemini to identify
    only NEW damages not present during move-in.
    """
    
    # Validate video type
    allowed_types = ["video/mp4", "video/quicktime", "video/x-msvideo", "video/webm", "video/mpeg"]
    if video.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid video type. Allowed types: {', '.join(allowed_types)}"
        )
    
    # Retrieve baseline from database
    db = get_db()
    try:
        baseline = db.query(UnitBaseline).filter(UnitBaseline.unit_id == unit_id).first()
        baseline_description = baseline.move_in_video_summary if baseline else None
    finally:
        db.close()
    
    if not baseline_description:
        raise HTTPException(
            status_code=404,
            detail=f"No move-in baseline found for unit '{unit_id}'. Please complete a move-in audit first."
        )
    
    try:
        # Read video data
        video_data = await video.read()
        
        # Initialize agent and run comparison audit
        agent = MaintenanceAgent()
        result = agent.audit_video_bytes(
            video_data=video_data,
            video_mime_type=video.content_type,
            mode="move-out",
            baseline_text=baseline_description
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing move-out audit: {str(e)}")


# ==================== TICKET MANAGEMENT ENDPOINTS ====================

@app.post("/tickets")
async def create_ticket(ticket: TicketCreate):
    """
    Create a new maintenance ticket.
    Accepts ticket information along with optional AI diagnosis details.
    """
    try:
        db = get_db()
        db_ticket = Ticket(
            name=ticket.name,
            phone=ticket.phone,
            postal_code=ticket.postal_code,
            unit_id=ticket.unit_id,
            issue_category=ticket.issue_category,
            issue_title=ticket.issue_title,
            issue_description=ticket.issue_description,
            conversation_history=ticket.conversation_history or [],
            status=ticket.status or TicketStatus.OPEN.value,
            risk_level=ticket.risk_level or RiskLevel.GREEN.value,
            ai_estimated_cost=ticket.ai_estimated_cost,
            ai_diagnosis=ticket.ai_diagnosis,
            ai_recommended_action=ticket.ai_recommended_action
        )
        db.add(db_ticket)
        db.commit()
        db.refresh(db_ticket)
        ticket_id = db_ticket.id
        db.close()
        
        return {
            "status": "success",
            "message": "Ticket created successfully",
            "ticket_id": ticket_id
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error creating ticket: {str(e)}"
        )


@app.get("/tickets")
async def get_tickets(
    admin_key: str = Query(None),
    status: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None)
):
    """
    Retrieve tickets from the database (Admin only).
    Supports filtering by status and risk_level.
    """
    if admin_key != ADMIN_KEY:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized. Invalid or missing admin_key."
        )
    
    try:
        db = get_db()
        query = db.query(Ticket)
        
        # Apply filters
        if status:
            query = query.filter(Ticket.status == status)
        if risk_level:
            query = query.filter(Ticket.risk_level == risk_level)
        
        tickets = query.order_by(Ticket.created_at.desc()).all()
        db.close()
        
        tickets_list = [
            {
                "id": t.id,
                "name": t.name,
                "phone": t.phone,
                "postal_code": t.postal_code,
                "unit_id": t.unit_id,
                "issue_category": t.issue_category,
                "issue_title": t.issue_title,
                "issue_description": t.issue_description,
                "conversation_history": t.conversation_history,
                "status": t.status,
                "risk_level": t.risk_level,
                "ai_estimated_cost": t.ai_estimated_cost,
                "ai_diagnosis": t.ai_diagnosis,
                "ai_recommended_action": t.ai_recommended_action,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None
            }
            for t in tickets
        ]
        
        return {
            "status": "success",
            "count": len(tickets_list),
            "tickets": tickets_list
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving tickets: {str(e)}"
        )


@app.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: int, admin_key: str = Query(None)):
    """Retrieve a single ticket by ID."""
    if admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized.")
    
    db = get_db()
    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found.")
        
        return {
            "id": ticket.id,
            "name": ticket.name,
            "phone": ticket.phone,
            "postal_code": ticket.postal_code,
            "unit_id": ticket.unit_id,
            "issue_category": ticket.issue_category,
            "issue_title": ticket.issue_title,
            "issue_description": ticket.issue_description,
            "conversation_history": ticket.conversation_history,
            "status": ticket.status,
            "risk_level": ticket.risk_level,
            "ai_estimated_cost": ticket.ai_estimated_cost,
            "ai_diagnosis": ticket.ai_diagnosis,
            "ai_recommended_action": ticket.ai_recommended_action,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
            "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None
        }
    finally:
        db.close()


@app.patch("/tickets/{ticket_id}")
async def update_ticket(ticket_id: int, update: TicketUpdate, admin_key: str = Query(None)):
    """Update a ticket's status, risk level, or other fields."""
    if admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized.")
    
    db = get_db()
    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found.")
        
        if update.status is not None:
            ticket.status = update.status
        if update.risk_level is not None:
            ticket.risk_level = update.risk_level
        if update.conversation_history is not None:
            ticket.conversation_history = update.conversation_history
        if update.ai_diagnosis is not None:
            ticket.ai_diagnosis = update.ai_diagnosis
        if update.ai_recommended_action is not None:
            ticket.ai_recommended_action = update.ai_recommended_action
        
        db.commit()
        
        return {"status": "success", "message": "Ticket updated"}
    finally:
        db.close()


# ==================== UNIT BASELINE ENDPOINTS ====================

@app.get("/baselines/{unit_id}")
async def get_baseline(unit_id: str, admin_key: str = Query(None)):
    """Retrieve the baseline for a specific unit."""
    if admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized.")
    
    db = get_db()
    try:
        baseline = db.query(UnitBaseline).filter(UnitBaseline.unit_id == unit_id).first()
        if not baseline:
            raise HTTPException(status_code=404, detail=f"No baseline found for unit '{unit_id}'.")
        
        return {
            "unit_id": baseline.unit_id,
            "move_in_video_summary": baseline.move_in_video_summary,
            "last_audit_date": baseline.last_audit_date.isoformat() if baseline.last_audit_date else None,
            "created_at": baseline.created_at.isoformat() if baseline.created_at else None,
            "updated_at": baseline.updated_at.isoformat() if baseline.updated_at else None
        }
    finally:
        db.close()


@app.get("/baselines")
async def list_baselines(admin_key: str = Query(None)):
    """List all unit baselines."""
    if admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized.")
    
    db = get_db()
    try:
        baselines = db.query(UnitBaseline).order_by(UnitBaseline.last_audit_date.desc()).all()
        
        return {
            "status": "success",
            "count": len(baselines),
            "baselines": [
                {
                    "unit_id": b.unit_id,
                    "last_audit_date": b.last_audit_date.isoformat() if b.last_audit_date else None,
                    "has_summary": bool(b.move_in_video_summary)
                }
                for b in baselines
            ]
        }
    finally:
        db.close()


# ==================== LEGACY SUPPORT (deprecated) ====================

@app.post("/leads")
async def create_lead_legacy(lead: TicketCreate):
    """
    DEPRECATED: Use /tickets instead.
    Maintained for backward compatibility.
    """
    return await create_ticket(lead)


@app.get("/leads")
async def get_leads_legacy(admin_key: str = Query(None)):
    """
    DEPRECATED: Use /tickets instead.
    Maintained for backward compatibility.
    """
    result = await get_tickets(admin_key=admin_key)
    # Rename 'tickets' to 'leads' for backward compatibility
    if "tickets" in result:
        result["leads"] = result.pop("tickets")
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
