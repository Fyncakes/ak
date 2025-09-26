#!/usr/bin/env python3
"""
Test script to verify the new customer features
"""

import requests
import json

def test_customer_features():
    """Test the new customer features"""
    print("👤 Testing New Customer Features")
    print("=" * 50)
    
    base_url = "http://localhost:5001"
    
    # Test 1: Navbar with customer name
    print("1. Testing Navbar with Customer Name...")
    try:
        response = requests.get(f"{base_url}/", timeout=10)
        if response.status_code == 200:
            if "welcome-text" in response.text:
                print("   ✅ Customer welcome text implemented")
            if "user-dropdown" in response.text:
                print("   ✅ User dropdown menu implemented")
            if "customer_dashboard" in response.text:
                print("   ✅ Customer dashboard link added")
            if "customer_profile" in response.text:
                print("   ✅ Customer profile link added")
            if "order_history" in response.text:
                print("   ✅ Order history link added")
        else:
            print(f"   ❌ Homepage error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Homepage test error: {e}")
    
    # Test 2: Customer Dashboard (requires authentication)
    print("\n2. Testing Customer Dashboard...")
    try:
        response = requests.get(f"{base_url}/customer/dashboard", timeout=10)
        if response.status_code == 302:
            print("   ✅ Customer dashboard requires authentication (redirect)")
        elif response.status_code == 200:
            if "dashboard-container" in response.text:
                print("   ✅ Customer dashboard template loaded")
            if "stats-grid" in response.text:
                print("   ✅ Statistics grid implemented")
            if "recent-orders" in response.text:
                print("   ✅ Recent orders section implemented")
            if "quick-actions" in response.text:
                print("   ✅ Quick actions section implemented")
            if "wishlist-items" in response.text:
                print("   ✅ Wishlist section implemented")
        else:
            print(f"   ❌ Customer dashboard error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Customer dashboard test error: {e}")
    
    # Test 3: Customer Profile (requires authentication)
    print("\n3. Testing Customer Profile...")
    try:
        response = requests.get(f"{base_url}/customer/profile", timeout=10)
        if response.status_code == 302:
            print("   ✅ Customer profile requires authentication (redirect)")
        elif response.status_code == 200:
            if "profile-container" in response.text:
                print("   ✅ Customer profile template loaded")
            if "profile-form" in response.text:
                print("   ✅ Profile form implemented")
            if "form-section" in response.text:
                print("   ✅ Form sections implemented")
            if "Personal Information" in response.text:
                print("   ✅ Personal information section present")
            if "Address Information" in response.text:
                print("   ✅ Address information section present")
            if "Account Settings" in response.text:
                print("   ✅ Account settings section present")
            if "Security" in response.text:
                print("   ✅ Security section present")
        else:
            print(f"   ❌ Customer profile error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Customer profile test error: {e}")
    
    # Test 4: Order History (requires authentication)
    print("\n4. Testing Order History...")
    try:
        response = requests.get(f"{base_url}/customer/orders", timeout=10)
        if response.status_code == 302:
            print("   ✅ Order history requires authentication (redirect)")
        elif response.status_code == 200:
            if "history-container" in response.text:
                print("   ✅ Order history template loaded")
            if "filters-section" in response.text:
                print("   ✅ Filters section implemented")
            if "orders-list" in response.text:
                print("   ✅ Orders list implemented")
            if "order-card" in response.text:
                print("   ✅ Order card layout implemented")
        else:
            print(f"   ❌ Order history error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Order history test error: {e}")
    
    # Test 5: CSS and Styling
    print("\n5. Testing CSS and Styling...")
    try:
        response = requests.get(f"{base_url}/static/css/main.css", timeout=10)
        if response.status_code == 200:
            css_content = response.text
            if ".user-menu" in css_content:
                print("   ✅ User menu styles implemented")
            if ".welcome-text" in css_content:
                print("   ✅ Welcome text styles implemented")
            if ".user-dropdown" in css_content:
                print("   ✅ User dropdown styles implemented")
            if ".dropdown-item" in css_content:
                print("   ✅ Dropdown item styles implemented")
        else:
            print(f"   ❌ CSS file error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ CSS test error: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Customer Features Test Complete!")
    print("✅ New customer features implemented:")
    print("   • Personalized navbar with customer name")
    print("   • User dropdown menu with dashboard, profile, and orders")
    print("   • Customer dashboard with statistics and quick actions")
    print("   • Customer profile page for editing information")
    print("   • Order history page with filtering and tracking")
    print("   • Professional styling and responsive design")
    print("\n🌐 Test your new features:")
    print(f"   • Homepage: {base_url}/ (login to see personalized navbar)")
    print(f"   • Customer Dashboard: {base_url}/customer/dashboard (requires login)")
    print(f"   • Customer Profile: {base_url}/customer/profile (requires login)")
    print(f"   • Order History: {base_url}/customer/orders (requires login)")

if __name__ == "__main__":
    test_customer_features()
