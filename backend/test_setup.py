"""
Setup Verification Script
-------------------------
Run this script to verify that all dependencies are installed correctly
and your environment is properly configured.

Usage: python test_setup.py
"""

import sys

def test_python_version():
    """Check Python version."""
    print("\n" + "="*60)
    print("1. Testing Python Version")
    print("="*60)
    
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major >= 3 and version.minor >= 10:
        print("✓ Python version is compatible (3.10+)")
        return True
    else:
        print("✗ Python 3.10+ is required")
        return False


def test_imports():
    """Test if all required packages are installed."""
    print("\n" + "="*60)
    print("2. Testing Package Imports")
    print("="*60)
    
    packages = {
        'flask': 'Flask',
        'flask_cors': 'Flask-CORS',
        'openai': 'OpenAI',
        'langchain': 'LangChain',
        'chromadb': 'ChromaDB',
        'transformers': 'Transformers (Hugging Face)',
        'sqlalchemy': 'SQLAlchemy',
        'stripe': 'Stripe',
        'dotenv': 'python-dotenv',
    }
    
    all_good = True
    
    for module, name in packages.items():
        try:
            __import__(module)
            print(f"✓ {name} installed")
        except ImportError as e:
            print(f"✗ {name} NOT installed - {e}")
            all_good = False
    
    return all_good


def test_environment_variables():
    """Check if environment variables are set."""
    print("\n" + "="*60)
    print("3. Testing Environment Variables")
    print("="*60)
    
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    required_vars = {
        'OPENAI_API_KEY': 'OpenAI API Key',
        'STRIPE_SECRET_KEY': 'Stripe Secret Key',
        'SECRET_KEY': 'Flask Secret Key'
    }
    
    all_good = True
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value and value != f'your-{var.lower().replace("_", "-")}-here':
            print(f"✓ {description} is set")
        else:
            print(f"✗ {description} is missing or not configured")
            all_good = False
    
    return all_good


def test_config():
    """Test configuration loading."""
    print("\n" + "="*60)
    print("4. Testing Configuration")
    print("="*60)
    
    try:
        from config import get_config
        
        config = get_config('development')
        print(f"✓ Configuration loaded successfully")
        print(f"  Environment: development")
        print(f"  Debug mode: {config.DEBUG}")
        print(f"  Database: {config.SQLALCHEMY_DATABASE_URI}")
        return True
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        return False


def test_flask_app():
    """Test Flask app creation."""
    print("\n" + "="*60)
    print("5. Testing Flask App")
    print("="*60)
    
    try:
        from run import create_app
        
        app = create_app('development')
        print("✓ Flask app created successfully")
        print(f"  App name: {app.name}")
        print(f"  Debug mode: {app.debug}")
        return True
    except Exception as e:
        print(f"✗ Flask app error: {e}")
        return False


def test_openai_connection():
    """Test OpenAI API connection."""
    print("\n" + "="*60)
    print("6. Testing OpenAI API Connection")
    print("="*60)
    
    try:
        import os
        from openai import OpenAI
        from dotenv import load_dotenv
        
        load_dotenv()
        
        api_key = os.getenv('OPENAI_API_KEY')
        
        if not api_key or api_key.startswith('your-'):
            print("✗ OpenAI API key not configured")
            print("  Set OPENAI_API_KEY in your .env file")
            return False
        
        client = OpenAI(api_key=api_key)
        
        # Make a minimal API call to test
        response = client.embeddings.create(
            input="test",
            model="text-embedding-3-small"
        )
        
        print("✓ OpenAI API is accessible")
        print(f"  Embedding dimensions: {len(response.data[0].embedding)}")
        return True
        
    except Exception as e:
        print(f"✗ OpenAI API error: {e}")
        print("  Check your API key and internet connection")
        return False


def test_directories():
    """Check if required directories exist."""
    print("\n" + "="*60)
    print("7. Testing Directory Structure")
    print("="*60)
    
    import os
    
    directories = [
        '../data',
        '../data/chroma_db',
        'app',
        'app/api',
        'app/models',
        'app/services',
        'app/utils',
        'tests'
    ]
    
    all_good = True
    
    for directory in directories:
        if os.path.exists(directory):
            print(f"✓ {directory}/ exists")
        else:
            print(f"⚠ {directory}/ does not exist (will be created when needed)")
            # Create if it doesn't exist
            os.makedirs(directory, exist_ok=True)
            print(f"  Created {directory}/")
    
    return all_good


def print_summary(results):
    """Print test summary."""
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print("\n" + "-"*60)
    print(f"Results: {passed}/{total} tests passed")
    print("-"*60)
    
    if passed == total:
        print("\n🎉 All tests passed! You're ready to start developing!")
        print("\nNext steps:")
        print("1. Run: python run.py")
        print("2. Open browser to: http://localhost:5000")
        print("3. Start building with docs/PHASE_2_GUIDE.md")
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("- Install missing packages: pip install -r requirements.txt")
        print("- Create .env file: cp .env.example .env")
        print("- Add your API keys to .env file")
    
    print("\n")


def main():
    """Run all tests."""
    print("\n" + "🔍 SETUP VERIFICATION SCRIPT")
    print("This will test your development environment setup\n")
    
    # Run tests
    results = {
        'Python Version': test_python_version(),
        'Package Imports': test_imports(),
        'Environment Variables': test_environment_variables(),
        'Configuration': test_config(),
        'Flask App': test_flask_app(),
        'OpenAI API': test_openai_connection(),
        'Directory Structure': test_directories()
    }
    
    # Print summary
    print_summary(results)
    
    # Return exit code
    return 0 if all(results.values()) else 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
