#!/bin/bash

# Setup script for AI Pair-Programmer Interview Room

echo "🚀 Setting up AI Pair-Programmer Interview Room..."
echo ""

# Check Python installation
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "✓ Python 3 found"

# Check Node.js installation
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 16 or higher."
    exit 1
fi

echo "✓ Node.js found"

# Create virtual environment
echo ""
echo "📦 Creating Python virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
echo "📥 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your Groq API key!"
    echo "    Get your key at: https://console.groq.com"
fi

# Install frontend dependencies
echo ""
echo "📦 Installing frontend dependencies..."
cd client
npm install
cd ..

# Create sessions directory
echo ""
echo "📁 Creating sessions directory..."
mkdir -p sessions

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your GROQ_API_KEY (get it at https://console.groq.com)"
echo "2. Start the backend: source venv/bin/activate && uvicorn backend.main:app --reload"
echo "3. In a new terminal, start the frontend: cd client && npm start"
echo "4. Open http://localhost:3000 in your browser"
echo ""
echo "Happy interviewing! 🎉"
