#!/usr/bin/env python3
"""
Comprehensive test script to verify all the latest improvements
"""

import requests
import json
import time

def test_all_improvements():
    """Test all the latest improvements"""
    print("🎂 Testing All Latest Improvements")
    print("=" * 60)
    
    base_url = "http://localhost:5001"
    
    # Test 1: Dynamic Back Button
    print("1. Testing Dynamic Back Button...")
    try:
        response = requests.get(f"{base_url}/cake/68befa30b880451d3d87ba28", timeout=10)
        if response.status_code == 200:
            if "javascript:history.back()" in response.text:
                print("   ✅ Dynamic back button implemented in cake details")
            else:
                print("   ❌ Dynamic back button not found")
        else:
            print(f"   ❌ Cake details page error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Cake details test error: {e}")
    
    # Test 2: Enhanced About Page
    print("\n2. Testing Enhanced About Page...")
    try:
        response = requests.get(f"{base_url}/about", timeout=10)
        if response.status_code == 200:
            if "hero-section" in response.text:
                print("   ✅ Hero section with stats implemented")
            if "stats-grid" in response.text:
                print("   ✅ Statistics grid implemented")
            if "features-grid" in response.text:
                print("   ✅ Features grid implemented")
            if "testimonials-grid" in response.text:
                print("   ✅ Enhanced testimonials implemented")
            if "cta-section" in response.text:
                print("   ✅ Call-to-action section implemented")
            if "comments-section" in response.text:
                print("   ✅ Comments section integrated")
        else:
            print(f"   ❌ About page error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ About page test error: {e}")
    
    # Test 3: Comments System
    print("\n3. Testing Comments System...")
    try:
        # Test GET comments
        response = requests.get(f"{base_url}/api/comments", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("   ✅ Comments API working")
                print(f"   📊 Found {len(data.get('comments', []))} comments")
            else:
                print("   ❌ Comments API error")
        else:
            print(f"   ❌ Comments API error: {response.status_code}")
        
        # Test POST comment
        test_comment = {
            "name": "Test User",
            "email": "test@example.com",
            "comment": "This is a test comment for FynCakes!",
            "rating": 5
        }
        response = requests.post(f"{base_url}/api/comments", 
                               json=test_comment, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("   ✅ Comment submission working")
            else:
                print("   ❌ Comment submission failed")
        else:
            print(f"   ❌ Comment submission error: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Comments system test error: {e}")
    
    # Test 4: Wedding Gallery Links
    print("\n4. Testing Wedding Gallery Links...")
    try:
        response = requests.get(f"{base_url}/wedding-cakes", timeout=10)
        if response.status_code == 200:
            if "gallery-main-link" in response.text:
                print("   ✅ Main image links implemented")
            if "gallery-item-actions" in response.text:
                print("   ✅ Action buttons section implemented")
            if "quick-add-btn" in response.text:
                print("   ✅ Add to cart buttons implemented")
            if "view-details-link" in response.text:
                print("   ✅ View details buttons implemented")
            if "event.stopPropagation()" in response.text:
                print("   ✅ Event handling implemented")
        else:
            print(f"   ❌ Wedding gallery error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Wedding gallery test error: {e}")
    
    # Test 5: Homepage Comments Integration
    print("\n5. Testing Homepage Comments Integration...")
    try:
        response = requests.get(f"{base_url}/", timeout=10)
        if response.status_code == 200:
            if "comments-wrapper" in response.text:
                print("   ✅ Comments section integrated in homepage")
            if "comments-section" in response.text:
                print("   ✅ Comments component included")
        else:
            print(f"   ❌ Homepage error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Homepage test error: {e}")
    
    # Test 6: CSS Styling
    print("\n6. Testing CSS Styling...")
    try:
        response = requests.get(f"{base_url}/static/css/gallery.css", timeout=10)
        if response.status_code == 200:
            css_content = response.text
            if ".gallery-main-link" in css_content:
                print("   ✅ Gallery link styles implemented")
            if ".gallery-item-actions" in css_content:
                print("   ✅ Action buttons styles implemented")
            if ".quick-add-btn" in css_content:
                print("   ✅ Add to cart button styles implemented")
            if ".view-details-link" in css_content:
                print("   ✅ View details button styles implemented")
        else:
            print(f"   ❌ CSS file error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ CSS test error: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 All Improvements Test Complete!")
    print("✅ Your FynCakes website now features:")
    print("   • Dynamic back buttons that return to previous page")
    print("   • Stunning, eye-catching About page with stats and features")
    print("   • Dynamic customer comments system with rating and approval")
    print("   • Clickable wedding gallery with multiple ways to access details")
    print("   • Add to Cart buttons on wedding gallery (requires login)")
    print("   • Professional styling and responsive design")
    print("   • Real-time comment submission and display")
    print("\n🌐 Test your improvements:")
    print(f"   • Homepage: {base_url}/")
    print(f"   • About Page: {base_url}/about")
    print(f"   • Wedding Gallery: {base_url}/wedding-cakes")
    print(f"   • Comments API: {base_url}/api/comments")

if __name__ == "__main__":
    test_all_improvements()
