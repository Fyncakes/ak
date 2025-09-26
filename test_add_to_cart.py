#!/usr/bin/env python3
"""
Test Add to Cart functionality
"""

import requests
import json

def test_add_to_cart():
    """Test the Add to Cart functionality"""
    print("🛒 Testing Add to Cart Functionality")
    print("=" * 50)
    
    base_url = "http://localhost:5001"
    
    # Test 1: Check if Add to Cart buttons are present
    print("1. Testing Add to Cart Buttons...")
    try:
        response = requests.get(f"{base_url}/customer", timeout=10)
        if response.status_code == 200:
            if "quickAddToCart" in response.text:
                print("   ✅ Add to Cart buttons present in customer page")
            else:
                print("   ❌ Add to Cart buttons missing from customer page")
            
            if "quick-cart-btn" in response.text:
                print("   ✅ Quick cart button classes present")
            else:
                print("   ❌ Quick cart button classes missing")
        else:
            print(f"   ❌ Customer page error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Customer page test error: {e}")
    
    # Test 2: Check wedding gallery Add to Cart
    print("\n2. Testing Wedding Gallery Add to Cart...")
    try:
        response = requests.get(f"{base_url}/wedding-cakes", timeout=10)
        if response.status_code == 200:
            if "quickAddToCart" in response.text:
                print("   ✅ Add to Cart buttons present in wedding gallery")
            else:
                print("   ❌ Add to Cart buttons missing from wedding gallery")
            
            if "quick-add-btn" in response.text:
                print("   ✅ Quick add button classes present")
            else:
                print("   ❌ Quick add button classes missing")
        else:
            print(f"   ❌ Wedding gallery error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Wedding gallery test error: {e}")
    
    # Test 3: Check cake details Add to Cart
    print("\n3. Testing Cake Details Add to Cart...")
    try:
        # Get a cake ID from the API
        response = requests.get(f"{base_url}/api/get_cakes", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('cakes'):
                cake_id = data['cakes'][0]['_id']
                print(f"   Testing with cake ID: {cake_id}")
                
                # Test cake details page
                response = requests.get(f"{base_url}/cake/{cake_id}", timeout=10)
                if response.status_code == 200:
                    if "addToCart" in response.text:
                        print("   ✅ Add to Cart functionality present in cake details")
                    else:
                        print("   ❌ Add to Cart functionality missing from cake details")
                else:
                    print(f"   ❌ Cake details error: {response.status_code}")
            else:
                print("   ❌ No cakes found in API response")
        else:
            print(f"   ❌ API error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Cake details test error: {e}")
    
    # Test 4: Check cart API endpoint
    print("\n4. Testing Cart API Endpoint...")
    try:
        response = requests.get(f"{base_url}/cart/items", timeout=10)
        if response.status_code == 302:
            print("   ✅ Cart API requires authentication (redirect)")
        elif response.status_code == 200:
            print("   ✅ Cart API accessible")
        else:
            print(f"   ❌ Cart API error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Cart API test error: {e}")
    
    # Test 5: Check if specific cakes are in the database
    print("\n5. Testing Specific Cakes...")
    try:
        response = requests.get(f"{base_url}/api/get_cakes", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('cakes'):
                cakes = data['cakes']
                
                # Check for Birch Bark Wedding Cake
                birch_cake = next((cake for cake in cakes if 'birch' in cake.get('name', '').lower()), None)
                if birch_cake:
                    print(f"   ✅ Birch Bark Wedding Cake found: {birch_cake['name']}")
                    print(f"      Price: {birch_cake.get('price', 'N/A')}")
                    print(f"      Category: {birch_cake.get('category', 'N/A')}")
                else:
                    print("   ❌ Birch Bark Wedding Cake not found")
                
                # Check for Naked Cake
                naked_cake = next((cake for cake in cakes if 'naked' in cake.get('name', '').lower()), None)
                if naked_cake:
                    print(f"   ✅ Naked Cake found: {naked_cake['name']}")
                    print(f"      Price: {naked_cake.get('price', 'N/A')}")
                    print(f"      Category: {naked_cake.get('category', 'N/A')}")
                else:
                    print("   ❌ Naked Cake not found")
            else:
                print("   ❌ No cakes found in API response")
        else:
            print(f"   ❌ API error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Specific cakes test error: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Add to Cart Test Complete!")
    print("\n💡 If Add to Cart is not working:")
    print("   1. Make sure you're logged in")
    print("   2. Check browser console for JavaScript errors")
    print("   3. Verify the cart API endpoint is working")
    print("   4. Check if the cake data is properly formatted")

if __name__ == "__main__":
    test_add_to_cart()
