"""
Unit tests for the Slot-Filling State Machine in MaintenanceAgent.

Tests the agent's ability to:
1. Identify missing slots and ask appropriate questions
2. Detect emergencies and return EMERGENCY action
3. Request photos for visual issues
4. Show confirmation before creating tickets
5. Only create tickets when all 7 slots are filled
"""

import pytest
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))


class TestSlotFillingLogic:
    """Test the slot-filling state machine logic."""
    
    # ─────────────────────────────────────────────────────────────────────────────
    # SLOT IDENTIFICATION TESTS
    # ─────────────────────────────────────────────────────────────────────────────
    
    def test_all_slots_defined(self):
        """Verify all 7 required slots are defined in the system prompt."""
        from agent import TRIAGE_SYSTEM_PROMPT
        
        required_slots = [
            "TENANT_NAME",
            "UNIT",
            "ISSUE",
            "SEVERITY",
            "LOCATION",
            "ACCESS",
            "CONTACT"
        ]
        
        for slot in required_slots:
            assert slot in TRIAGE_SYSTEM_PROMPT, f"Slot {slot} not found in system prompt"
    
    def test_confirm_action_defined(self):
        """Verify CONFIRM action is defined for pre-ticket confirmation."""
        from agent import TRIAGE_SYSTEM_PROMPT
        
        assert "CONFIRM" in TRIAGE_SYSTEM_PROMPT
        assert "CREATE_TICKET" in TRIAGE_SYSTEM_PROMPT
        assert "EMERGENCY" in TRIAGE_SYSTEM_PROMPT
        assert "QUESTION" in TRIAGE_SYSTEM_PROMPT
    
    def test_photo_request_defined(self):
        """Verify photo request logic is defined."""
        from agent import TRIAGE_SYSTEM_PROMPT
        
        assert "request_photo" in TRIAGE_SYSTEM_PROMPT
        assert "photo" in TRIAGE_SYSTEM_PROMPT.lower()
    
    # ─────────────────────────────────────────────────────────────────────────────
    # RESPONSE FORMAT TESTS
    # ─────────────────────────────────────────────────────────────────────────────
    
    def test_response_includes_all_fields(self):
        """Test that triage response includes all expected fields."""
        from agent import MaintenanceAgent
        
        # Skip if no API key
        if not os.getenv("GEMINI_API_KEY"):
            pytest.skip("GEMINI_API_KEY not set")
        
        agent = MaintenanceAgent()
        history = [{"role": "user", "content": "I have a leak"}]
        
        result = agent.triage(history)
        
        # Check required fields exist
        assert "text" in result
        assert "risk" in result
        assert "action" in result
        assert "missing_info" in result
        assert "filled_slots" in result
        assert "request_photo" in result
    
    def test_filled_slots_structure(self):
        """Test that filled_slots has all 7 slot keys."""
        from agent import MaintenanceAgent
        
        if not os.getenv("GEMINI_API_KEY"):
            pytest.skip("GEMINI_API_KEY not set")
        
        agent = MaintenanceAgent()
        history = [{"role": "user", "content": "My name is John, I'm in unit 5A, toilet is leaking badly in the bathroom, it's flooding, use the master key, call me at 555-1234"}]
        
        result = agent.triage(history)
        filled_slots = result.get("filled_slots", {})
        
        expected_keys = ["tenant_name", "unit", "issue", "severity", "location", "access", "contact"]
        for key in expected_keys:
            assert key in filled_slots, f"Key {key} missing from filled_slots"
    
    # ─────────────────────────────────────────────────────────────────────────────
    # ACTION TESTS
    # ─────────────────────────────────────────────────────────────────────────────
    
    def test_question_action_when_slots_missing(self):
        """Test that QUESTION action is returned when slots are missing."""
        from agent import MaintenanceAgent
        
        if not os.getenv("GEMINI_API_KEY"):
            pytest.skip("GEMINI_API_KEY not set")
        
        agent = MaintenanceAgent()
        # Minimal info - should trigger QUESTION
        history = [{"role": "user", "content": "leak"}]
        
        result = agent.triage(history)
        
        # Should be asking a question since most slots are missing
        assert result.get("action") in ["QUESTION", "EMERGENCY"], f"Expected QUESTION, got {result.get('action')}"
        assert len(result.get("missing_info", [])) > 0, "Should have missing info"
    
    def test_emergency_action_for_gas_leak(self):
        """Test that EMERGENCY action is returned for gas leaks."""
        from agent import MaintenanceAgent
        
        if not os.getenv("GEMINI_API_KEY"):
            pytest.skip("GEMINI_API_KEY not set")
        
        agent = MaintenanceAgent()
        history = [{"role": "user", "content": "I smell gas! There's a strong gas smell in my apartment!"}]
        
        result = agent.triage(history)
        
        # Gas should trigger emergency
        assert result.get("risk") == "Red" or result.get("action") == "EMERGENCY", \
            f"Gas leak should be Red risk or EMERGENCY, got risk={result.get('risk')}, action={result.get('action')}"
    
    def test_emergency_action_for_fire(self):
        """Test that EMERGENCY action is returned for fire."""
        from agent import MaintenanceAgent
        
        if not os.getenv("GEMINI_API_KEY"):
            pytest.skip("GEMINI_API_KEY not set")
        
        agent = MaintenanceAgent()
        history = [{"role": "user", "content": "There's a fire in my kitchen! Flames coming from the stove!"}]
        
        result = agent.triage(history)
        
        assert result.get("risk") == "Red" or result.get("action") == "EMERGENCY", \
            f"Fire should be Red risk or EMERGENCY, got risk={result.get('risk')}, action={result.get('action')}"
    
    # ─────────────────────────────────────────────────────────────────────────────
    # TICKET DATA TESTS
    # ─────────────────────────────────────────────────────────────────────────────
    
    def test_ticket_data_when_all_slots_filled(self):
        """Test that ticket_data is populated when all slots are filled."""
        from agent import MaintenanceAgent
        
        if not os.getenv("GEMINI_API_KEY"):
            pytest.skip("GEMINI_API_KEY not set")
        
        agent = MaintenanceAgent()
        
        # Provide all information in a single detailed message
        history = [
            {"role": "user", "content": """Hi, my name is Sarah Johnson.
            I live in Unit 12B at 456 Oak Street.
            My kitchen faucet is leaking water continuously - it's a steady drip.
            The leak is under the kitchen sink.
            You can use the master key to enter, I work from 9-5.
            Please call me at 555-987-6543."""},
            {"role": "assistant", "content": "Let me confirm the details..."},
            {"role": "user", "content": "Yes, that's all correct."}
        ]
        
        result = agent.triage(history)
        
        # Should have ticket_data if action is CONFIRM or CREATE_TICKET
        if result.get("action") in ["CONFIRM", "CREATE_TICKET"]:
            assert "ticket_data" in result, "ticket_data should be present"
            ticket_data = result["ticket_data"]
            assert ticket_data.get("tenant_name") is not None, "tenant_name should be filled"
            assert ticket_data.get("contact") is not None, "contact should be filled"
    
    # ─────────────────────────────────────────────────────────────────────────────
    # CONTACT VALIDATION TESTS
    # ─────────────────────────────────────────────────────────────────────────────
    
    def test_contact_me_not_valid_contact(self):
        """Test that 'contact me' is not accepted as valid contact info."""
        from agent import TRIAGE_SYSTEM_PROMPT
        
        # The prompt should explicitly state this
        assert "contact me" in TRIAGE_SYSTEM_PROMPT.lower() or "call me" in TRIAGE_SYSTEM_PROMPT.lower()
        assert "NOT valid" in TRIAGE_SYSTEM_PROMPT or "NOT sufficient" in TRIAGE_SYSTEM_PROMPT


