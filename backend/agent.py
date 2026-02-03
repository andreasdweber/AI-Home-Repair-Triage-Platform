"""
Fix-It AI - Maintenance Agent
AI-powered maintenance triage and video audit capabilities using Google Gemini 2.0 Flash

Features:
- Smart triage with "Give Up" detection for escalation
- Escalation mode to collect contact/access info
- "Golden Ticket" vendor summary generation
- Video audit with JSON-only output for damages
"""

import os
import json
import tempfile
import time
import re
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# Lazy load genai to reduce startup memory
genai = None

def _get_genai():
    """Lazy load Google Generative AI module."""
    global genai
    if genai is None:
        import google.generativeai as _genai
        genai = _genai
    return genai

load_dotenv()

# Gemini model configuration
GEMINI_MODEL = "gemini-2.0-flash"

# Phrases that trigger escalation mode ("Give Up" detector)
GIVE_UP_PHRASES = [
    "didn't work", "didnt work", "doesn't work", "doesnt work",
    "not working", "still broken", "still not",
    "call a pro", "call someone", "need a professional", "need professional",
    "send someone", "get help", "give up", "i give up",
    "forget it", "just fix it", "can't fix", "cant fix",
    "too hard", "too complicated", "need a plumber", "need an electrician",
    "need a technician", "escalate", "talk to human", "real person"
]

# System prompt for maintenance triage - Slot-Filling State Machine
TRIAGE_SYSTEM_PROMPT = """You are Fix-It AI, a professional property management assistant. Your goal is NOT just to give advice, but to gather specific information to create a complete work order.

The required "Slots" you must fill are:
- TENANT_NAME: The tenant's name (e.g., "John Smith")
- UNIT: Unit number or address (e.g., "Unit 4B", "123 Main St Apt 2")
- ISSUE: What is broken? (e.g., "Leaking toilet hose")
- SEVERITY: Is it happening right now? Is it damaging property? (e.g., "Slow drip," "Active spray")
- LOCATION: Precise location within the unit? (e.g., "Behind toilet in master bathroom")
- ACCESS: Instructions for property entry? (e.g., "Use master key," "Schedule appointment")
- CONTACT: Phone number or email to reach the tenant (e.g., "555-123-4567")

Your Logic Loop (Execute in order):

1. Analyze Risk: If the issue indicates fire, gas, or massive flooding → Return Action EMERGENCY immediately.

2. Check Slots: Look at the conversation history. Which of the 7 slots are still missing or vague?

3. Photo Request: For visual issues (leaks, damage, mold, pests, broken items), if no image has been uploaded, ask the user to upload a photo. Set "request_photo": true.

4. Formulate Response:
   - If slots are missing: Ask ONE clear, direct question to fill the most critical missing slot. Do not give generic advice yet.
   - Priority order: TENANT_NAME → UNIT → ISSUE → SEVERITY → LOCATION → ACCESS → CONTACT
   - CONTACT must be an actual phone number or email, not just "contact me"
   - If all 7 slots are filled with specific values: Return Action CONFIRM (show summary for user confirmation)

5. Confirmation: When action is CONFIRM, show a summary of all collected information and ask "Is this information correct?" 
   - If user confirms (yes, correct, looks good, etc.) → Return Action CREATE_TICKET
   - If user says no or wants to change something → Return Action QUESTION to fix the slot

Output Format (JSON Only):
{
    "text": "The question you are asking the user...",
    "risk": "Green" | "Yellow" | "Red",
    "action": "QUESTION" | "CONFIRM" | "CREATE_TICKET" | "EMERGENCY",
    "request_photo": true | false,
    "missing_info": ["Contact", "Access", "Unit", "Tenant_Name"],
    "category": "Plumbing" | "Electrical" | "HVAC" | "Appliance" | "Structural" | "Pest Control" | "Locksmith" | "Other",
    "filled_slots": {
        "tenant_name": "extracted tenant name or null",
        "unit": "extracted unit/address or null",
        "issue": "extracted issue or null",
        "severity": "extracted severity or null",
        "location": "extracted location or null",
        "access": "extracted access info or null",
        "contact": "extracted phone/email or null"
    }
}

IMPORTANT RULES:
- NEVER give generic advice when slots are missing. Your job is to ASK QUESTIONS.
- Ask only ONE question at a time to fill the most critical missing slot.
- Prioritize Severity questions for safety assessment.
- CONTACT slot requires an actual phone number or email address - "call me" or "contact me" is NOT sufficient.
- For visual issues without a photo, set request_photo to true and ask the user to upload one.
- When ALL 7 slots are filled, return CONFIRM action with a summary for user to verify.
- Only return CREATE_TICKET after user confirms the summary is correct.
- Return EMERGENCY immediately for fire, gas leaks, or major flooding."""

