import requests
import json

# Test login endpoint
login_url = "http://localhost:8001/api/login"
login_data = {
    "username": "amits.joys@gmail.com",
    "password": "ij@123"
}

print("=" * 80)
print("TESTING LOGIN ENDPOINT")
print("=" * 80)

print(f"\nEndpoint: {login_url}")
print(f"Credentials: {login_data}")

try:
    response = requests.post(login_url, data=login_data)
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"\nResponse Body:")
    
    if response.status_code == 200:
        data = response.json()
        print(json.dumps(data, indent=2))
        print("\n✅ Login successful!")
        print(f"Access Token: {data.get('access_token', 'N/A')[:50]}...")
    else:
        print(response.text)
        print("\n❌ Login failed!")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

