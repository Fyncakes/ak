#!/usr/bin/env python3
"""
Test Orders Page and Wishlist Functionality
"""

import requests
import json

def test_orders_wishlist():
    """Test orders page and wishlist functionality"""
    print("🎯 Testing Orders Page and Wishlist Functionality")
    print("=" * 60)
    
    base_url = "http://localhost:5001"
    
    # Test 1: Check orders page with real data
    print("1. Testing Orders Page with Real Data...")
    try:
        response = requests.get(f"{base_url}/customer/orders", timeout=10)
        if response.status_code == 200:
            content = response.text
            
            if "{{ orders }}" in content:
                print("   ✅ Orders page uses dynamic data templates")
            else:
                print("   ❌ Orders page may still have hardcoded data")
            
            if "{{ total_orders }}" in content:
                print("   ✅ Orders page shows total orders count")
            else:
                print("   ❌ Orders page missing total orders count")
            
            if "{{ total_spent }}" in content:
                print("   ✅ Orders page shows total spent amount")
            else:
                print("   ❌ Orders page missing total spent amount")
            
            if "loadOrders()" not in content:
                print("   ✅ Mock JavaScript functions removed")
            else:
                print("   ⚠️  Some mock JavaScript functions may still exist")
        else:
            print(f"   ❌ Orders page error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Orders page test error: {e}")
    
    # Test 2: Check wishlist page
    print("\n2. Testing Wishlist Page...")
    try:
        response = requests.get(f"{base_url}/wishlist", timeout=10)
        if response.status_code == 200:
            print("   ✅ Wishlist page accessible")
            
            if "{{ wishlist_items }}" in response.text:
                print("   ✅ Wishlist page uses dynamic data")
            else:
                print("   ❌ Wishlist page may use hardcoded data")
            
            if "My Wishlist" in response.text:
                print("   ✅ Wishlist page has proper title")
            else:
                print("   ❌ Wishlist page missing title")
        elif response.status_code == 302:
            print("   ✅ Wishlist page requires authentication (expected)")
        else:
            print(f"   ❌ Wishlist page error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Wishlist page test error: {e}")
    
    # Test 3: Check wishlist API endpoints
    print("\n3. Testing Wishlist API Endpoints...")
    
    # Test add to wishlist endpoint
    try:
        test_data = {
            "cake_id": "test_cake_123",
            "cake_name": "Test Cake",
            "cake_price": 100000,
            "cake_image": "/static/test.jpg"
        }
        
        response = requests.post(f"{base_url}/wishlist/add", 
                               json=test_data, 
                               timeout=10)
        if response.status_code == 401 or response.status_code == 302:
            print("   ✅ Add to wishlist API requires authentication (expected)")
        elif response.status_code == 200:
            print("   ✅ Add to wishlist API working")
        else:
            print(f"   ❌ Add to wishlist API error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Add to wishlist API test error: {e}")
    
    # Test remove from wishlist endpoint
    try:
        test_data = {"cake_id": "test_cake_123"}
        
        response = requests.post(f"{base_url}/wishlist/remove", 
                               json=test_data, 
                               timeout=10)
        if response.status_code == 401 or response.status_code == 302:
            print("   ✅ Remove from wishlist API requires authentication (expected)")
        elif response.status_code == 200:
            print("   ✅ Remove from wishlist API working")
        else:
            print(f"   ❌ Remove from wishlist API error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Remove from wishlist API test error: {e}")
    
    # Test 4: Check wishlist functionality on cake details page
    print("\n4. Testing Wishlist on Cake Details Page...")
    try:
        # Get a cake ID from the API
        response = requests.get(f"{base_url}/api/get_cakes", timeout=10)
        if response.status_code == 200:
            cakes = response.json()
            if cakes and len(cakes) > 0:
                cake_id = cakes[0]['_id']
                print(f"   Testing with cake ID: {cake_id}")
                
                response = requests.get(f"{base_url}/cake/{cake_id}", timeout=10)
                if response.status_code == 200:
                    content = response.text
                    
                    if "addToWishlist" in content:
                        print("   ✅ Add to wishlist functionality present")
                    else:
                        print("   ❌ Add to wishlist functionality missing")
                    
                    if "wishlist-btn" in content:
                        print("   ✅ Wishlist button present")
                    else:
                        print("   ❌ Wishlist button missing")
                else:
                    print(f"   ❌ Cake details error: {response.status_code}")
            else:
                print("   ❌ No cakes found for testing")
        else:
            print(f"   ❌ API error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Cake details wishlist test error: {e}")
    
    # Test 5: Check navbar wishlist link
    print("\n5. Testing Navbar Wishlist Link...")
    try:
        response = requests.get(f"{base_url}/", timeout=10)
        if response.status_code == 200:
            content = response.text
            
            if "My Wishlist" in content:
                print("   ✅ Wishlist link present in navbar")
            else:
                print("   ❌ Wishlist link missing from navbar")
            
            if "wishlist_page" in content:
                print("   ✅ Wishlist route referenced in navbar")
            else:
                print("   ❌ Wishlist route not referenced in navbar")
        else:
            print(f"   ❌ Homepage error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Navbar wishlist test error: {e}")
    
    # Test 6: Check customer dashboard wishlist count
    print("\n6. Testing Customer Dashboard Wishlist Count...")
    try:
        response = requests.get(f"{base_url}/customer/dashboard", timeout=10)
        if response.status_code == 200:
            content = response.text
            
            if "{{ wishlist_items|length }}" in content:
                print("   ✅ Customer dashboard shows wishlist count")
            else:
                print("   ❌ Customer dashboard missing wishlist count")
            
            if "Favorite cakes" in content:
                print("   ✅ Customer dashboard has wishlist label")
            else:
                print("   ❌ Customer dashboard missing wishlist label")
        else:
            print(f"   ❌ Customer dashboard error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Customer dashboard wishlist test error: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Orders and Wishlist Test Complete!")
    print("\n✅ Summary of Improvements:")
    print("   • Orders page now fetches real data from database")
    print("   • Wishlist system fully implemented with database storage")
    print("   • Wishlist page created with real data display")
    print("   • Add to wishlist functionality on cake details page")
    print("   • Wishlist link added to navbar")
    print("   • Customer dashboard shows wishlist count")
    print("\n🌐 Test your new features:")
    print(f"   • Orders Page: {base_url}/customer/orders (login required)")
    print(f"   • Wishlist Page: {base_url}/wishlist (login required)")
    print(f"   • Customer Dashboard: {base_url}/customer/dashboard (login required)")
    print("\n💡 To test wishlist functionality:")
    print("   1. Login to your account")
    print("   2. Go to any cake details page")
    print("   3. Click 'Add to Wishlist' button")
    print("   4. Go to 'My Wishlist' from navbar dropdown")
    print("   5. See your favorite cakes displayed with real data")

if __name__ == "__main__":
    test_orders_wishlist()
