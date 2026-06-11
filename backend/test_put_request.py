#!/usr/bin/env python3
"""Test PUT request to profile endpoint with real token."""
import sys
import json

try:
    import urllib.request
    import urllib.parse
except ImportError:
    print("Failed to import urllib")
    sys.exit(1)

def test_profile_endpoint():
    base_url = 'http://localhost:5000'
    
    # Step 1: Login to get token
    print("=== Step 1: Login ===")
    login_data = json.dumps({
        'email': 'lina@example.com',
        'password': 'password123'
    }).encode('utf-8')
    
    login_req = urllib.request.Request(
        f'{base_url}/api/auth/login',
        data=login_data,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(login_req) as response:
            login_response = json.loads(response.read().decode('utf-8'))
            token = login_response.get('token')
            print(f"✓ Login successful. Token: {token[:50]}...")
    except urllib.error.HTTPError as e:
        print(f"✗ Login failed: {e.code}")
        print(e.read().decode('utf-8'))
        return
    
    # Step 2: Test GET /api/profile/me
    print("\n=== Step 2: GET /api/profile/me ===")
    get_req = urllib.request.Request(
        f'{base_url}/api/profile/me',
        headers={'Authorization': f'Bearer {token}'},
        method='GET'
    )
    
    try:
        with urllib.request.urlopen(get_req) as response:
            get_response = json.loads(response.read().decode('utf-8'))
            print(f"✓ GET successful (200)")
            print(f"  Photographer: {get_response.get('name', 'N/A')}")
    except urllib.error.HTTPError as e:
        print(f"✗ GET failed: {e.code}")
        print(e.read().decode('utf-8'))
    
    # Step 3: Test PUT /api/profile/me/contact
    print("\n=== Step 3: PUT /api/profile/me/contact ===")
    put_data = json.dumps({
        'name': 'Updated Name',
        'email': 'lina@example.com',
        'mobile_number': '+919876543210'
    }).encode('utf-8')
    
    put_req = urllib.request.Request(
        f'{base_url}/api/profile/me/contact',
        data=put_data,
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        },
        method='PUT'
    )
    
    try:
        with urllib.request.urlopen(put_req) as response:
            put_response = json.loads(response.read().decode('utf-8'))
            print(f"✓ PUT successful (200)")
            print(f"  Response: {put_response.get('message', 'N/A')}")
    except urllib.error.HTTPError as e:
        print(f"✗ PUT failed: {e.code}")
        error_body = e.read().decode('utf-8')
        print(f"  Error: {error_body[:300]}")
        print(f"  Headers: {dict(e.headers)}")
    
    # Step 4: Test OPTIONS (CORS preflight)
    print("\n=== Step 4: OPTIONS /api/profile/me/contact (CORS) ===")
    options_req = urllib.request.Request(
        f'{base_url}/api/profile/me/contact',
        headers={
            'Origin': 'http://localhost:3000',
            'Access-Control-Request-Method': 'PUT',
            'Access-Control-Request-Headers': 'Authorization,Content-Type'
        },
        method='OPTIONS'
    )
    
    try:
        with urllib.request.urlopen(options_req) as response:
            print(f"✓ OPTIONS successful (200)")
            print(f"  Allow header: {response.headers.get('Allow', 'Not set')}")
            print(f"  Access-Control-Allow-Methods: {response.headers.get('Access-Control-Allow-Methods', 'Not set')}")
    except urllib.error.HTTPError as e:
        print(f"✗ OPTIONS failed: {e.code}")

if __name__ == '__main__':
    test_profile_endpoint()
