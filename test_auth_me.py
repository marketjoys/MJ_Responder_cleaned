import requests
import json

# First login to get token
login_url = "http://localhost:8001/api/auth/login"
login_data = {
    "email": "amits.joys@gmail.com",
    "password": "ij@123"
}

print("Step 1: Login...")
login_response = requests.post(
    login_url, 
    json=login_data,
    headers={"Content-Type": "application/json"}
)

if login_response.status_code == 200:
    token_data = login_response.json()
    access_token = token_data['access_token']
    print(f"✅ Login successful")
    print(f"Token: {access_token[:30]}...")
    
    # Test /auth/me endpoint
    print("\nStep 2: Testing /auth/me endpoint...")
    me_url = "http://localhost:8001/api/auth/me"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    me_response = requests.get(me_url, headers=headers)
    print(f"Status: {me_response.status_code}")
    
    if me_response.status_code == 200:
        user_data = me_response.json()
        print("✅ /auth/me working!")
        print(json.dumps(user_data, indent=2, default=str))
    else:
        print(f"❌ /auth/me failed!")
        print(me_response.text)
else:
    print(f"❌ Login failed: {login_response.status_code}")
    print(login_response.text)