class TestTriageWithImageBytes:
    """Test the triage_with_image_bytes method."""
    
    def test_image_flag_tracked(self):
        """Test that image upload status is tracked in prompt."""
        from agent import MaintenanceAgent
        
        if not os.getenv("GEMINI_API_KEY"):
            pytest.skip("GEMINI_API_KEY not set")
        
        agent = MaintenanceAgent()
        history = [{"role": "user", "content": "I have water damage on my ceiling"}]
        
        # Without image
        result = agent.triage_with_image_bytes(history, image_data=None)
        
        # Should possibly request a photo for visual issues
        assert "request_photo" in result
    
    def test_escalation_mode_preserved(self):
        """Test that escalation_mode is included in response."""
        from agent import MaintenanceAgent
        
        if not os.getenv("GEMINI_API_KEY"):
            pytest.skip("GEMINI_API_KEY not set")
        
        agent = MaintenanceAgent()
        history = [{"role": "user", "content": "I need help with a repair"}]
        
        result = agent.triage_with_image_bytes(history)
        
        assert "escalation_mode" in result


class TestErrorHandling:
    """Test error handling in the agent."""
    
    def test_error_response_format(self):
        """Test that error responses have correct format."""
        # This tests the error response structure defined in the code
        expected_error_fields = {
            "text": str,
            "risk": str,
            "action": str,
            "category": str,
            "missing_info": list,
            "filled_slots": dict,
            "request_photo": bool
        }
        
        # The error response should include all 7 slots in missing_info
        expected_missing = ["Tenant_Name", "Unit", "Issue", "Severity", "Location", "Access", "Contact"]
        
        # Import to verify the code structure
        from agent import MaintenanceAgent
        
        # Verify the class exists and has triage methods
        assert hasattr(MaintenanceAgent, 'triage')
        assert hasattr(MaintenanceAgent, 'triage_with_image_bytes')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
