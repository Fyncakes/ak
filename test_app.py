#!/usr/bin/env python3
"""
FynCakes Application Test Script
Tests all major features without requiring MongoDB
"""

import requests
import time
import sys

def test_application():
    base_url = "http://localhost:5001"
    
    print("🧪 Testing FynCakes Application...")
    print("=" * 50)
    
    # Test 1: Homepage
    print("1. Testing Homepage...")
    try:
        response = requests.get(f"{base_url}/", timeout=10)
        if response.status_code == 200:
            print("   ✅ Homepage loads successfully")
            if "FynCakes" in response.text and "Welcome to FynCakes" in response.text:
                print("   ✅ Homepage content is correct")
            else:
                print("   ⚠️  Homepage content may be incomplete")
        else:
            print(f"   ❌ Homepage failed with status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Homepage test failed: {e}")
    
    # Test 2: Products Page
    print("\n2. Testing Products Page...")
    try:
        response = requests.get(f"{base_url}/customer", timeout=10)
        if response.status_code == 200:
            print("   ✅ Products page loads successfully")
            if "Our Cakes" in response.text and "Chocolate Delight" in response.text:
                print("   ✅ Sample products are displayed")
            else:
                print("   ⚠️  Products may not be loading correctly")
        else:
            print(f"   ❌ Products page failed with status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Products page test failed: {e}")
    
    # Test 3: About Page
    print("\n3. Testing About Page...")
    try:
        response = requests.get(f"{base_url}/about", timeout=10)
        if response.status_code == 200:
            print("   ✅ About page loads successfully")
            if "Fatima Kolyanga" in response.text and "Aron Kolyanga" in response.text:
                print("   ✅ About page content is correct")
            else:
                print("   ⚠️  About page content may be incomplete")
        else:
            print(f"   ❌ About page failed with status {response.status_code}")
    except Exception as e:
        print(f"   ❌ About page test failed: {e}")
    
    # Test 4: API Endpoint
    print("\n4. Testing API Endpoint...")
    try:
        response = requests.get(f"{base_url}/api/get_cakes", timeout=10)
        if response.status_code == 200:
            print("   ✅ API endpoint responds successfully")
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                print(f"   ✅ API returns {len(data)} cakes")
            else:
                print("   ⚠️  API may not be returning data correctly")
        else:
            print(f"   ❌ API endpoint failed with status {response.status_code}")
    except Exception as e:
        print(f"   ❌ API test failed: {e}")
    
    # Test 5: Static Files
    print("\n5. Testing Static Files...")
    try:
        response = requests.get(f"{base_url}/static/css/main.css", timeout=10)
        if response.status_code == 200:
            print("   ✅ CSS files are accessible")
        else:
            print(f"   ❌ CSS files failed with status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Static files test failed: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Application testing completed!")
    print(f"🌐 Your FynCakes website is running at: {base_url}")
    print("📱 Open this URL in your browser to see the enhanced website!")

if __name__ == "__main__":
    # Wait a moment for the server to start
    print("⏳ Waiting for server to start...")
    time.sleep(2)
    
    try:
        test_application()
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)
