#!/usr/bin/env python3
"""
Test user data and username display
"""

import os
import certifi
from pymongo import MongoClient

def test_user_data():
    """Test user data in MongoDB"""
    print("👤 Testing User Data in MongoDB")
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
        
        # Check users collection
        users = list(db.users.find())
        print(f"\n👥 Users in database: {len(users)}")
        
        for i, user in enumerate(users, 1):
            print(f"\n   User {i}:")
            print(f"     ID: {user.get('_id', 'N/A')}")
            print(f"     Username: {user.get('username', 'N/A')}")
            print(f"     First Name: {user.get('first_name', 'N/A')}")
            print(f"     Last Name: {user.get('last_name', 'N/A')}")
            print(f"     Email: {user.get('email', 'N/A')}")
            print(f"     Role: {user.get('role', 'N/A')}")
            print(f"     Is Student: {user.get('is_student', 'N/A')}")
        
        # Check if there are any users with missing names
        users_without_names = [user for user in users if not user.get('first_name') and not user.get('username')]
        if users_without_names:
            print(f"\n⚠️  {len(users_without_names)} users without first_name or username")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_user_data()
