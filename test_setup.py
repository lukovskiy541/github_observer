#!/usr/bin/env python3
"""
Simple test script to verify the bot components work correctly.
Run this before starting the bot to check your setup.
"""

import os
import sys
from dotenv import load_dotenv

def test_env_vars():
    """Test that all required environment variables are set."""
    print("🔍 Checking environment variables...")
    load_dotenv()
    
    required = ['TELEGRAM_TOKEN', 'GOOGLE_API_KEY']
    optional = ['GITHUB_TOKEN']
    
    missing = []
    for var in required:
        if not os.getenv(var):
            missing.append(var)
            print(f"  ❌ {var}: NOT SET")
        else:
            print(f"  ✅ {var}: SET")
    
    for var in optional:
        if not os.getenv(var):
            print(f"  ⚠️  {var}: NOT SET (optional, but recommended)")
        else:
            print(f"  ✅ {var}: SET")
    
    if missing:
        print(f"\n❌ Missing required variables: {', '.join(missing)}")
        return False
    
    print("\n✅ All required environment variables are set!")
    return True

def test_imports():
    """Test that all required packages are installed."""
    print("\n🔍 Checking package imports...")
    
    packages = [
        ('telegram', 'python-telegram-bot'),
        ('google.generativeai', 'google-generativeai'),
        ('github', 'PyGithub'),
        ('dotenv', 'python-dotenv'),
    ]
    
    missing = []
    for module, package in packages:
        try:
            __import__(module)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package}")
            missing.append(package)
    
    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print("Run: uv pip install -r requirements.txt")
        return False
    
    print("\n✅ All packages are installed!")
    return True

def test_github_client():
    """Test GitHub client."""
    print("\n🔍 Testing GitHub client...")
    
    try:
        from github_client import GitHubClient
        
        github_token = os.getenv('GITHUB_TOKEN')
        client = GitHubClient(github_token)
        
        # Test with a known user
        result = client.get_user_summary('octocat')
        
        if 'octocat' in result.lower():
            print("  ✅ GitHub client works!")
            return True
        else:
            print("  ❌ GitHub client returned unexpected result")
            return False
            
    except Exception as e:
        print(f"  ❌ GitHub client error: {e}")
        return False

def test_ai_agent():
    """Test AI agent initialization."""
    print("\n🔍 Testing AI agent...")
    
    try:
        from ai_agent import AIAgent
        
        github_token = os.getenv('GITHUB_TOKEN')
        agent = AIAgent(github_token)
        
        print("  ✅ AI agent initialized successfully!")
        return True
        
    except Exception as e:
        print(f"  ❌ AI agent error: {e}")
        return False

def main():
    print("=" * 50)
    print("AI Recruiter Bot - Setup Test")
    print("=" * 50)
    
    results = []
    
    results.append(test_env_vars())
    results.append(test_imports())
    
    if all(results):
        results.append(test_github_client())
        results.append(test_ai_agent())
    
    print("\n" + "=" * 50)
    if all(results):
        print("✅ All tests passed! You're ready to run the bot.")
        print("\nStart the bot with: uv run python bot.py")
        return 0
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
