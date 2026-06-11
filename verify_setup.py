#!/usr/bin/env python3
"""
Test script to verify the AI Pair-Programmer Interview Room setup
"""

import sys
import os

def check_python_version():
    """Check Python version"""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"  ✓ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"  ✗ Python {version.major}.{version.minor}.{version.micro} (requires 3.8+)")
        return False

def check_dependencies():
    """Check if required Python packages are installed"""
    print("\n📦 Checking Python dependencies...")
    
    required_packages = [
        'fastapi',
        'uvicorn',
        'langchain',
        'langgraph',
        'crewai',
        'openai',
        'dotenv'
    ]
    
    all_installed = True
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package} (not installed)")
            all_installed = False
    
    return all_installed

def check_env_file():
    """Check if .env file exists and has required variables"""
    print("\n🔐 Checking environment configuration...")
    
    if not os.path.exists('.env'):
        print("  ✗ .env file not found")
        print("     Run: cp .env.example .env")
        return False
    
    print("  ✓ .env file exists")
    
    with open('.env', 'r') as f:
        content = f.read()
        
    env_valid = True
    if 'GROQ_API_KEY=your_groq_api_key_here' in content or 'GROQ_API_KEY=' not in content:
        print("  ⚠️  GROQ_API_KEY not set in .env")
        print("     Get your key at: https://console.groq.com")
        env_valid = False
    else:
        print("  ✓ GROQ_API_KEY configured")

    optional_keys = [
        ("MISTRAL_API_KEY", "https://console.mistral.ai"),
        ("GOOGLE_GEMINI_API_KEY", "https://console.cloud.google.com/vertex-ai")
    ]
    for key, source in optional_keys:
        if f"{key}=your" in content or f"{key}=" not in content:
            print(f"  ⚠️  {key} not set in .env (multi-LLM benefits will be limited)")
            print(f"     Get credentials at: {source}")
        else:
            print(f"  ✓ {key} configured")

    return env_valid

def check_backend_structure():
    """Check if backend files exist"""
    print("\n📂 Checking backend structure...")
    
    required_files = [
        'backend/__init__.py',
        'backend/main.py',
        'backend/workflows/interview_graph.py',
        'backend/agents/evaluation_crew.py',
        'backend/services/code_executor.py',
        'backend/services/session_manager.py'
    ]
    
    all_exist = True
    for file in required_files:
        if os.path.exists(file):
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ {file}")
            all_exist = False
    
    return all_exist

def check_frontend_structure():
    """Check if frontend files exist"""
    print("\n⚛️  Checking frontend structure...")
    
    required_files = [
        'client/package.json',
        'client/src/App.js',
        'client/src/components/StartScreen.js',
        'client/src/components/InterviewRoom.js',
        'client/src/components/EvaluationReport.js'
    ]
    
    all_exist = True
    for file in required_files:
        if os.path.exists(file):
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ {file}")
            all_exist = False
    
    return all_exist

def main():
    print("=" * 60)
    print("AI Pair-Programmer Interview Room - Setup Verification")
    print("=" * 60)
    
    checks = [
        check_python_version(),
        check_dependencies(),
        check_env_file(),
        check_backend_structure(),
        check_frontend_structure()
    ]
    
    print("\n" + "=" * 60)
    
    if all(checks):
        print("✅ All checks passed! You're ready to go.")
        print("\nNext steps:")
        print("1. Make sure GROQ_API_KEY, MISTRAL_API_KEY, and GOOGLE_GEMINI_API_KEY are set in .env (see README)")
        print("2. Start backend: source venv/bin/activate && uvicorn backend.main:app --reload")
        print("3. Start frontend: cd client && npm start")
        print("4. Open http://localhost:3000")
    else:
        print("❌ Some checks failed. Please review the errors above.")
        print("\nTo fix issues:")
        print("1. Run ./setup.sh to install dependencies")
        print("2. Create .env from .env.example and add your Groq, Mistral, and Gemini API keys")
        print("3. Verify all files are present")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
