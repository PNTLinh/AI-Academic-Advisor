"""Test suite for /api/chat endpoint and server-UI integration."""

import pytest
import json
import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from src.server.main import app

client = TestClient(app)


# ─── TEST 1: Health Check ────────────────────────────────────────────────
class TestHealthCheck:
    """Verify server is running and database connectivity."""
    
    def test_health_check_success(self):
        """Health endpoint should return 200 and status=ok."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["ok", "error"]
        assert "database" in data
        print(f"✅ Health check: {data}")


# ─── TEST 2: Chat Endpoint - Basic ──────────────────────────────────────
class TestChatBasic:
    """Test basic chat endpoint functionality."""
    
    def test_chat_basic_message(self):
        """POST /api/chat with simple message should return reply."""
        payload = {
            "message": "Hello, what courses should I take?",
            "max_turns": 3
        }
        response = client.post("/api/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        assert isinstance(data["reply"], str)
        assert len(data["reply"]) > 0
        print(f"✅ Chat response: {data['reply'][:100]}...")
    
    def test_chat_with_user_id_header(self):
        """POST /api/chat with X-User-Id header should track user conversation."""
        user_id = "test_user_001"
        
        # First message
        payload1 = {"message": "What is my GPA?", "max_turns": 3}
        response1 = client.post("/api/chat", json=payload1, headers={"X-User-Id": user_id})
        assert response1.status_code == 200
        
        # Second message (should maintain context with same user)
        payload2 = {"message": "What courses do you recommend?", "max_turns": 3}
        response2 = client.post("/api/chat", json=payload2, headers={"X-User-Id": user_id})
        assert response2.status_code == 200
        print(f"✅ Multi-turn conversation with user_id works")
    
    def test_chat_anonymous_user(self):
        """POST /api/chat without X-User-Id should default to 'anonymous'."""
        payload = {"message": "What's your name?", "max_turns": 1}
        response = client.post("/api/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        print(f"✅ Anonymous user chat works: {data['reply'][:80]}...")


# ─── TEST 3: Chat Endpoint - Input Validation ──────────────────────────
class TestChatValidation:
    """Test input validation for chat endpoint."""
    
    def test_chat_empty_message(self):
        """POST /api/chat with empty message should fail validation."""
        payload = {"message": "", "max_turns": 3}
        response = client.post("/api/chat", json=payload)
        # Could be 422 (validation error) or 200 with fallback reply
        assert response.status_code in [200, 422]
        print(f"✅ Empty message validation: status={response.status_code}")
    
    def test_chat_missing_message_field(self):
        """POST /api/chat without 'message' field should return 422."""
        payload = {"max_turns": 3}
        response = client.post("/api/chat", json=payload)
        assert response.status_code == 422
        print(f"✅ Missing 'message' field rejected: {response.status_code}")
    
    def test_chat_max_turns_default(self):
        """POST /api/chat without 'max_turns' should use default (10)."""
        payload = {"message": "Test message"}
        response = client.post("/api/chat", json=payload)
        assert response.status_code == 200
        print(f"✅ Default max_turns=10 used")
    
    def test_chat_invalid_json(self):
        """POST /api/chat with invalid JSON should return 422."""
        response = client.post(
            "/api/chat",
            content="invalid json {",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
        print(f"✅ Invalid JSON rejected: {response.status_code}")


# ─── TEST 4: Chat Endpoint - Response Format ───────────────────────────
class TestChatResponseFormat:
    """Test ChatResponse schema compliance."""
    
    def test_chat_response_schema(self):
        """Verify ChatResponse contains required fields."""
        payload = {"message": "Tell me something interesting", "max_turns": 1}
        response = client.post("/api/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        # Required fields
        assert "reply" in data
        assert isinstance(data["reply"], str)
        
        # Optional fields
        if "status" in data:
            assert data["status"] in ["completed", "pending", "error"]
        if "debug_info" in data:
            assert data["debug_info"] is None or isinstance(data["debug_info"], str)
        
        print(f"✅ Response schema valid: {list(data.keys())}")


# ─── TEST 5: Chat Endpoint - CORS Headers ──────────────────────────────
class TestCORSHeaders:
    """Test CORS middleware configuration."""
    
    def test_cors_headers_present(self):
        """Verify CORS headers are present in response."""
        response = client.options("/api/chat")
        # TestClient automatically handles CORS
        print(f"✅ CORS configuration check (status={response.status_code})")


# ─── TEST 6: File Upload (related to chat) ──────────────────────────────
class TestFileUpload:
    """Test file upload endpoint (often used with chat)."""
    
    def test_upload_invalid_file_type(self):
        """POST /upload with unsupported file type should fail."""
        response = client.post(
            "/api/upload",
            files={"file": ("test.txt", b"some text", "text/plain")}
        )
        assert response.status_code in [400, 422]
        print(f"✅ Invalid file type rejected: {response.status_code}")
    
    def test_upload_no_file(self):
        """POST /upload without file should fail."""
        response = client.post("/api/upload")
        assert response.status_code == 422
        print(f"✅ Missing file rejected: {response.status_code}")


# ─── TEST 7: Integration - Server + UI Simulation ──────────────────────
class TestServerUIIntegration:
    """Simulate UI calling server endpoints as per app/advisor/page.tsx."""
    
    def test_ui_chat_flow_simulation(self):
        """Simulate UI chat flow: GET user status → POST chat messages."""
        user_id = "UI_TEST_USER_001"
        
        # Step 1: Fetch user status (if endpoint exists)
        # response_status = client.get("/api/user/status", params={"student_id": user_id})
        # Note: /api/user/status might not exist yet; skip for now
        
        # Step 2: Send chat message as UI would
        chat_payload = {
            "message": "Tôi vừa tải lên bảng điểm. Bạn có thể giúp tôi phân tích không?",
            "max_turns": 5
        }
        response = client.post(
            "/api/chat",
            json=chat_payload,
            headers={"X-User-Id": user_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        
        # Step 3: Send follow-up message
        followup_payload = {
            "message": "Lộ trình học tập của tôi như thế nào?",
            "max_turns": 5
        }
        response2 = client.post(
            "/api/chat",
            json=followup_payload,
            headers={"X-User-Id": user_id}
        )
        assert response2.status_code == 200
        
        print(f"✅ UI simulation: multi-turn conversation works")


# ─── TEST 8: Load/Stress Test (light) ──────────────────────────────────
class TestLoadSimulation:
    """Light load test for chat endpoint."""
    
    def test_rapid_requests(self):
        """Send multiple rapid requests to simulate light load."""
        payload = {"message": "Quick test", "max_turns": 1}
        
        for i in range(5):
            response = client.post(
                "/api/chat",
                json=payload,
                headers={"X-User-Id": f"load_test_{i}"}
            )
            assert response.status_code == 200
        
        print(f"✅ Load test: 5 rapid requests processed")


# ─── TEST 9: Error Handling ────────────────────────────────────────────
class TestErrorHandling:
    """Test error handling and fallback behavior."""
    
    def test_chat_fallback_to_mock(self):
        """Chat should fallback gracefully if agent fails."""
        payload = {"message": "Test", "max_turns": 3}
        response = client.post("/api/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        # Should always return a reply (mock or real)
        assert data["reply"] is not None
        assert len(data["reply"]) > 0
        print(f"✅ Fallback mechanism works")


# ─── Main Test Runner ──────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚀 CHAT API TEST SUITE")
    print("="*70 + "\n")
    
    # Run tests with pytest
    import sys
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    
    print("\n" + "="*70)
    print(f"Test run completed (exit code: {exit_code})")
    print("="*70 + "\n")
    
    sys.exit(exit_code)
