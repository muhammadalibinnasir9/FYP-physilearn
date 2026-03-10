import os
import django
from django.test import Client
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "physilearn_backend.settings")
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Create a test user
User.objects.filter(username="testuser_login").delete()
user = User.objects.create_user(username="testuser_login", password="securepassword123")

client = Client()

print("--- SIMULATING VALID LOGIN ---")
response = client.post('/api/login/', json.dumps({'username': 'testuser_login', 'password': 'securepassword123'}), content_type='application/json')
print("Status Code:", response.status_code)
try:
    content = json.loads(response.content)
    print("Response keys:", list(content.keys()) if response.status_code == 200 else content)
    if response.status_code == 200 and 'access' in content:
        print("PASS: Valid login simulation successful. Token generated.")
    else:
        print("FAIL: Valid login simulation failed.")
except Exception as e:
    print("Error parsing JSON:", e)
    print("Raw Content:", response.content[:500])

print("\n--- SIMULATING INVALID PASSWORD ---")
response_invalid = client.post('/api/login/', json.dumps({'username': 'testuser_login', 'password': 'wrongpassword'}), content_type='application/json')
print("Status Code:", response_invalid.status_code)
try:
    print("Response:", json.loads(response_invalid.content))
except:
    print("Raw Content:", response_invalid.content[:500])
if response_invalid.status_code == 401:
    print("PASS: Invalid password simulation successful. Error returned.")
else:
    print("FAIL: Invalid password simulation failed.")

print("\n--- SIMULATING MISSING CREDENTIALS ---")
response_missing = client.post('/api/login/', json.dumps({'username': 'testuser_login'}), content_type='application/json')
print("Status Code:", response_missing.status_code)
try:
    print("Response:", json.loads(response_missing.content))
except:
    print("Raw Content:", response_missing.content[:500])
if response_missing.status_code == 400:
    print("PASS: Missing credentials simulation successful. Error returned.")
else:
    print("FAIL: Missing credentials simulation failed.")

# Clean up
user.delete()
