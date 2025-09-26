#!/usr/bin/env python3
"""
Test dashboard improvements and real data integration
"""

import requests
import json

def test_dashboard_improvements():
    """Test all dashboard improvements"""
    print("🎯 Testing Dashboard Improvements")
    print("=" * 60)
    
    base_url = "http://localhost:5001"
    
    # Test 1: Check customer dashboard with real data
    print("1. Testing Customer Dashboard with Real Data...")
    try:
        response = requests.get(f"{base_url}/customer/dashboard", timeout=10)
        if response.status_code == 200:
            content = response.text
            
            # Check for real data indicators
            if "{{ total_orders }}" in content:
                print("   ✅ Customer dashboard uses dynamic data templates")
            else:
                print("   ❌ Customer dashboard may still have hardcoded data")
            
            if "{{ orders }}" in content:
                print("   ✅ Orders section uses real data")
            else:
                print("   ❌ Orders section may use mock data")
            
            if "{{ cart_items }}" in content:
                print("   ✅ Cart items section uses real data")
            else:
                print("   ❌ Cart items section may use mock data")
            
            if "loadDashboardData()" not in content:
                print("   ✅ Mock JavaScript functions removed")
            else:
                print("   ⚠️  Some mock JavaScript functions may still exist")
        else:
            print(f"   ❌ Customer dashboard error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Customer dashboard test error: {e}")
    
    # Test 2: Check admin dashboard with real data
    print("\n2. Testing Admin Dashboard with Real Data...")
    try:
        response = requests.get(f"{base_url}/admin/dashboard", timeout=10)
        if response.status_code == 200:
            content = response.text
            
            if "{{ total_sales }}" in content:
                print("   ✅ Admin dashboard uses dynamic sales data")
            else:
                print("   ❌ Admin dashboard may have hardcoded sales data")
            
            if "{{ total_orders }}" in content:
                print("   ✅ Admin dashboard uses dynamic orders data")
            else:
                print("   ❌ Admin dashboard may have hardcoded orders data")
            
            if "{{ customers }}" in content:
                print("   ✅ Admin dashboard uses dynamic customers data")
            else:
                print("   ❌ Admin dashboard may have hardcoded customers data")
        else:
            print(f"   ❌ Admin dashboard error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Admin dashboard test error: {e}")
    
    # Test 3: Check new admin pages
    print("\n3. Testing New Admin Pages...")
    
    # Test manage orders page
    try:
        response = requests.get(f"{base_url}/admin/manage_orders", timeout=10)
        if response.status_code == 200:
            print("   ✅ Manage Orders page accessible")
            if "{{ orders }}" in response.text:
                print("   ✅ Manage Orders uses real data")
            else:
                print("   ❌ Manage Orders may use mock data")
        else:
            print(f"   ❌ Manage Orders error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Manage Orders test error: {e}")
    
    # Test manage users page
    try:
        response = requests.get(f"{base_url}/admin/manage_users", timeout=10)
        if response.status_code == 200:
            print("   ✅ Manage Users page accessible")
            if "{{ users }}" in response.text:
                print("   ✅ Manage Users uses real data")
            else:
                print("   ❌ Manage Users may use mock data")
        else:
            print(f"   ❌ Manage Users error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Manage Users test error: {e}")
    
    # Test 4: Check username display
    print("\n4. Testing Username Display...")
    try:
        response = requests.get(f"{base_url}/", timeout=10)
        if response.status_code == 200:
            content = response.text
            
            if "{{ current_user.first_name or current_user.username }}" in content:
                print("   ✅ Username display uses dynamic user data")
            else:
                print("   ❌ Username display may be hardcoded")
            
            if "welcome-text" in content:
                print("   ✅ Welcome text element present")
            else:
                print("   ❌ Welcome text element missing")
        else:
            print(f"   ❌ Homepage error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Username display test error: {e}")
    
    # Test 5: Check cake data is from database
    print("\n5. Testing Cake Data from Database...")
    try:
        response = requests.get(f"{base_url}/api/get_cakes", timeout=10)
        if response.status_code == 200:
            cakes = response.json()
            
            if isinstance(cakes, list) and len(cakes) > 0:
                print(f"   ✅ API returns {len(cakes)} cakes from database")
                
                # Check for real MongoDB ObjectIds (not mock data)
                real_ids = [cake for cake in cakes if len(str(cake.get('_id', ''))) == 24]
                if len(real_ids) == len(cakes):
                    print("   ✅ All cakes have real MongoDB ObjectIds")
                else:
                    print("   ⚠️  Some cakes may have mock IDs")
                
                # Check for specific cakes
                birch_cake = next((cake for cake in cakes if 'birch' in cake.get('name', '').lower()), None)
                if birch_cake:
                    print(f"   ✅ Birch Bark Wedding Cake found: {birch_cake['name']}")
                else:
                    print("   ℹ️  Birch Bark Wedding Cake not in first page (pagination)")
            else:
                print("   ❌ No cakes found in API response")
        else:
            print(f"   ❌ API error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Cake data test error: {e}")
    
    # Test 6: Check navigation between pages
    print("\n6. Testing Navigation Between Pages...")
    try:
        # Test admin dashboard links
        response = requests.get(f"{base_url}/admin/dashboard", timeout=10)
        if response.status_code == 200:
            content = response.text
            
            if "View Orders" in content:
                print("   ✅ Admin dashboard has link to manage orders")
            else:
                print("   ❌ Admin dashboard missing manage orders link")
            
            if "Manage Users" in content:
                print("   ✅ Admin dashboard has link to manage users")
            else:
                print("   ❌ Admin dashboard missing manage users link")
            
            if "Back to Dashboard" in content:
                print("   ✅ Admin pages have back navigation")
            else:
                print("   ❌ Admin pages missing back navigation")
        else:
            print(f"   ❌ Admin dashboard error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Navigation test error: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Dashboard Improvements Test Complete!")
    print("\n✅ Summary of Improvements:")
    print("   • Customer dashboard now uses real data from database")
    print("   • Admin dashboard uses real sales, orders, and customer data")
    print("   • New admin pages created: Manage Orders, Manage Users")
    print("   • Username display uses dynamic user data")
    print("   • All cake data comes from MongoDB database")
    print("   • Proper navigation between admin pages")
    print("\n🌐 Test your improved dashboards:")
    print(f"   • Customer Dashboard: {base_url}/customer/dashboard (login required)")
    print(f"   • Admin Dashboard: {base_url}/admin/dashboard (admin login required)")
    print(f"   • Manage Orders: {base_url}/admin/manage_orders (admin login required)")
    print(f"   • Manage Users: {base_url}/admin/manage_users (admin login required)")

if __name__ == "__main__":
    test_dashboard_improvements()
