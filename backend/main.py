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
    """Initialize database - simple create_all (columns already exist or will be added)."""
    try:
        Base.metadata.create_all(bind=engine)
        print("Database initialized")
    except Exception as e:
        print(f"Database init warning (likely OK): {e}")


@app.get("/")
async def health():
    """Health check."""
    return {"status": "ok", "version": "2.0.0"}


@app.get("/migrate-once")
async def migrate_once():
    """One-time migration endpoint - adds new columns if missing."""
    from sqlalchemy import text
    results = []
    try:
        with engine.connect() as conn:
            migrations = [
                "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS contact_info JSON",
                "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS category VARCHAR",
                "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS summary TEXT", 
                "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS priority VARCHAR",
                "ALTER TABLE unit_baselines ADD COLUMN IF NOT EXISTS baseline_json JSON",
                "ALTER TABLE unit_baselines ADD COLUMN IF NOT EXISTS last_updated TIMESTAMP",
            ]
            for sql in migrations:
                try:
                    conn.execute(text(sql))
                    results.append(f"OK: {sql[:50]}...")
                except Exception as e:
                    results.append(f"Skip: {str(e)[:50]}...")
            conn.commit()
        return {"status": "success", "results": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}


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
            
            # Store filled_slots as contact_info for backward compatibility
            filled_slots = result.get("filled_slots", {})
            ticket.contact_info = filled_slots
            
            if result.get("risk"):
                ticket.risk_level = result["risk"]
                ticket.priority = result["risk"]
            
            if result.get("category"):
                ticket.category = result["category"]
            
            # Handle CREATE_TICKET action - save all ticket_data fields
            if result.get("action") == "CREATE_TICKET":
                ticket.status = TicketStatus.DISPATCHED.value
                ticket_data = result.get("ticket_data", {})
                
                # Save tenant info
                if ticket_data.get("tenant_name"):
                    ticket.name = ticket_data["tenant_name"]
                if ticket_data.get("unit"):
                    ticket.unit_id = ticket_data["unit"]
                if ticket_data.get("contact"):
                    ticket.phone = ticket_data["contact"]
                
                # Save issue details
                if ticket_data.get("issue"):
                    ticket.issue_title = ticket_data["issue"]
                if ticket_data.get("severity"):
                    ticket.issue_description = f"Severity: {ticket_data['severity']}"
                    if ticket_data.get("location"):
                        ticket.issue_description += f" | Location: {ticket_data['location']}"
                
                # Generate summary for vendor ("Golden Ticket")
                summary_parts = []
                if ticket_data.get("issue"):
                    summary_parts.append(f"Issue: {ticket_data['issue']}")
                if ticket_data.get("severity"):
                    summary_parts.append(f"Severity: {ticket_data['severity']}")
                if ticket_data.get("location"):
                    summary_parts.append(f"Location: {ticket_data['location']}")
                if ticket_data.get("access"):
                    summary_parts.append(f"Access: {ticket_data['access']}")
                if ticket_data.get("contact"):
                    summary_parts.append(f"Contact: {ticket_data['contact']}")
                if ticket_data.get("unit"):
                    summary_parts.append(f"Unit: {ticket_data['unit']}")
                ticket.summary = " | ".join(summary_parts)
                
            elif result.get("action") == "CONFIRM":
                # Awaiting user confirmation - don't create ticket yet
                ticket.status = TicketStatus.OPEN.value
            elif result.get("action") == "Escalate":
                ticket.status = TicketStatus.ESCALATED.value
                if result.get("contact_info", {}).get("phone"):
                    ticket.phone = result["contact_info"]["phone"]
    
    response_data = {
        "session_id": str(ticket_id),
        "response": result.get("text"),
        "risk": result.get("risk"),
        "action": result.get("action"),
        "category": result.get("category"),
        "escalation_mode": result.get("escalation_mode", False),
        "contact_info": result.get("contact_info", {}),
        "filled_slots": result.get("filled_slots", {}),
        "missing_info": result.get("missing_info", []),
        "request_photo": result.get("request_photo", False),
        "awaiting_confirmation": result.get("awaiting_confirmation", False),
        "history": history
    }
    
    # Add ticket details if dispatched
    if result.get("action") == "CREATE_TICKET":
        response_data["ticket_id"] = ticket_id
        response_data["ticket_summary"] = result.get("ticket_summary", "")
        response_data["ticket_data"] = result.get("ticket_data", {})
    
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
    
    # Normalize unit_id to uppercase for consistent matching
    unit_id = unit_id.strip().upper()
    
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
# ADMIN ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

