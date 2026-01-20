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

# System prompt for maintenance triage
TRIAGE_SYSTEM_PROMPT = """You are a property maintenance expert. Your goal is to:
1. Identify the maintenance issue from the description and/or image
2. Assess safety risks using this scale:
   - Green: Safe, minor issue, tenant can likely fix themselves
   - Yellow: Moderate concern, should be addressed soon, may need professional
   - Red: Urgent safety hazard, requires immediate professional attention
3. Provide a self-help fix if the issue is safe (Green/Yellow)
4. Recommend professional help if needed

Categorize issues into: Plumbing, Electrical, HVAC, Appliance, Structural, Pest Control, Locksmith, Other

Be concise, helpful, and prioritize safety."""

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
        
        Args:
            history: List of conversation messages [{"role": "user"|"assistant", "content": "..."}]
            image_path: Optional path to an image file
        
        Returns:
            Dict with: {"text": "response", "risk": "Green|Yellow|Red", "action": "Deflect|Escalate|Info|CREATE_TICKET"}
        """
        prompt_parts = []
        
        # Build prompt from conversation history
        conversation_text = self._format_history(history)
        prompt_parts.append(f"""Analyze this maintenance issue:

{conversation_text}

Return ONLY valid JSON:
{{"text": "your response", "risk": "Green|Yellow|Red", "action": "Deflect|Escalate|Info", "category": "Plumbing|Electrical|HVAC|Appliance|Structural|Pest Control|Locksmith|Other"}}""")
        
        # Add image if provided
        if image_path and os.path.exists(image_path):
            try:
                prompt_parts.append(self._load_image(image_path))
            except Exception:
                pass
        
        try:
            response = self.model.generate_content(prompt_parts)
            result = self._parse_json_response(response.text)
            return {
                "text": result.get("text", "Could you provide more details?"),
                "risk": result.get("risk", "Yellow"),
                "action": result.get("action", "Info"),
                "category": result.get("category", "Other")
            }
        except Exception as e:
            return {
                "text": "I encountered an issue. Please try again.",
                "risk": "Yellow",
                "action": "Info",
                "category": "Other",
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
        
        # ── NORMAL TRIAGE MODE ──
        prompt_parts = []
        
        conversation_text = self._format_history(history)
        prompt_parts.append(f"""Analyze this maintenance issue:

{conversation_text}

Return ONLY valid JSON:
{{"text": "your response", "risk": "Green|Yellow|Red", "action": "Deflect|Escalate|Info", "category": "Plumbing|Electrical|HVAC|Appliance|Structural|Pest Control|Locksmith|Other"}}""")
        
        if image_data:
            prompt_parts.append({"mime_type": image_mime_type, "data": image_data})
        
        try:
            response = self.model.generate_content(prompt_parts)
            result = self._parse_json_response(response.text)
            return {
                "text": result.get("text", "Could you provide more details?"),
                "risk": result.get("risk", "Yellow"),
                "action": result.get("action", "Info"),
                "category": result.get("category", "Other"),
                "escalation_mode": False,
                "contact_info": {}
            }
        except Exception as e:
            return {
                "text": "I encountered an issue. Please try again.",
                "risk": "Yellow",
                "action": "Info",
                "category": "Other",
                "escalation_mode": False,
                "contact_info": {},
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
