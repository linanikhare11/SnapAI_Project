import urllib.request
import urllib.error
import json

BASE_URL = "http://localhost:5000"
TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTcxMzAwNzE3OSwianRpIjoiZjNkMWI0OGQtMjBkNC00YjBhLThmNjUtZmU2N2E1NjQ1MWIwIiwidHlwZSI6ImFjY2VzcyIsInN1YiI6IjEiLCJuYmYiOjE3MTMwMDcxNzksImV4cCI6MTcxMzA5MzU3OX0.vAKHU1jWJjhjLJ1wZp0KTXdGbnR3-6Zr6GdHjFJjdIo"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
DATA = json.dumps({"name": "Test", "email": "test@test.com", "mobile_number": "+123"})

def test_route(method, route):
    url = f"{BASE_URL}{route}"
    try:
        req = urllib.request.Request(url, method=method, headers=HEADERS)
        if method in ["PUT", "POST"]:
            req.data = DATA.encode('utf-8')
        
        response = urllib.request.urlopen(req)
        print(f"{method} {route}")
        print(f"  Status: {response.status}")
        print(f"  Response: {response.read().decode()[:200]}")
    except urllib.error.HTTPError as e:
        print(f"{method} {route}")
        print(f"  Status: {e.code}")
        print(f"  Message: {e.reason}")
        print(f"  Response: {e.read().decode()[:200]}")
    except Exception as e:
        print(f"{method} {route} - ERROR: {e}")
    print()

routes_to_test = [
    ("GET", "/api/profile/me"),
    ("PUT", "/api/profile/me/contact"),
    ("OPTIONS", "/api/profile/me/contact"),
]

for method, route in routes_to_test:
    test_route(method, route)
