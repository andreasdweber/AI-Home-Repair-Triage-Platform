"""
Fix-It AI - Home Repair Triage Backend
FastAPI backend with Google Gemini AI integration for image analysis
"""

import os
import json
import base64
import sqlite3
from datetime import datetime
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_PATH = "leads.db"

# Admin key for accessing leads (MVP security)
ADMIN_KEY = "secret123"


def init_db():
    """Initialize the SQLite database and create tables if they don't exist."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            postal_code TEXT NOT NULL,
            issue_category TEXT,
            issue_title TEXT,
            issue_description TEXT,
            ai_estimated_cost TEXT,
            ai_severity TEXT,
            ai_recommended_action TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


# Pydantic model for lead submission
class LeadCreate(BaseModel):
    name: str
    phone: str
    postal_code: str
    issue_category: Optional[str] = None
    issue_title: Optional[str] = None
    issue_description: Optional[str] = None
    ai_estimated_cost: Optional[str] = None
    ai_severity: Optional[str] = None
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

# Configure Gemini API
# Using gemini-2.0-flash - can easily swap to newer models later
GEMINI_MODEL = "gemini-2.0-flash"

def get_gemini_client():
    """Initialize and return the Gemini client."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY not configured. Please set it in the .env file."
        )
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(GEMINI_MODEL)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Fix-It AI Backend is running"}


@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "model": GEMINI_MODEL,
        "api_configured": bool(os.getenv("GEMINI_API_KEY"))
    }


@app.post("/analyze")
async def analyze_image(
    image: UploadFile = File(None),
    description: str = Form(""),
    category: str = Form("")
):
    """
    Analyze a home repair issue using Google Gemini AI.
    
    Accepts an optional image upload along with description and category,
    and returns a JSON diagnosis with:
    - issue_title: Brief description of the issue
    - severity: Low/Medium/High
    - estimated_cost_range: Estimated repair cost
    - trade_category: Type of professional needed
    - diagnosis_explanation: Detailed explanation of the issue
    - recommended_action: Immediate next step
    - safety_warning: Any safety concerns
    """
    
    # Check if we have at least some input to analyze
    if not image and not description and not category:
        raise HTTPException(
            status_code=400,
            detail="Please provide an image, description, or category to analyze."
        )
    
    # Validate file type if image is provided
    image_data = None
    image_mime_type = None
    if image and image.filename:
        allowed_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
        if image.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}"
            )
        image_data = await image.read()
        image_mime_type = image.content_type
    
    try:
        # Get Gemini client
        model = get_gemini_client()
        
        # Build user context from provided inputs
        user_context = ""
        if category or description:
            user_context = "User Context:\n"
            if category:
                user_context += f"- Category: {category}\n"
            if description:
                user_context += f"- Description: {description}\n"
            user_context += "\n"
        
        # Determine analysis mode
        has_image = image_data is not None
        analysis_mode = "image and description" if has_image else "description only (no image provided)"
        
        # Prepare the AI prompt with user context
        prompt = f"""{user_context}Task: You are a Master Tradesperson with decades of experience in home repair and maintenance. 
Analyze this home repair issue carefully based on {analysis_mode}.

Return your analysis as a strict JSON response with exactly these fields:
{{
    "issue_title": "A brief, clear title describing the issue (string)",
    "severity": "Low, Medium, or High (string)",
    "estimated_cost_range": "Estimated repair cost range in USD, e.g., '$50-$150' (string)",
    "trade_category": "The type of professional needed, e.g., Electrical, Plumbing, HVAC, Roofing, General Contractor, Carpentry, Painting, Appliance Repair (string)",
    "diagnosis_explanation": "2-3 sentences explaining exactly what is wrong and why this issue occurs (string)",
    "recommended_action": "The immediate next step the homeowner should take, e.g., 'Turn off water supply' or 'Do not use the outlet until inspected' (string)",
    "safety_warning": "Any immediate safety concerns or precautions, or 'None' if no safety issues (string)"
}}

Important guidelines:
- Be specific and practical in your assessment
- Consider both DIY potential and professional requirements
- Highlight any urgent safety concerns prominently
- Provide realistic cost estimates based on current market rates
- Give actionable, clear recommended actions
- Use any user-provided context (category/description) to improve your analysis accuracy
- If analyzing without an image, base your diagnosis on the description provided

Return ONLY the JSON object, no additional text or markdown formatting."""

        # Generate response from Gemini
        if has_image:
            # Create the image part for Gemini
            image_part = {
                "mime_type": image_mime_type,
                "data": base64.b64encode(image_data).decode("utf-8")
            }
            response = model.generate_content([prompt, image_part])
        else:
            # Text-only analysis
            response = model.generate_content(prompt)
        
        # Parse the response
        response_text = response.text.strip()
        
        # Clean up the response if it contains markdown code blocks
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        # Parse JSON response
        try:
            analysis_result = json.loads(response_text)
        except json.JSONDecodeError:
            # If JSON parsing fails, create a structured response from the text
            analysis_result = {
                "issue_title": "Analysis Complete",
                "severity": "Medium",
                "estimated_cost_range": "Varies",
                "trade_category": "General Contractor",
                "diagnosis_explanation": response_text[:500] if response_text else "Unable to parse detailed analysis",
                "recommended_action": "Consult a professional for assessment",
                "safety_warning": "None"
            }
        
        # Validate required fields
        required_fields = ["issue_title", "severity", "estimated_cost_range", "trade_category", "diagnosis_explanation", "recommended_action", "safety_warning"]
        for field in required_fields:
            if field not in analysis_result:
                analysis_result[field] = "Not determined"
        
        return {
            "success": True,
            "analysis": analysis_result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing issue: {str(e)}"
        )


# ==================== LEAD MANAGEMENT ENDPOINTS ====================

@app.post("/leads")
async def create_lead(lead: LeadCreate):
    """
    Save a new lead to the database.
    Accepts lead information along with AI diagnosis details.
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO leads (
                name, phone, postal_code, issue_category, issue_title,
                issue_description, ai_estimated_cost, ai_severity, ai_recommended_action
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            lead.name,
            lead.phone,
            lead.postal_code,
            lead.issue_category,
            lead.issue_title,
            lead.issue_description,
            lead.ai_estimated_cost,
            lead.ai_severity,
            lead.ai_recommended_action
        ))
        conn.commit()
        lead_id = cursor.lastrowid
        conn.close()
        
        return {
            "status": "success",
            "message": "Lead saved successfully",
            "lead_id": lead_id
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error saving lead: {str(e)}"
        )


@app.get("/leads")
async def get_leads(admin_key: str = Query(None)):
    """
    Retrieve all leads from the database (Admin only).
    Requires admin_key query parameter for authentication.
    """
    # Simple MVP authentication
    if admin_key != ADMIN_KEY:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized. Invalid or missing admin_key."
        )
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM leads ORDER BY timestamp DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        
        # Convert rows to list of dictionaries
        leads = [dict(row) for row in rows]
        
        return {
            "status": "success",
            "count": len(leads),
            "leads": leads
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving leads: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
