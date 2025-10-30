import requests
import json

# Test with correct endpoint
login_url = "http://localhost:8001/api/auth/login"
login_data = {
    "email": "amits.joys@gmail.com",
    "password": "ij@123"
}

print("Testing login with correct endpoint...")
print(f"URL: {login_url}")

try:
    response = requests.post(
        login_url, 
        json=login_data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("\n✅ Login Successful!")
        print(f"Access Token: {data.get('access_token', 'N/A')[:50]}...")
        print(f"Token Type: {data.get('token_type', 'N/A')}")
        
        # Test accessing protected endpoint
        headers = {"Authorization": f"Bearer {data['access_token']}"}
        me_response = requests.get("http://localhost:8001/api/users/me", headers=headers)
        print(f"\nUser Info Test: {me_response.status_code}")
        if me_response.status_code == 200:
            user_data = me_response.json()
            print(f"User Email: {user_data.get('email')}")
            print(f"User Name: {user_data.get('full_name')}")
    else:
        print(f"\n❌ Login Failed!")
        print(response.text)
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

