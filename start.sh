#!/bin/bash

# FynCakes Startup Script
echo "🚀 Starting FynCakes Application..."

# Activate virtual environment
source venv/bin/activate

# Set environment variables
export SECRET_KEY="dev-secret-key-change-in-production"
export MONGO_URI="mongodb://localhost:27017/fyncakes"
export MAIL_SERVER="smtp.gmail.com"
export MAIL_PORT="587"
export MAIL_USERNAME=""
export MAIL_PASSWORD=""

# Start the application
echo "✅ Virtual environment activated"
echo "🌐 Starting Flask development server..."
echo "📱 Open your browser and go to: http://localhost:5001"
echo "⏹️  Press Ctrl+C to stop the server"
echo ""

# Set Flask to use port 5001
export FLASK_RUN_PORT=5001
python main.py
