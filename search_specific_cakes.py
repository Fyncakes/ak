#!/usr/bin/env python3
"""
Search for specific cakes in MongoDB
"""

import os
import certifi
from pymongo import MongoClient

def search_specific_cakes():
    """Search for specific cakes in MongoDB"""
    print("🔍 Searching for Specific Cakes in MongoDB")
    print("=" * 50)
    
    try:
        mongo_uri = os.environ.get('MONGO_URI', 'mongodb+srv://fyncakes_user:<db_password>@fyncakes-cluster.sfxujh9.mongodb.net/?retryWrites=true&w=majority&appName=fyncakes-cluster')
        
        if '<db_password>' in mongo_uri:
            print("❌ Password placeholder not replaced in MONGO_URI")
            return
        
        client = MongoClient(mongo_uri, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        db = client.fyncakes
        
        print("✅ Connected to MongoDB Atlas successfully!")
        
        # Search for Birch Bark Wedding Cake
        print("\n🔍 Searching for Birch Bark Wedding Cake...")
        birch_cakes = list(db.cakes.find({'name': {'$regex': 'birch', '$options': 'i'}}))
        if birch_cakes:
            for cake in birch_cakes:
                print(f"   ✅ Found: {cake['name']}")
                print(f"      ID: {cake['_id']}")
                print(f"      Price: {cake.get('price', 'N/A')}")
                print(f"      Category: {cake.get('category', 'N/A')}")
                print(f"      Image: {cake.get('image', 'N/A')}")
        else:
            print("   ❌ No Birch Bark Wedding Cake found")
        
        # Search for Naked Cake
        print("\n🔍 Searching for Naked Cake...")
        naked_cakes = list(db.cakes.find({'name': {'$regex': 'naked', '$options': 'i'}}))
        if naked_cakes:
            for cake in naked_cakes:
                print(f"   ✅ Found: {cake['name']}")
                print(f"      ID: {cake['_id']}")
                print(f"      Price: {cake.get('price', 'N/A')}")
                print(f"      Category: {cake.get('category', 'N/A')}")
                print(f"      Image: {cake.get('image', 'N/A')}")
        else:
            print("   ❌ No Naked Cake found")
        
        # Search for Wedding Cakes
        print("\n🔍 Searching for Wedding Cakes...")
        wedding_cakes = list(db.cakes.find({'category': {'$regex': 'wedding', '$options': 'i'}}))
        print(f"   Found {len(wedding_cakes)} wedding cakes:")
        for cake in wedding_cakes[:5]:  # Show first 5
            print(f"      - {cake['name']} (Shs {cake.get('price', 'N/A')})")
        
        # Check total cakes
        total_cakes = db.cakes.count_documents({})
        print(f"\n📊 Total cakes in database: {total_cakes}")
        
        # Check pagination issue
        print("\n🔍 Checking pagination...")
        first_page = list(db.cakes.find().limit(6))
        print(f"   First 6 cakes:")
        for i, cake in enumerate(first_page, 1):
            print(f"      {i}. {cake['name']} - {cake.get('category', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    search_specific_cakes()
