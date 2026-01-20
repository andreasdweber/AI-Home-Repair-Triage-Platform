"""
Fix-It AI - Maintenance Agent
AI-powered maintenance triage and video audit capabilities using Google Gemini
"""

import os
import json
import base64
import tempfile
import time
from typing import Optional, List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

# Gemini model configuration
GEMINI_MODEL = "gemini-2.0-flash"


class MaintenanceAgent:
    """
    AI agent for maintenance issue triage and video auditing.
    Uses Google Gemini for multi-modal analysis.
    """
    
    def __init__(self, db_session=None):
        """Initialize the agent with Gemini API configuration."""
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not configured. Please set it in the .env file.")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(GEMINI_MODEL)
        self.db_session = db_session
    
    def triage_issue(
        self,
        history: List[Dict[str, Any]],
        image_data: Optional[bytes] = None,
        image_mime_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Triage a maintenance issue using conversation history and optional image.
        
        Args:
            history: List of conversation messages [{"role": "user"|"assistant", "content": "..."}]
            image_data: Optional image bytes
            image_mime_type: MIME type of the image (e.g., "image/jpeg")
        
        Returns:
            Dict with response, diagnosis (if ready), risk_level, and needs_more_info flag
        """
        
        # Build conversation context
        conversation_context = self._build_conversation_context(history)
        has_image = image_data is not None
        has_description = any(
            msg.get("role") == "user" and len(msg.get("content", "")) > 20
            for msg in history
        )
        
        # Determine if we have enough info for diagnosis
        if has_image and has_description:
            return self._generate_diagnosis(conversation_context, image_data, image_mime_type)
        else:
            return self._gather_more_info(conversation_context, has_image, has_description)
    
    def _build_conversation_context(self, history: List[Dict[str, Any]]) -> str:
        """Build a text representation of the conversation history."""
        if not history:
            return "No previous conversation."
        
        context_parts = []
        for msg in history:
            role = msg.get("role", "user").capitalize()
            content = msg.get("content", "")
            context_parts.append(f"{role}: {content}")
        
        return "\n".join(context_parts)
    
    def _gather_more_info(
        self,
        conversation_context: str,
        has_image: bool,
        has_description: bool
    ) -> Dict[str, Any]:
        """Generate a response asking for more information."""
        
        prompt = f"""You are a helpful maintenance assistant for Fix-It AI.
Your goal is to gather enough information to diagnose a maintenance issue.

Current conversation:
{conversation_context}

Current status:
- Has image: {has_image}
- Has detailed description: {has_description}

Based on what's missing, ask a helpful follow-up question to better understand the issue.
If no image has been provided, politely ask if they can share a photo.
If the description is vague, ask specific questions about:
- Location of the issue in the unit
- When they first noticed it
- Any sounds, smells, or visible damage
- Whether it's affecting daily use

Keep your response conversational, brief, and helpful. Don't be repetitive with previous questions.
Return ONLY a JSON object:
{{
    "response": "Your follow-up question or message",
    "needs_more_info": true
}}"""

        try:
            response = self.model.generate_content(prompt)
            result = self._parse_json_response(response.text)
            result["needs_more_info"] = True
            result["risk_level"] = None
            result["diagnosis"] = None
            return result
        except Exception as e:
            return {
                "response": "Could you please describe the issue you're experiencing and share a photo if possible?",
                "needs_more_info": True,
                "risk_level": None,
                "diagnosis": None,
                "error": str(e)
            }
    
    def _generate_diagnosis(
        self,
        conversation_context: str,
        image_data: bytes,
        image_mime_type: str
    ) -> Dict[str, Any]:
        """Generate a full diagnosis with risk assessment."""
        
        prompt = f"""You are a Master Tradesperson with decades of experience in property maintenance.
Analyze this maintenance issue based on the conversation and image provided.

Conversation history:
{conversation_context}

Provide a complete diagnosis. Return ONLY a JSON object:
{{
    "response": "A friendly summary for the tenant explaining what you found",
    "diagnosis": {{
        "issue_title": "Brief title of the issue",
        "severity": "Low, Medium, or High",
        "estimated_cost_range": "Estimated repair cost in USD, e.g., '$50-$150'",
        "trade_category": "Electrical, Plumbing, HVAC, Roofing, General, Carpentry, Painting, Appliance",
        "explanation": "2-3 sentences explaining the issue",
        "recommended_action": "Immediate next step",
        "safety_warning": "Any safety concerns or 'None'",
        "can_diy": true/false,
        "diy_instructions": "If DIY is possible, brief instructions. Otherwise null"
    }},
    "risk_level": "Green (minor/cosmetic), Yellow (needs attention soon), or Red (urgent/safety issue)",
    "needs_more_info": false,
    "recommended_status": "Deflected (if DIY), Escalated (if needs pro), or Open (if unclear)"
}}

Risk Level Guidelines:
- GREEN: Cosmetic issues, minor wear, non-urgent items that can wait
- YELLOW: Functional issues that need attention within days/weeks, potential to worsen
- RED: Safety hazards, water damage, electrical issues, anything needing immediate professional attention"""

        try:
            # Create image part for Gemini
            image_part = {
                "mime_type": image_mime_type,
                "data": base64.b64encode(image_data).decode("utf-8")
            }
            
            response = self.model.generate_content([prompt, image_part])
            result = self._parse_json_response(response.text)
            result["needs_more_info"] = False
            return result
            
        except Exception as e:
            return {
                "response": "I was able to review your issue. Based on what I can see, I recommend having a professional take a look to provide an accurate assessment.",
                "diagnosis": {
                    "issue_title": "Maintenance Issue Identified",
                    "severity": "Medium",
                    "estimated_cost_range": "Varies",
                    "trade_category": "General",
                    "explanation": "Unable to complete detailed analysis.",
                    "recommended_action": "Schedule a professional inspection",
                    "safety_warning": "None identified",
                    "can_diy": False,
                    "diy_instructions": None
                },
                "risk_level": "Yellow",
                "needs_more_info": False,
                "recommended_status": "Open",
                "error": str(e)
            }
    
    def audit_video(
        self,
        video_data: bytes,
        video_mime_type: str,
        mode: str,
        unit_id: str,
        baseline_description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Audit a video for move-in or move-out inspection.
        
        Args:
            video_data: Video file bytes
            video_mime_type: MIME type (e.g., "video/mp4")
            mode: "move-in" or "move-out"
            unit_id: Identifier for the unit
            baseline_description: For move-out, the existing baseline to compare against
        
        Returns:
            Dict with audit results
        """
        
        if mode == "move-in":
            return self._audit_move_in(video_data, video_mime_type, unit_id)
        elif mode == "move-out":
            return self._audit_move_out(video_data, video_mime_type, unit_id, baseline_description)
        else:
            raise ValueError(f"Invalid audit mode: {mode}. Must be 'move-in' or 'move-out'.")
    
    def _upload_video_to_gemini(self, video_data: bytes, video_mime_type: str) -> Any:
        """Upload video to Gemini File API and wait for processing."""
        
        # Write video to temp file for upload
        suffix = self._get_video_extension(video_mime_type)
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(video_data)
            tmp_path = tmp_file.name
        
        try:
            # Upload to Gemini
            video_file = genai.upload_file(path=tmp_path, mime_type=video_mime_type)
            
            # Wait for processing to complete
            while video_file.state.name == "PROCESSING":
                time.sleep(2)
                video_file = genai.get_file(video_file.name)
            
            if video_file.state.name == "FAILED":
                raise ValueError(f"Video processing failed: {video_file.state.name}")
            
            return video_file
            
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    def _get_video_extension(self, mime_type: str) -> str:
        """Get file extension from MIME type."""
        extensions = {
            "video/mp4": ".mp4",
            "video/quicktime": ".mov",
            "video/x-msvideo": ".avi",
            "video/webm": ".webm",
            "video/mpeg": ".mpeg"
        }
        return extensions.get(mime_type, ".mp4")
    
    def _audit_move_in(
        self,
        video_data: bytes,
        video_mime_type: str,
        unit_id: str
    ) -> Dict[str, Any]:
        """Generate a baseline description from move-in video."""
        
        prompt = """You are a professional property inspector conducting a move-in inspection.
Analyze this video walkthrough and create a detailed baseline description of the unit's condition.

For each room/area visible, document:
1. Overall condition (Excellent, Good, Fair, Poor)
2. Walls: Paint condition, marks, holes, damage
3. Floors: Type, condition, scratches, stains
4. Ceilings: Condition, stains, cracks
5. Windows/Doors: Condition, operation notes
6. Fixtures: Lights, outlets, switches - note any issues
7. Appliances (if visible): Condition, any damage
8. Bathroom fixtures (if visible): Condition of sink, toilet, tub/shower
9. Any existing damage or wear that should be documented

Be thorough but concise. This baseline will be used to compare against move-out condition.

Return a JSON object:
{
    "unit_summary": "Brief overall description of the unit",
    "rooms": [
        {
            "name": "Room name (e.g., Living Room, Kitchen, Bedroom 1)",
            "overall_condition": "Excellent/Good/Fair/Poor",
            "details": "Detailed description of condition and any existing damage"
        }
    ],
    "existing_damage": [
        "List of any pre-existing damage items"
    ],
    "baseline_description": "A comprehensive narrative description suitable for future comparison",
    "inspection_date": "Current date",
    "notes": "Any additional observations"
}"""

        try:
            # Upload video to Gemini
            video_file = self._upload_video_to_gemini(video_data, video_mime_type)
            
            # Generate baseline analysis
            response = self.model.generate_content([prompt, video_file])
            result = self._parse_json_response(response.text)
            
            # Add metadata
            result["unit_id"] = unit_id
            result["mode"] = "move-in"
            result["success"] = True
            result["audit_date"] = datetime.utcnow().isoformat()
            
            # Clean up uploaded file
            try:
                genai.delete_file(video_file.name)
            except:
                pass
            
            return result
            
        except Exception as e:
            return {
                "unit_id": unit_id,
                "mode": "move-in",
                "success": False,
                "error": str(e),
                "baseline_description": None
            }
    
    def _audit_move_out(
        self,
        video_data: bytes,
        video_mime_type: str,
        unit_id: str,
        baseline_description: Optional[str]
    ) -> Dict[str, Any]:
        """Compare move-out video against baseline to identify new damages."""
        
        if not baseline_description:
            return {
                "unit_id": unit_id,
                "mode": "move-out",
                "success": False,
                "error": "No baseline description found for this unit. Please complete a move-in audit first.",
                "new_damages": []
            }
        
        prompt = f"""You are a professional property inspector conducting a move-out inspection.
Compare this video walkthrough against the move-in baseline description and identify ONLY NEW damages.

MOVE-IN BASELINE DESCRIPTION:
{baseline_description}

Your task:
1. Watch the move-out video carefully
2. Compare current condition against the baseline
3. Identify ONLY damages that are NEW (not documented in baseline)
4. Do NOT list items that were already noted in the baseline
5. Assess if each new damage is normal wear-and-tear or tenant-caused

Return a JSON object:
{{
    "unit_summary": "Brief overall assessment of move-out condition",
    "comparison_result": "Better than baseline / Same as baseline / Worse than baseline",
    "new_damages": [
        {{
            "location": "Room/area where damage is located",
            "description": "What the damage is",
            "severity": "Minor / Moderate / Severe",
            "wear_and_tear": true/false,
            "estimated_repair_cost": "Cost estimate in USD",
            "notes": "Additional context"
        }}
    ],
    "deductions_recommended": [
        {{
            "item": "Damage item",
            "amount": "Dollar amount",
            "justification": "Why this is tenant responsibility"
        }}
    ],
    "total_estimated_deductions": "Total dollar amount",
    "inspection_date": "Current date",
    "notes": "Any additional observations about the comparison"
}}

Important: Be fair and distinguish between normal wear-and-tear (landlord's responsibility) 
and actual damage (potentially tenant's responsibility)."""

        try:
            # Upload video to Gemini
            video_file = self._upload_video_to_gemini(video_data, video_mime_type)
            
            # Generate comparison analysis
            response = self.model.generate_content([prompt, video_file])
            result = self._parse_json_response(response.text)
            
            # Add metadata
            result["unit_id"] = unit_id
            result["mode"] = "move-out"
            result["success"] = True
            result["audit_date"] = datetime.utcnow().isoformat()
            
            # Clean up uploaded file
            try:
                genai.delete_file(video_file.name)
            except:
                pass
            
            return result
            
        except Exception as e:
            return {
                "unit_id": unit_id,
                "mode": "move-out",
                "success": False,
                "error": str(e),
                "new_damages": []
            }
    
    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON from Gemini response, handling markdown code blocks."""
        text = response_text.strip()
        
        # Remove markdown code blocks if present
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            # Return a basic structure if parsing fails
            return {
                "response": text[:500] if text else "Unable to parse response",
                "parse_error": str(e)
            }
