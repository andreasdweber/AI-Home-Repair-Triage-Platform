"""
Fix-It AI - Backend Verification Script
Smoke test to verify API endpoints are working correctly.

Usage:
    python tests/verify_backend.py

Prerequisites:
    - Backend running at http://localhost:8000
    - pip install requests
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"


def test_health():
    """Test the health endpoint."""
    print("=" * 50)
    print("TEST 1: Health Check")
    print("=" * 50)
    
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ Health check PASSED")
            return True
        else:
            print("❌ Health check FAILED")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ FAILED - Could not connect to server")
        print("   Make sure the backend is running: uvicorn main:app --reload")
        return False
    except Exception as e:
        print(f"❌ FAILED - {e}")
        return False


def test_chat_text_only():
    """Test the chat endpoint with text-only payload."""
    print("\n" + "=" * 50)
    print("TEST 2: Chat Endpoint (Text Only)")
    print("=" * 50)
    
    try:
        # Simulate a maintenance issue report
        payload = {
            "session_id": "test-session-1",
            "text": "My sink is leaking under the cabinet. There's water pooling on the floor."
        }
        
        print(f"Request: POST {BASE_URL}/chat")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        print("-" * 50)
        
        response = requests.post(
            f"{BASE_URL}/chat",
            data=payload  # Using form data as per the endpoint spec
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n📥 Agent Response:")
            print(f"   Session ID: {data.get('session_id')}")
            print(f"   Response: {data.get('response')}")
            print(f"   Risk Level: {data.get('risk')}")
            print(f"   Action: {data.get('action')}")
            print("\n✅ Chat endpoint PASSED")
            return True
        else:
            print(f"Response: {response.text}")
            print("❌ Chat endpoint FAILED")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ FAILED - Could not connect to server")
        return False
    except Exception as e:
        print(f"❌ FAILED - {e}")
        return False


def test_chat_follow_up():
    """Test a follow-up message in the same session."""
    print("\n" + "=" * 50)
    print("TEST 3: Chat Follow-up Message")
    print("=" * 50)
    
    try:
        payload = {
            "session_id": "test-session-1",
            "text": "The leak started yesterday and it's getting worse. I can see rust around the pipe."
        }
        
        print(f"Request: POST {BASE_URL}/chat")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        print("-" * 50)
        
        response = requests.post(
            f"{BASE_URL}/chat",
            data=payload
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n📥 Agent Response:")
            print(f"   Response: {data.get('response')}")
            print(f"   Risk Level: {data.get('risk')}")
            print(f"   Action: {data.get('action')}")
            print("\n✅ Follow-up test PASSED")
            return True
        else:
            print(f"Response: {response.text}")
            print("❌ Follow-up test FAILED")
            return False
            
    except Exception as e:
        print(f"❌ FAILED - {e}")
        return False


def main():
    """Run all verification tests."""
    print("\n🔧 FIX-IT AI - BACKEND VERIFICATION")
    print("=" * 50)
    print(f"Target: {BASE_URL}")
    print("=" * 50)
    
    results = []
    
    # Run tests
    results.append(("Health Check", test_health()))
    results.append(("Chat (Text Only)", test_chat_text_only()))
    results.append(("Chat (Follow-up)", test_chat_follow_up()))
    
    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {name}")
    
    print("-" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Backend is ready.")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Check the output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