ADMIN_KEY = os.getenv("ADMIN_KEY", "demo-admin-key")

@app.get("/admin/verify")
async def admin_verify(key: str = ""):
    """Verify admin key."""
    if key == ADMIN_KEY:
        return {"valid": True}
    raise HTTPException(401, "Invalid admin key")


@app.get("/admin/tickets")
async def admin_get_tickets():
    """Get all tickets with stats for admin dashboard."""
    with get_db() as db:
        tickets = db.query(Ticket).order_by(Ticket.id.desc()).all()
        
        # Calculate stats
        total = len(tickets)
        open_count = sum(1 for t in tickets if t.status in [None, 'Open', TicketStatus.OPEN.value])
        dispatched = sum(1 for t in tickets if t.status == TicketStatus.DISPATCHED.value)
        emergency = sum(1 for t in tickets if t.priority == 'Red' or t.risk_level == 'Red')
        
        # Serialize tickets
        tickets_data = []
        for t in tickets:
            tickets_data.append({
                "id": t.id,
                "name": t.name,
                "phone": t.phone,
                "unit_id": t.unit_id,
                "category": t.category,
                "issue_title": t.issue_title,
                "issue_description": t.issue_description,
                "status": t.status,
                "priority": t.priority or t.risk_level,
                "summary": t.summary,
                "contact_info": t.contact_info,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None
            })
        
        return {
            "tickets": tickets_data,
            "stats": {
                "total": total,
                "open": open_count,
                "dispatched": dispatched,
                "emergency": emergency
            }
        }


@app.get("/admin/tickets/{ticket_id}")
async def admin_get_ticket(ticket_id: int):
    """Get single ticket with full conversation history."""
    with get_db() as db:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(404, "Ticket not found")
        
        return {
            "id": ticket.id,
            "name": ticket.name,
            "phone": ticket.phone,
            "postal_code": ticket.postal_code,
            "unit_id": ticket.unit_id,
            "category": ticket.category,
            "issue_title": ticket.issue_title,
            "issue_description": ticket.issue_description,
            "status": ticket.status,
            "priority": ticket.priority or ticket.risk_level,
            "summary": ticket.summary,
            "contact_info": ticket.contact_info,
            "conversation_history": ticket.conversation_history,
            "ai_diagnosis": ticket.ai_diagnosis,
            "ai_recommended_action": ticket.ai_recommended_action,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
            "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None
        }


@app.get("/admin/units")
async def admin_get_units():
    """Get all units with baselines."""
    with get_db() as db:
        units = db.query(UnitBaseline).all()
        
        units_data = []
        for u in units:
            units_data.append({
                "id": u.id,
                "unit_id": u.unit_id,
                "has_baseline": bool(u.move_in_video_summary or u.baseline_json),
                "summary": u.move_in_video_summary,
                "items_count": len(u.baseline_json) if u.baseline_json else 0,
                "last_updated": u.last_updated.isoformat() if u.last_updated else None
            })
        
        return {"units": units_data}


@app.patch("/admin/tickets/{ticket_id}")
async def admin_update_ticket(ticket_id: int, status: str = None, priority: str = None):
    """Update ticket status or priority."""
    with get_db() as db:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(404, "Ticket not found")
        
        if status:
            ticket.status = status
        if priority:
            ticket.priority = priority
            ticket.risk_level = priority
        
        return {"success": True, "ticket_id": ticket_id}


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
