#!/bin/bash

# Script to set MongoDB Atlas password
# Usage: ./set_mongo_password.sh YOUR_ACTUAL_PASSWORD

if [ -z "$1" ]; then
    echo "❌ Please provide your MongoDB Atlas password"
    echo "Usage: ./set_mongo_password.sh YOUR_ACTUAL_PASSWORD"
    echo ""
    echo "Example: ./set_mongo_password.sh mypassword123"
    exit 1
fi

PASSWORD="$1"
MONGO_URI="mongodb+srv://fyncakes_user:${PASSWORD}@fyncakes-cluster.sfxujh9.mongodb.net/?retryWrites=true&w=majority&appName=fyncakes-cluster"

echo "🔧 Setting MongoDB Atlas connection string..."
export MONGO_URI="$MONGO_URI"

echo "✅ MongoDB Atlas URI set successfully!"
echo "🚀 Starting FynCakes application..."

# Start the application
cd "$(dirname "$0")"
source venv/bin/activate
python main.py
