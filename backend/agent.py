"""
Fix-It AI - Maintenance Agent
AI-powered maintenance triage and video audit capabilities using Google Gemini 2.0 Flash
"""

import os
import json
import tempfile
import time
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

# Gemini model configuration
GEMINI_MODEL = "gemini-2.0-flash"

# System prompt for maintenance triage
TRIAGE_SYSTEM_PROMPT = """You are a property maintenance expert. Your goal is to:
1. Identify the maintenance issue from the description and/or image
2. Assess safety risks using this scale:
   - Green: Safe, minor issue, tenant can likely fix themselves
   - Yellow: Moderate concern, should be addressed soon, may need professional
   - Red: Urgent safety hazard, requires immediate professional attention
3. Provide a self-help fix if the issue is safe (Green/Yellow)
4. Recommend professional help if needed

Be concise, helpful, and prioritize safety."""


class MaintenanceAgent:
    """
    AI agent for maintenance issue triage and video auditing.
    Uses Google Gemini 2.0 Flash for multi-modal analysis.
    """
    
    def __init__(self):
        """Initialize the agent with Gemini API configuration."""
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not configured. Please set it in the .env file.")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=TRIAGE_SYSTEM_PROMPT
        )
    
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
            Dict with: {"text": "response", "risk": "Green|Yellow|Red", "action": "Deflect|Escalate|Info"}
        """
        prompt_parts = []
        
        # Build prompt from conversation history
        conversation_text = self._format_history(history)
        prompt_parts.append(f"""Analyze this maintenance issue:

{conversation_text}

Return ONLY valid JSON:
{{"text": "your response", "risk": "Green|Yellow|Red", "action": "Deflect|Escalate|Info"}}""")
        
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
                "action": result.get("action", "Info")
            }
        except Exception as e:
            return {
                "text": "I encountered an issue. Please try again.",
                "risk": "Yellow",
                "action": "Info",
                "error": str(e)
            }
    
    def triage_with_image_bytes(
        self,
        history: List[Dict[str, Any]],
        image_data: Optional[bytes] = None,
        image_mime_type: str = "image/jpeg"
    ) -> Dict[str, Any]:
        """
        Triage using image bytes directly (for API uploads).
        
        Args:
            history: Conversation history
            image_data: Raw image bytes
            image_mime_type: MIME type of image
        
        Returns:
            Dict with: {"text": "...", "risk": "...", "action": "..."}
        """
        prompt_parts = []
        
        conversation_text = self._format_history(history)
        prompt_parts.append(f"""Analyze this maintenance issue:

{conversation_text}

Return ONLY valid JSON:
{{"text": "your response", "risk": "Green|Yellow|Red", "action": "Deflect|Escalate|Info"}}""")
        
        if image_data:
            prompt_parts.append({"mime_type": image_mime_type, "data": image_data})
        
        try:
            response = self.model.generate_content(prompt_parts)
            result = self._parse_json_response(response.text)
            return {
                "text": result.get("text", "Could you provide more details?"),
                "risk": result.get("risk", "Yellow"),
                "action": result.get("action", "Info")
            }
        except Exception as e:
            return {
                "text": "I encountered an issue. Please try again.",
                "risk": "Yellow",
                "action": "Info",
                "error": str(e)
            }
    
    # ─────────────────────────────────────────────────────────────────────────────
    # VIDEO AUDIT METHODS
    # ─────────────────────────────────────────────────────────────────────────────
    
    def audit_video(
        self,
        video_path: str,
        mode: str,
        baseline_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Audit a video for move-in or move-out inspection.
        
        Args:
            video_path: Path to video file
            mode: "move-in" or "move-out"
            baseline_text: For move-out, the move-in summary to compare against
        
        Returns:
            Dict with audit results
        """
        if mode == "move-in":
            return self._audit_move_in(video_path)
        elif mode == "move-out":
            return self._audit_move_out(video_path, baseline_text)
        else:
            return {"error": f"Invalid mode: {mode}. Use 'move-in' or 'move-out'."}
    
    def audit_video_bytes(
        self,
        video_data: bytes,
        video_mime_type: str,
        mode: str,
        baseline_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Audit a video from bytes (for API uploads).
        
        Args:
            video_data: Raw video bytes
            video_mime_type: MIME type (e.g., "video/mp4")
            mode: "move-in" or "move-out"
            baseline_text: For move-out comparison
        
        Returns:
            Dict with audit results
        """
        # Save to temp file then process
        ext = self._get_video_extension(video_mime_type)
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
            f.write(video_data)
            temp_path = f.name
        
        try:
            return self.audit_video(temp_path, mode, baseline_text)
        finally:
            try:
                os.unlink(temp_path)
            except Exception:
                pass
    
    def _audit_move_in(self, video_path: str) -> Dict[str, Any]:
        """Generate baseline summary from move-in video."""
        video_file = None
        try:
            video_file = self._upload_video(video_path)
            
            prompt = """Analyze this move-in inspection video. Create a detailed baseline record of:
1. Each room/area shown
2. Condition of walls, floors, ceilings
3. Condition of fixtures, appliances, cabinets
4. Any pre-existing damage or wear
5. Overall cleanliness and condition

Return ONLY valid JSON:
{
    "summary": "Detailed baseline description",
    "rooms": ["list of rooms/areas inspected"],
    "condition_notes": ["specific condition observations"],
    "pre_existing_issues": ["any existing damage or wear noted"]
}"""
            
            response = self.model.generate_content([video_file, prompt])
            result = self._parse_json_response(response.text)
            
            return {
                "success": True,
                "summary": result.get("summary", response.text),
                "rooms": result.get("rooms", []),
                "condition_notes": result.get("condition_notes", []),
                "pre_existing_issues": result.get("pre_existing_issues", [])
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            if video_file:
                self._delete_video(video_file)
    
    def _audit_move_out(self, video_path: str, baseline_text: Optional[str]) -> Dict[str, Any]:
        """Compare move-out video against baseline."""
        video_file = None
        try:
            video_file = self._upload_video(video_path)
            
            baseline_context = ""
            if baseline_text:
                baseline_context = f"""
MOVE-IN BASELINE:
{baseline_text}

Compare current condition against this baseline."""
            
            prompt = f"""Analyze this move-out inspection video.{baseline_context}

Identify:
1. Any new damage since move-in
2. Wear beyond normal use
3. Cleanliness issues
4. Missing fixtures or items
5. Areas requiring repair or cleaning

Return ONLY valid JSON:
{{
    "summary": "Overall assessment",
    "new_damages": ["list of new damages found"],
    "excessive_wear": ["wear beyond normal use"],
    "cleaning_needed": ["areas needing cleaning"],
    "deposit_deductions": ["recommended deductions with estimated costs"],
    "total_estimated_cost": 0
}}"""
            
            response = self.model.generate_content([video_file, prompt])
            result = self._parse_json_response(response.text)
            
            return {
                "success": True,
                "summary": result.get("summary", response.text),
                "new_damages": result.get("new_damages", []),
                "excessive_wear": result.get("excessive_wear", []),
                "cleaning_needed": result.get("cleaning_needed", []),
                "deposit_deductions": result.get("deposit_deductions", []),
                "total_estimated_cost": result.get("total_estimated_cost", 0)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
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
        """Parse JSON from Gemini response."""
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
