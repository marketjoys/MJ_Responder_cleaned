#!/usr/bin/env python3
"""
Simple Meeting Detection Test - Focus on core functionality
"""
import requests
import json
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')

# Configuration
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://email-automation-hub.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

def test_meeting_detection_simple():
    """Simple test of meeting detection API"""
    print("🔍 Testing Meeting Detection API (Simple)...")
    
    # Register test user
    user_data = {
        "email": f"simple.test.{int(time.time())}@example.com",
        "password": "testpassword123",
        "full_name": "Simple Test User"
    }
    
    try:
        # Register
        response = requests.post(f"{API_BASE}/auth/register", json=user_data, timeout=15)
        if response.status_code not in [200, 201]:
            print(f"❌ Registration failed: {response.status_code}")
            return
        
        auth_result = response.json()
        auth_token = auth_result.get('access_token')
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        print(f"✅ User registered: {user_data['email']}")
        
        # Test simple meeting detection
        meeting_request = {
            "email_content": "Hi, can we schedule a meeting tomorrow at 2 PM to discuss the project?",
            "subject": "Meeting Request",
            "sender": "test@example.com",
            "user_timezone": "UTC"
        }
        
        print("Testing meeting detection...")
        response = requests.post(
            f"{API_BASE}/calendar/detect-meeting",
            json=meeting_request,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            detected = result.get('meeting_detected', False)
            confidence = result.get('confidence_score', 0.0)
            
            print(f"✅ Meeting Detection API Response:")
            print(f"   - Detected: {detected}")
            print(f"   - Confidence: {confidence:.2f}")
            print(f"   - DateTime: {result.get('detected_datetime')}")
            print(f"   - Title: {result.get('detected_title')}")
            print(f"   - Location: {result.get('detected_location')}")
            print(f"   - Duration: {result.get('suggested_duration')} minutes")
            print(f"   - Needs Confirmation: {result.get('needs_confirmation')}")
            
            if detected and confidence > 0.5:
                print("✅ Meeting detection working correctly!")
            else:
                print("⚠️ Meeting detection may have issues")
                
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")

def test_meeting_intent_creation():
    """Test creating meeting-related intents"""
    print("\n📅 Testing Meeting Intent Creation...")
    
    # Register test user
    user_data = {
        "email": f"intent.test.{int(time.time())}@example.com",
        "password": "testpassword123",
        "full_name": "Intent Test User"
    }
    
    try:
        # Register
        response = requests.post(f"{API_BASE}/auth/register", json=user_data, timeout=15)
        if response.status_code not in [200, 201]:
            print(f"❌ Registration failed: {response.status_code}")
            return
        
        auth_result = response.json()
        auth_token = auth_result.get('access_token')
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Create meeting-related intent
        intent_data = {
            "name": "Simple Meeting Intent",
            "description": "Handle meeting requests and scheduling",
            "examples": ["schedule a meeting", "let's meet", "book a call"],
            "is_meeting_related": True,
            "confidence_threshold": 0.7
        }
        
        response = requests.post(f"{API_BASE}/intents", json=intent_data, headers=headers, timeout=15)
        
        if response.status_code in [200, 201]:
            intent = response.json()
            print(f"✅ Meeting intent created:")
            print(f"   - ID: {intent.get('id')}")
            print(f"   - Name: {intent.get('name')}")
            print(f"   - Meeting-related: {intent.get('is_meeting_related')}")
            
            # Clean up
            intent_id = intent.get('id')
            if intent_id:
                requests.delete(f"{API_BASE}/intents/{intent_id}", headers=headers, timeout=10)
                print(f"✅ Cleaned up test intent")
                
        else:
            print(f"❌ Intent creation failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Intent test failed: {str(e)}")

def check_system_health():
    """Check basic system health"""
    print("\n🏥 Checking System Health...")
    
    try:
        # Check polling status
        response = requests.get(f"{API_BASE}/polling/status", timeout=10)
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Polling service: {status.get('status')}")
        else:
            print(f"⚠️ Polling service check failed: {response.status_code}")
        
        # Check email accounts
        response = requests.get(f"{API_BASE}/email-accounts", timeout=10)
        if response.status_code == 200:
            accounts = response.json()
            print(f"✅ Email accounts available: {len(accounts)}")
        else:
            print(f"⚠️ Email accounts check failed: {response.status_code}")
            
        # Check intents
        response = requests.get(f"{API_BASE}/intents", timeout=10)
        if response.status_code == 200:
            intents = response.json()
            meeting_intents = [i for i in intents if i.get('is_meeting_related', False)]
            print(f"✅ Total intents: {len(intents)}, Meeting-related: {len(meeting_intents)}")
        else:
            print(f"⚠️ Intents check failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Health check failed: {str(e)}")

if __name__ == "__main__":
    print("🚀 Starting Simple Meeting Detection Tests...")
    
    check_system_health()
    test_meeting_intent_creation()
    
    # Wait a bit to avoid rate limits
    print("\n⏳ Waiting to avoid rate limits...")
    time.sleep(5)
    
    test_meeting_detection_simple()
    
    print("\n✅ Simple tests completed!")