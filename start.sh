#!/bin/bash

# Start script for AI Pair-Programmer Interview Room

echo "🚀 Starting AI Pair-Programmer Interview Room..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "Please run ./setup.sh first or create .env from .env.example"
    echo "Don't forget to add your Groq API key (get it at https://console.groq.com)"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run ./setup.sh first"
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Start backend in background
echo "🐍 Starting backend server..."
uvicorn backend.main:app --reload --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 3

# Start frontend
echo "⚛️  Starting frontend..."
cd client
npm start

# Cleanup on exit
trap "echo ''; echo '🛑 Shutting down...'; kill $BACKEND_PID; exit" INT TERM

wait
