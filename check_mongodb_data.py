#!/usr/bin/env python3
"""
Check MongoDB Atlas data and collections
"""

import os
import certifi
from pymongo import MongoClient

def check_mongodb_data():
    """Check what data is available in MongoDB Atlas"""
    print("🔍 Checking MongoDB Atlas Data")
    print("=" * 50)
    
    try:
        # Use the same connection string as in __init__.py
        mongo_uri = os.environ.get('MONGO_URI', 'mongodb+srv://fyncakes_user:<db_password>@fyncakes-cluster.sfxujh9.mongodb.net/?retryWrites=true&w=majority&appName=fyncakes-cluster')
        
        if '<db_password>' in mongo_uri:
            print("❌ Password placeholder not replaced in MONGO_URI")
            print("   Please set your MongoDB Atlas password")
            return
        
        client = MongoClient(mongo_uri, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        db = client.fyncakes
        
        print("✅ Connected to MongoDB Atlas successfully!")
        print(f"   Database: {db.name}")
        
        # List all collections
        collections = db.list_collection_names()
        print(f"   Collections: {collections}")
        
        # Check cakes collection
        if 'cakes' in collections:
            cakes_count = db.cakes.count_documents({})
            print(f"\n📊 Cakes Collection:")
            print(f"   Total cakes: {cakes_count}")
            
            # Show sample cakes
            sample_cakes = list(db.cakes.find().limit(3))
            for i, cake in enumerate(sample_cakes, 1):
                print(f"\n   Cake {i}:")
                print(f"     Name: {cake.get('name', 'N/A')}")
                print(f"     Category: {cake.get('category', 'N/A')}")
                print(f"     Price: {cake.get('price', 'N/A')}")
                print(f"     Image: {cake.get('image', 'N/A')}")
                print(f"     ID: {cake.get('_id', 'N/A')}")
        
        # Check other collections
        for collection_name in collections:
            if collection_name != 'cakes':
                count = db[collection_name].count_documents({})
                print(f"\n📊 {collection_name.title()} Collection: {count} documents")
        
        # Check if we need to add more cake data
        if 'cakes' in collections:
            cakes = list(db.cakes.find())
            print(f"\n🔍 Current Cake Data Analysis:")
            print(f"   Total cakes in database: {len(cakes)}")
            
            # Check for specific cakes mentioned
            birch_cake = db.cakes.find_one({'name': {'$regex': 'birch', '$options': 'i'}})
            naked_cake = db.cakes.find_one({'name': {'$regex': 'naked', '$options': 'i'}})
            
            if birch_cake:
                print(f"   ✅ Birch Bark Wedding Cake found: {birch_cake['name']}")
            else:
                print(f"   ❌ Birch Bark Wedding Cake not found")
            
            if naked_cake:
                print(f"   ✅ Naked Cake found: {naked_cake['name']}")
            else:
                print(f"   ❌ Naked Cake not found")
            
            # Check if we need to add more data
            if len(cakes) < 10:
                print(f"\n⚠️  Only {len(cakes)} cakes found. Consider adding more sample data.")
        
    except Exception as e:
        print(f"❌ Error connecting to MongoDB: {str(e)}")
        print("   Using mock database instead")

if __name__ == "__main__":
    check_mongodb_data()