# System prompt for escalation mode
ESCALATION_SYSTEM_PROMPT = """You are a helpful assistant collecting information to dispatch a maintenance professional.
Be brief and friendly. Only ask for the specific information needed."""


class MaintenanceAgent:
    """
    AI agent for maintenance issue triage and video auditing.
    Uses Google Gemini 2.0 Flash for multi-modal analysis.
    
    Features:
    - "Give Up" detection to trigger escalation
    - Escalation mode to collect contact/access info
    - Vendor summary ("Golden Ticket") generation
    - JSON-only video audit output
    """
    
    def __init__(self):
        """Initialize the agent with Gemini API configuration."""
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not configured. Please set it in the .env file.")
        
        self._model = None
        self._escalation_model = None
    
    @property
    def model(self):
        """Lazy-load the main Gemini model."""
        if self._model is None:
            genai = _get_genai()
            genai.configure(api_key=self.api_key)
            self._model = genai.GenerativeModel(
                model_name=GEMINI_MODEL,
                system_instruction=TRIAGE_SYSTEM_PROMPT
            )
        return self._model
    
    @property
    def escalation_model(self):
        """Lazy-load the escalation Gemini model."""
        if self._escalation_model is None:
            genai = _get_genai()
            genai.configure(api_key=self.api_key)
            self._escalation_model = genai.GenerativeModel(
                model_name=GEMINI_MODEL,
                system_instruction=ESCALATION_SYSTEM_PROMPT
            )
        return self._escalation_model
    
    # ─────────────────────────────────────────────────────────────────────────────
    # GIVE UP DETECTION & ESCALATION
    # ─────────────────────────────────────────────────────────────────────────────
    
    def _detect_give_up(self, text: str) -> bool:
        """Check if user message contains 'give up' phrases indicating they want escalation."""
        if not text:
            return False
        text_lower = text.lower()
        return any(phrase in text_lower for phrase in GIVE_UP_PHRASES)
    
    def _detect_escalation_info(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Check conversation history to see what escalation info has been collected.
        Returns: {"has_phone": bool, "has_access": bool, "phone": str|None, "access": str|None}
        """
        collected = {"has_phone": False, "has_access": False, "phone": None, "access": None}
        
        # Look through history for patterns
        full_text = " ".join([m.get("content", "") for m in history if m.get("role") == "user"])
        
        # Phone pattern (various formats)
        phone_match = re.search(r'(\d{3}[-.\s]?\d{3}[-.\s]?\d{4}|\(\d{3}\)\s?\d{3}[-.\s]?\d{4})', full_text)
        if phone_match:
            collected["has_phone"] = True
            collected["phone"] = phone_match.group(1)
        
        # Access code patterns
        access_patterns = [
            r'(?:key|code|access|gate|door)\s*(?:is|:)?\s*[#]?(\w+[-\w]*)',
            r'(?:available|availability|free)\s*(?:is|:)?\s*(.+?)(?:\.|$)',
        ]
        for pattern in access_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                collected["has_access"] = True
                collected["access"] = match.group(1).strip()
                break
        
        return collected
    
    def _generate_vendor_summary(
        self,
        history: List[Dict[str, Any]],
        contact_info: Dict[str, Any]
    ) -> str:
        """
        Generate a concise "Golden Ticket" summary for the vendor.
        Format: "Issue: X. DIY Attempted: Y. Parts: Z. Access: W. Contact: P"
        """
        conversation_text = self._format_history(history)
        
        prompt = f"""Based on this conversation, create a BRIEF vendor dispatch summary.

CONVERSATION:
{conversation_text}

CONTACT INFO COLLECTED:
Phone: {contact_info.get('phone', 'Not provided')}
Access/Availability: {contact_info.get('access', 'Not provided')}

Return ONLY valid JSON:
{{
    "issue": "Brief description of the problem",
    "category": "Plumbing|Electrical|HVAC|Appliance|Structural|Pest Control|Locksmith|Other",
    "diy_attempted": "What the tenant tried",
    "likely_parts": "Parts that may be needed",
    "summary": "One-line summary for vendor: Issue: X. DIY: Y. Parts: Z."
}}"""
        
        try:
            response = self.model.generate_content(prompt)
            result = self._parse_json_response(response.text)
            
            # Build the golden ticket summary
            summary = result.get("summary", "")
            if not summary:
                summary = f"Issue: {result.get('issue', 'Maintenance needed')}. "
                if result.get('diy_attempted'):
                    summary += f"DIY: {result['diy_attempted']}. "
                if result.get('likely_parts'):
                    summary += f"Parts: {result['likely_parts']}. "
            
            # Append contact info
            if contact_info.get('access'):
                summary += f"Access: {contact_info['access']}. "
            if contact_info.get('phone'):
                summary += f"Contact: {contact_info['phone']}"
            
            return summary.strip(), result.get("category", "Other")
        except Exception:
            return "Maintenance issue - tenant requested professional help.", "Other"
    
    # ─────────────────────────────────────────────────────────────────────────────
    # TRIAGE METHODS
    # ─────────────────────────────────────────────────────────────────────────────
    
    def triage(
        self,
        history: List[Dict[str, Any]],
        image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Triage a maintenance issue using conversation history and optional image.
        Uses Slot-Filling State Machine logic to gather complete information.
        
        Args:
            history: List of conversation messages [{"role": "user"|"assistant", "content": "..."}]
            image_path: Optional path to an image file
        
        Returns:
            Dict with: {"text": "response", "risk": "Green|Yellow|Red", 
                       "action": "QUESTION|CREATE_TICKET|EMERGENCY",
                       "missing_info": [...], "filled_slots": {...}}
        """
        prompt_parts = []
        
        # Build prompt from conversation history
        conversation_text = self._format_history(history)
        prompt_parts.append(f"""Analyze this maintenance conversation and determine what information is still needed.

CONVERSATION:
{conversation_text}

IMAGE UPLOADED: {"Yes" if image_path else "No"}

Analyze the conversation and:
1. Check for EMERGENCY conditions (fire, gas, major flooding) → action: EMERGENCY
2. Extract any filled slots (tenant_name, unit, issue, severity, location, access, contact)
3. For visual issues without a photo, set request_photo: true
4. If slots are missing → action: QUESTION (ask ONE question for most critical missing slot)
5. If all 7 slots are filled → action: CONFIRM (show summary for user to verify)
6. If user confirmed the summary → action: CREATE_TICKET

IMPORTANT: CONTACT must be an actual phone number or email. "Contact me" or "call me" is NOT valid.

Return ONLY valid JSON:
{{
    "text": "Your response to the user",
    "risk": "Green|Yellow|Red",
    "action": "QUESTION|CONFIRM|CREATE_TICKET|EMERGENCY",
    "request_photo": false,
    "missing_info": ["list of missing slots"],
    "category": "Plumbing|Electrical|HVAC|Appliance|Structural|Pest Control|Locksmith|Other",
    "filled_slots": {{
        "tenant_name": "extracted name or null",
        "unit": "extracted unit/address or null",
        "issue": "extracted issue or null",
        "severity": "extracted severity or null",
        "location": "extracted location or null",
        "access": "extracted access info or null",
        "contact": "extracted phone/email or null"
    }}
}}""")
        
        # Add image if provided
        if image_path and os.path.exists(image_path):
            try:
                prompt_parts.append(self._load_image(image_path))
            except Exception:
                pass
        
        try:
            response = self.model.generate_content(prompt_parts)
            result = self._parse_json_response(response.text)
            
            action = result.get("action", "QUESTION")
            missing_info = result.get("missing_info", [])
            filled_slots = result.get("filled_slots", {})
            
            response_data = {
                "text": result.get("text", "Could you provide more details about the issue?"),
                "risk": result.get("risk", "Yellow"),
                "action": action,
                "category": result.get("category", "Other"),
                "missing_info": missing_info,
                "filled_slots": filled_slots,
                "request_photo": result.get("request_photo", False)
            }
            
            # Handle CREATE_TICKET action - prepare for database save
            if action == "CREATE_TICKET":
                response_data["ready_for_ticket"] = True
                response_data["ticket_data"] = {
                    "tenant_name": filled_slots.get("tenant_name"),
                    "unit": filled_slots.get("unit"),
                    "issue": filled_slots.get("issue"),
                    "severity": filled_slots.get("severity"),
                    "location": filled_slots.get("location"),
                    "access": filled_slots.get("access"),
                    "contact": filled_slots.get("contact"),
                    "category": result.get("category", "Other"),
                    "risk": result.get("risk", "Yellow")
                }
            
            # Handle CONFIRM action - user needs to verify before ticket creation
            if action == "CONFIRM":
                response_data["awaiting_confirmation"] = True
                response_data["ticket_data"] = {
                    "tenant_name": filled_slots.get("tenant_name"),
                    "unit": filled_slots.get("unit"),
                    "issue": filled_slots.get("issue"),
                    "severity": filled_slots.get("severity"),
                    "location": filled_slots.get("location"),
                    "access": filled_slots.get("access"),
                    "contact": filled_slots.get("contact"),
                    "category": result.get("category", "Other"),
                    "risk": result.get("risk", "Yellow")
                }
            
            # Handle EMERGENCY action
            if action == "EMERGENCY":
                response_data["is_emergency"] = True
                response_data["text"] = f"🚨 EMERGENCY: {result.get('text', 'This is an emergency situation. Please evacuate if necessary and call emergency services.')}"
            
            return response_data
            
        except Exception as e:
            return {
                "text": "I encountered an issue. Please try again.",
                "risk": "Yellow",
                "action": "QUESTION",
                "category": "Other",
                "missing_info": ["Tenant_Name", "Unit", "Issue", "Severity", "Location", "Access", "Contact"],
                "filled_slots": {},
                "request_photo": False,
                "error": str(e)
            }
    
    def triage_with_image_bytes(
        self,
        history: List[Dict[str, Any]],
        image_data: Optional[bytes] = None,
        image_mime_type: str = "image/jpeg",
        escalation_mode: bool = False,
        collected_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Triage using image bytes directly (for API uploads).
        
        Includes "Give Up" detection and escalation flow:
        1. If user says "didn't work" / "call a pro" → switch to escalation mode
        2. In escalation mode → ask for phone and access info
        3. Once info collected → generate vendor summary and return CREATE_TICKET
        
        Args:
            history: Conversation history
            image_data: Raw image bytes
            image_mime_type: MIME type of image
            escalation_mode: Whether we're already in escalation mode
            collected_info: Previously collected contact/access info
        
        Returns:
            Dict with: {"text": "...", "risk": "...", "action": "...", "category": "...", 
                       "escalation_mode": bool, "contact_info": {...}, "ticket_summary": "..."}
        """
        collected_info = collected_info or {}
        
        # Get latest user message
        latest_user_msg = ""
        for msg in reversed(history):
            if msg.get("role") == "user":
                latest_user_msg = msg.get("content", "")
                break
        
        # Check for "Give Up" trigger
        if not escalation_mode and self._detect_give_up(latest_user_msg):
            escalation_mode = True
        
        # ── ESCALATION MODE ──
        if escalation_mode:
            # Check what info we've collected
            detected = self._detect_escalation_info(history)
            
            # Merge with previously collected
            if detected["has_phone"]:
                collected_info["phone"] = detected["phone"]
            if detected["has_access"]:
                collected_info["access"] = detected["access"]
            
            has_phone = bool(collected_info.get("phone"))
            has_access = bool(collected_info.get("access"))
            
            # All info collected → CREATE TICKET
            if has_phone and has_access:
                summary, category = self._generate_vendor_summary(history, collected_info)
                return {
                    "text": f"✅ Got it! I'm creating a service ticket now.\n\n📋 **Ticket Summary:**\n{summary}\n\nA professional will contact you soon.",
                    "risk": "Yellow",
                    "action": "CREATE_TICKET",
                    "category": category,
                    "escalation_mode": False,
                    "contact_info": collected_info,
                    "ticket_summary": summary
                }
            
            # Still need info → ask for it
            if not has_phone and not has_access:
                return {
                    "text": "I understand - let me connect you with a professional. To create a service ticket, I need:\n\n1️⃣ **Your phone number** (so the technician can reach you)\n2️⃣ **Access info** (gate code, key location, or best times to visit)",
                    "risk": "Yellow",
                    "action": "Escalate",
                    "category": "Other",
                    "escalation_mode": True,
                    "contact_info": collected_info
                }
            elif not has_phone:
                return {
                    "text": f"Thanks! Access info noted: **{collected_info.get('access')}**\n\nNow, what's the best phone number to reach you?",
                    "risk": "Yellow",
                    "action": "Escalate",
                    "category": "Other",
                    "escalation_mode": True,
                    "contact_info": collected_info
                }
            else:  # not has_access
                return {
                    "text": f"Got your number: **{collected_info.get('phone')}**\n\nLastly, what's the access code or best time for the technician to visit?",
                    "risk": "Yellow",
                    "action": "Escalate",
                    "category": "Other",
                    "escalation_mode": True,
                    "contact_info": collected_info
                }
        
        # ── NORMAL TRIAGE MODE (Slot-Filling State Machine) ──
        prompt_parts = []
        
        conversation_text = self._format_history(history)
        has_image = image_data is not None
        prompt_parts.append(f"""Analyze this maintenance conversation and determine what information is still needed.

CONVERSATION:
{conversation_text}

IMAGE UPLOADED: {"Yes" if has_image else "No"}

Analyze the conversation and:
1. Check for EMERGENCY conditions (fire, gas, major flooding) → action: EMERGENCY
2. Extract any filled slots (tenant_name, unit, issue, severity, location, access, contact)
3. For visual issues without a photo, set request_photo: true
4. If slots are missing → action: QUESTION (ask ONE question for most critical missing slot)
5. If all 7 slots are filled → action: CONFIRM (show summary for user to verify)
6. If user confirmed the summary → action: CREATE_TICKET

IMPORTANT: CONTACT must be an actual phone number or email. "Contact me" or "call me" is NOT valid.

Return ONLY valid JSON:
{{
    "text": "Your response to the user",
    "risk": "Green|Yellow|Red",
    "action": "QUESTION|CONFIRM|CREATE_TICKET|EMERGENCY",
    "request_photo": false,
    "missing_info": ["list of missing slots"],
    "category": "Plumbing|Electrical|HVAC|Appliance|Structural|Pest Control|Locksmith|Other",
    "filled_slots": {{
        "tenant_name": "extracted name or null",
        "unit": "extracted unit/address or null",
        "issue": "extracted issue or null",
        "severity": "extracted severity or null",
        "location": "extracted location or null",
        "access": "extracted access info or null",
        "contact": "extracted phone/email or null"
    }}
}}""")
        
        if image_data:
            prompt_parts.append({"mime_type": image_mime_type, "data": image_data})
        
        try:
            response = self.model.generate_content(prompt_parts)
            result = self._parse_json_response(response.text)
            
            action = result.get("action", "QUESTION")
            missing_info = result.get("missing_info", [])
            filled_slots = result.get("filled_slots", {})
            
            response_data = {
                "text": result.get("text", "Could you provide more details about the issue?"),
                "risk": result.get("risk", "Yellow"),
                "action": action,
                "category": result.get("category", "Other"),
                "missing_info": missing_info,
                "filled_slots": filled_slots,
                "escalation_mode": False,
                "contact_info": {},
                "request_photo": result.get("request_photo", False)
            }
            
            # Handle CREATE_TICKET action - prepare for database save
            if action == "CREATE_TICKET":
                response_data["ready_for_ticket"] = True
                response_data["ticket_data"] = {
                    "tenant_name": filled_slots.get("tenant_name"),
                    "unit": filled_slots.get("unit"),
                    "issue": filled_slots.get("issue"),
                    "severity": filled_slots.get("severity"),
                    "location": filled_slots.get("location"),
                    "access": filled_slots.get("access"),
                    "contact": filled_slots.get("contact"),
                    "category": result.get("category", "Other"),
                    "risk": result.get("risk", "Yellow")
                }
            
            # Handle CONFIRM action - user needs to verify before ticket creation
            if action == "CONFIRM":
                response_data["awaiting_confirmation"] = True
                response_data["ticket_data"] = {
                    "tenant_name": filled_slots.get("tenant_name"),
                    "unit": filled_slots.get("unit"),
                    "issue": filled_slots.get("issue"),
                    "severity": filled_slots.get("severity"),
                    "location": filled_slots.get("location"),
                    "access": filled_slots.get("access"),
                    "contact": filled_slots.get("contact"),
                    "category": result.get("category", "Other"),
                    "risk": result.get("risk", "Yellow")
                }
            
            # Handle EMERGENCY action
            if action == "EMERGENCY":
                response_data["is_emergency"] = True
                response_data["text"] = f"🚨 EMERGENCY: {result.get('text', 'This is an emergency situation. Please evacuate if necessary and call emergency services.')}"
            
            return response_data
            
        except Exception as e:
            return {
                "text": "I encountered an issue. Please try again.",
                "risk": "Yellow",
                "action": "QUESTION",
                "category": "Other",
                "missing_info": ["Tenant_Name", "Unit", "Issue", "Severity", "Location", "Access", "Contact"],
                "filled_slots": {},
                "escalation_mode": False,
                "contact_info": {},
                "request_photo": False,
                "error": str(e)
            }
    
    # ─────────────────────────────────────────────────────────────────────────────
    # VIDEO AUDIT METHODS
    # ─────────────────────────────────────────────────────────────────────────────
    
    def audit_video(
        self,
        video_path: str,
        mode: str,
        baseline_text: Optional[str] = None,
        baseline_json: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Audit a video for move-in or move-out inspection.
        Returns structured JSON data (no markdown).
        
        Args:
            video_path: Path to video file
            mode: "move-in" or "move-out"
            baseline_text: For move-out, the move-in summary to compare against
            baseline_json: For move-out, the structured baseline items
        
        Returns:
            Dict with audit results including "items" array
        """
        if mode == "move-in":
            return self._audit_move_in(video_path)
        elif mode == "move-out":
            return self._audit_move_out(video_path, baseline_text, baseline_json)
        else:
            return {"success": False, "error": f"Invalid mode: {mode}. Use 'move-in' or 'move-out'."}
    
    def audit_video_bytes(
        self,
        video_data: bytes,
        video_mime_type: str,
        mode: str,
        baseline_text: Optional[str] = None,
        baseline_json: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Audit a video from bytes (for API uploads).
        Returns structured JSON data (no markdown).
        
        Args:
            video_data: Raw video bytes
            video_mime_type: MIME type (e.g., "video/mp4")
            mode: "move-in" or "move-out"
            baseline_text: For move-out comparison
            baseline_json: Structured baseline items
        
        Returns:
            Dict with audit results including "items" array
        """
        # Save to temp file then process
        ext = self._get_video_extension(video_mime_type)
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
            f.write(video_data)
            temp_path = f.name
        
        try:
            return self.audit_video(temp_path, mode, baseline_text, baseline_json)
        finally:
            try:
                os.unlink(temp_path)
            except Exception:
                pass
    
    def _audit_move_in(self, video_path: str) -> Dict[str, Any]:
        """
        Generate baseline from move-in video.
        Returns JSON array of items with conditions.
        """
        video_file = None
        try:
            video_file = self._upload_video(video_path)
            
            prompt = """Analyze this move-in inspection video. Document EVERY item you can see.

IMPORTANT: Return ONLY a valid JSON array. NO markdown, NO explanations, NO code blocks.

Format (return this EXACT structure):
[
  {"item": "Living Room - North Wall", "condition": "Good - no damage", "room": "Living Room", "timestamp": "0:05"},
  {"item": "Kitchen Counter", "condition": "Minor scratch near sink", "room": "Kitchen", "timestamp": "0:30"},
  {"item": "Bathroom Mirror", "condition": "Clean, no cracks", "room": "Bathroom", "timestamp": "1:15"}
]

Document: walls, floors, ceilings, fixtures, appliances, cabinets, doors, windows, counters, etc.
Note any pre-existing damage, wear, or issues.
Include approximate timestamp when each item is visible.

Return ONLY the JSON array, nothing else."""
            
            response = self.model.generate_content([video_file, prompt])
            items = self._parse_json_array(response.text)
            
            # Generate summary from items
            summary = f"Documented {len(items)} items. "
            rooms = list(set(item.get("room", "Unknown") for item in items if item.get("room")))
            if rooms:
                summary += f"Rooms: {', '.join(rooms)}. "
            
            issues = [item for item in items if any(word in item.get("condition", "").lower() 
                     for word in ["damage", "scratch", "stain", "crack", "worn", "broken", "missing"])]
            if issues:
                summary += f"Pre-existing issues: {len(issues)}."
            else:
                summary += "No significant pre-existing issues noted."
            
            return {
                "success": True,
                "items": items,
                "summary": summary,
                "rooms": rooms,
                "pre_existing_issues": [i["item"] + ": " + i["condition"] for i in issues]
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "items": []}
        finally:
            if video_file:
                self._delete_video(video_file)
    
    def _audit_move_out(
        self,
        video_path: str,
        baseline_text: Optional[str],
        baseline_json: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Compare move-out video against baseline.
        Returns JSON array of items with damage assessment.
        """
        video_file = None
        try:
            video_file = self._upload_video(video_path)
            
            baseline_context = ""
            if baseline_json:
                baseline_context = f"""
MOVE-IN BASELINE (compare against this):
{json.dumps(baseline_json, indent=2)}
"""
            elif baseline_text:
                baseline_context = f"""
MOVE-IN BASELINE (compare against this):
{baseline_text}
"""
            
            prompt = f"""Analyze this move-out inspection video.{baseline_context}

IMPORTANT: Return ONLY a valid JSON array. NO markdown, NO explanations, NO code blocks.

For EACH item visible, determine if there's NEW damage compared to move-in baseline.

Format (return this EXACT structure):
[
  {{"item": "Living Room - North Wall", "condition": "Large hole near outlet", "is_new": true, "room": "Living Room", "timestamp": "0:10", "estimated_cost": 150}},
  {{"item": "Kitchen Counter", "condition": "Same minor scratch as move-in", "is_new": false, "room": "Kitchen", "timestamp": "0:35", "estimated_cost": 0}},
  {{"item": "Bathroom Mirror", "condition": "Cracked in corner", "is_new": true, "room": "Bathroom", "timestamp": "1:20", "estimated_cost": 75}}
]

Fields:
- is_new: true if this is NEW damage not in baseline, false if pre-existing or normal wear
- estimated_cost: Repair cost estimate in USD (0 if no damage or pre-existing)

Return ONLY the JSON array, nothing else."""
            
            response = self.model.generate_content([video_file, prompt])
            items = self._parse_json_array(response.text)
            
            # Calculate new damages and costs
            new_damages = [i for i in items if i.get("is_new")]
            total_cost = sum(i.get("estimated_cost", 0) for i in new_damages)
            
            # Generate summary
            summary = f"Inspected {len(items)} items. "
            if new_damages:
                summary += f"Found {len(new_damages)} new damages. Total estimated cost: ${total_cost}."
            else:
                summary += "No new damages found beyond normal wear."
            
            return {
                "success": True,
                "items": items,
                "summary": summary,
                "new_damages": [f"{i['item']}: {i['condition']} (${i.get('estimated_cost', 0)})" for i in new_damages],
                "total_estimated_cost": total_cost
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "items": []}
        finally:
            if video_file:
                self._delete_video(video_file)
    
    # ─────────────────────────────────────────────────────────────────────────────
    # HELPER METHODS
    # ─────────────────────────────────────────────────────────────────────────────
    
    def _format_history(self, history: List[Dict[str, Any]]) -> str:
        """Format conversation history as text."""
        lines = []
        for msg in history:
            role = msg.get("role", "user").upper()
            content = msg.get("content", "")
            lines.append(f"{role}: {content}")
        return "\n".join(lines) if lines else "No conversation history."
    
    def _load_image(self, image_path: str) -> Dict[str, Any]:
        """Load image file for Gemini."""
        import mimetypes
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type:
            mime_type = "image/jpeg"
        
        with open(image_path, "rb") as f:
            data = f.read()
        
        return {"mime_type": mime_type, "data": data}
    
    def _upload_video(self, video_path: str):
        """Upload video to Gemini File API."""
        genai = _get_genai()
        ext = os.path.splitext(video_path)[1].lower()
        mime_types = {
            ".mp4": "video/mp4",
            ".mov": "video/quicktime",
            ".avi": "video/x-msvideo",
            ".webm": "video/webm"
        }
        mime_type = mime_types.get(ext, "video/mp4")
        
        video_file = genai.upload_file(path=video_path, mime_type=mime_type)
        
        # Wait for processing
        while video_file.state.name == "PROCESSING":
            time.sleep(2)
            video_file = genai.get_file(video_file.name)
        
        if video_file.state.name == "FAILED":
            raise ValueError("Video processing failed")
        
        return video_file
    
    def _delete_video(self, video_file):
        """Delete uploaded video from Gemini."""
        try:
            genai = _get_genai()
            genai.delete_file(video_file.name)
        except Exception:
            pass
    
    def _get_video_extension(self, mime_type: str) -> str:
        """Get file extension from MIME type."""
        extensions = {
            "video/mp4": ".mp4",
            "video/quicktime": ".mov",
            "video/x-msvideo": ".avi",
            "video/webm": ".webm"
        }
        return extensions.get(mime_type, ".mp4")
    
    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON object from Gemini response."""
        text = response_text.strip()
        
        # Remove markdown code blocks
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"text": text}
    
    def _parse_json_array(self, response_text: str) -> List[Dict[str, Any]]:
        """Parse JSON array from Gemini response (for audit results)."""
        text = response_text.strip()
        
        # Remove markdown code blocks
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        # Find the JSON array in the text
        start = text.find('[')
        end = text.rfind(']')
        if start != -1 and end != -1 and end > start:
            text = text[start:end + 1]
        
        try:
            result = json.loads(text)
            if isinstance(result, list):
                return result
            return []
        except json.JSONDecodeError:
            return []
