"""
Fix-It AI - Backend API
FastAPI backend with AI triage and video audit endpoints
"""

import os
import json
from datetime import datetime
from contextlib import contextmanager
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, Ticket, UnitBaseline, TicketStatus
from agent import MaintenanceAgent

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# DATABASE SETUP
# ─────────────────────────────────────────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Production: PostgreSQL (fix Render's postgres:// URL)
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(DATABASE_URL)
else:
    # Local: SQLite
    engine = create_engine("sqlite:///./fixit.db", connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db():
    """Database session context manager."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# FASTAPI APP
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(title="Fix-It AI", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)


@app.get("/")
async def health():
    """Health check."""
    return {"status": "ok", "version": "2.0.0"}


# ─────────────────────────────────────────────────────────────────────────────
# POST /chat - Conversational Triage with Smart Dispatch
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/chat")
async def chat(
    session_id: str = Form(...),
    text: str = Form(""),
    file: UploadFile = File(None),
    escalation_mode: str = Form("false"),
    contact_info: str = Form("{}")
):
    """
    Conversational chat endpoint for maintenance triage with Smart Dispatch.
    
    Features:
    - "Give Up" detection triggers escalation mode
    - Escalation mode collects phone/access info
    - CREATE_TICKET action generates "Golden Ticket" summary
    
    Returns:
    - response, risk, action, category
    - escalation_mode: bool (if in escalation flow)
    - contact_info: collected info
    - ticket_id: if CREATE_TICKET action
    - ticket_summary: "Golden Ticket" summary for vendor
    """
    
    # Parse contact_info from JSON string
    try:
        collected_info = json.loads(contact_info) if contact_info else {}
    except json.JSONDecodeError:
        collected_info = {}
    
    # Get or create ticket for this session
    ticket_id = None
    if session_id and session_id.isdigit():
        ticket_id = int(session_id)
    
    with get_db() as db:
        ticket = None
        if ticket_id:
            ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        
        if not ticket:
            ticket = Ticket(
                name="Widget User",
                phone="N/A",
                postal_code="N/A",
                conversation_history=[]
            )
            db.add(ticket)
            db.flush()
            ticket_id = ticket.id
        
        history = ticket.conversation_history or []
        # Get escalation state from ticket if stored
        if ticket.contact_info:
            collected_info = {**ticket.contact_info, **collected_info}
    
    # Add user message to history
    if text:
        history.append({"role": "user", "content": text})
    
    # Process image if provided
    image_data = None
    image_mime_type = None
    if file and file.filename:
        allowed = ["image/jpeg", "image/png", "image/webp", "image/gif"]
        if file.content_type not in allowed:
            raise HTTPException(400, f"Invalid image type. Allowed: {allowed}")
        
        image_data = await file.read()
        image_mime_type = file.content_type
        history.append({"role": "user", "content": "[Image uploaded]"})
    
    # Call agent with escalation context
    # Convert escalation_mode string to bool
    is_escalation = escalation_mode.lower() in ("true", "1", "yes")
    
    try:
        agent = MaintenanceAgent()
        result = agent.triage_with_image_bytes(
            history=history,
            image_data=image_data,
            image_mime_type=image_mime_type,
            escalation_mode=is_escalation,
            collected_info=collected_info
        )
    except Exception as e:
        raise HTTPException(500, f"AI error: {str(e)}")
    
    # Add assistant response to history
    if result.get("text"):
        history.append({"role": "assistant", "content": result["text"]})
    
    # Save to DB
    with get_db() as db:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if ticket:
            ticket.conversation_history = history
            ticket.contact_info = result.get("contact_info", {})
            
            if result.get("risk"):
                ticket.risk_level = result["risk"]
                ticket.priority = result["risk"]
            
            if result.get("category"):
                ticket.category = result["category"]
            
            # Handle CREATE_TICKET action (dispatch)
            if result.get("action") == "CREATE_TICKET":
                ticket.status = TicketStatus.DISPATCHED.value
                ticket.summary = result.get("ticket_summary", "")
                if result.get("contact_info", {}).get("phone"):
                    ticket.phone = result["contact_info"]["phone"]
            elif result.get("action") == "Escalate":
                ticket.status = TicketStatus.ESCALATED.value
    
    response_data = {
        "session_id": str(ticket_id),
        "response": result.get("text"),
        "risk": result.get("risk"),
        "action": result.get("action"),
        "category": result.get("category"),
        "escalation_mode": result.get("escalation_mode", False),
        "contact_info": result.get("contact_info", {}),
        "history": history
    }
    
    # Add ticket details if dispatched
    if result.get("action") == "CREATE_TICKET":
        response_data["ticket_id"] = ticket_id
        response_data["ticket_summary"] = result.get("ticket_summary", "")
    
    return response_data


# ─────────────────────────────────────────────────────────────────────────────
# POST /audit - Video Audit (Move-in / Move-out)
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/audit")
async def audit(
    unit_id: str = Form(...),
    mode: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Video audit endpoint for move-in/move-out inspections.
    
    mode='move-in':
        - Calls agent.audit_video() to generate baseline
        - Saves summary to UnitBaseline table
        
    mode='move-out':
        - Fetches baseline from UnitBaseline
        - Calls agent.audit_video() with baseline for comparison
        - Returns new damages report
    """
    
    # Validate mode
    if mode not in ["move-in", "move-out"]:
        raise HTTPException(400, "mode must be 'move-in' or 'move-out'")
    
    # Validate video type
    allowed = ["video/mp4", "video/quicktime", "video/x-msvideo", "video/webm", "video/mpeg"]
    if file.content_type not in allowed:
        raise HTTPException(400, f"Invalid video type. Allowed: {allowed}")
    
    video_data = await file.read()
    video_mime_type = file.content_type
    
    agent = MaintenanceAgent()
    
    # ── MOVE-IN ──
    if mode == "move-in":
        try:
            result = agent.audit_video_bytes(
                video_data=video_data,
                video_mime_type=video_mime_type,
                mode="move-in"
            )
        except Exception as e:
            raise HTTPException(500, f"AI error: {str(e)}")
        
        if result.get("success"):
            with get_db() as db:
                existing = db.query(UnitBaseline).filter(UnitBaseline.unit_id == unit_id).first()
                
                if existing:
                    existing.move_in_video_summary = result.get("summary", "")
                    existing.baseline_json = result.get("items", [])
                    existing.last_audit_date = datetime.utcnow()
                    existing.last_updated = datetime.utcnow()
                else:
                    baseline = UnitBaseline(
                        unit_id=unit_id,
                        move_in_video_summary=result.get("summary", ""),
                        baseline_json=result.get("items", []),
                        last_audit_date=datetime.utcnow()
                    )
                    db.add(baseline)
            
            result["saved"] = True
        
        return result
    
    # ── MOVE-OUT ──
    else:
        # Fetch baseline
        with get_db() as db:
            baseline = db.query(UnitBaseline).filter(UnitBaseline.unit_id == unit_id).first()
            baseline_text = baseline.move_in_video_summary if baseline else None
            baseline_json = baseline.baseline_json if baseline else None
        
        if not baseline_text and not baseline_json:
            raise HTTPException(404, f"No move-in baseline found for unit '{unit_id}'")
        
        try:
            result = agent.audit_video_bytes(
                video_data=video_data,
                video_mime_type=video_mime_type,
                mode="move-out",
                baseline_text=baseline_text,
                baseline_json=baseline_json
            )
        except Exception as e:
            raise HTTPException(500, f"AI error: {str(e)}")
        
        return result


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
