# Phase 1: Environment Setup Guide

## Prerequisites

Before starting, ensure you have:
- Computer with at least 8GB RAM
- Stable internet connection
- Text editor (VS Code recommended)
- Basic command line knowledge

---

## Step 1: Install Core Software

### 1.1 Python Installation

**Windows:**
```bash
# Download from python.org (Python 3.10 or higher)
# During installation, CHECK "Add Python to PATH"

# Verify installation
python --version
pip --version
```

**Mac/Linux:**
```bash
# Mac (using Homebrew)
brew install python@3.10

# Linux (Ubuntu/Debian)
sudo apt update
sudo apt install python3.10 python3-pip python3-venv

# Verify
python3 --version
pip3 --version
```

### 1.2 Node.js Installation (for frontend tools)

```bash
# Download from nodejs.org (LTS version)
# Or use nvm (recommended)

# Verify
node --version
npm --version
```

### 1.3 Git Installation

```bash
# Download from git-scm.com

# Verify
git --version

# Configure
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### 1.4 VS Code Setup

Download from code.visualstudio.com

**Recommended Extensions:**
- Python (Microsoft)
- Pylance
- SQLite Viewer
- REST Client
- GitLens
- Thunder Client (API testing)

---

## Step 2: Project Setup

### 2.1 Clone/Create Project

```bash
# Navigate to your workspace
cd ~/Projects  # or wherever you keep projects

# Create project directory
mkdir ai-support-saas
cd ai-support-saas

# Initialize git
git init
```

### 2.2 Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate

# You should see (venv) in your terminal prompt
```

**Important:** Always activate venv before working on the project!

### 2.3 Create Project Structure

```bash
# Create backend structure
mkdir -p backend/{app/{api,models,services,utils},migrations,tests}
mkdir -p backend/app/api
mkdir -p backend/app/models
mkdir -p backend/app/services
mkdir -p backend/app/utils

# Create frontend structure
mkdir -p frontend/{css,js,pages,widget}

# Create docs
mkdir docs

# Create other necessary directories
mkdir -p data/chroma_db
mkdir logs
```

---

## Step 3: Install Python Dependencies

### 3.1 Create requirements.txt

Create `backend/requirements.txt`:

```txt
# Web Framework
Flask==3.0.0
Flask-CORS==4.0.0
Flask-SocketIO==5.3.5
python-socketio==5.10.0

# Database
SQLAlchemy==2.0.23
Flask-SQLAlchemy==3.1.1
Flask-Migrate==4.0.5

# AI/ML Libraries
langchain==0.1.0
langchain-openai==0.0.2
openai==1.6.1
chromadb==0.4.22
sentence-transformers==2.2.2
transformers==4.36.2
torch==2.1.2

# Authentication
PyJWT==2.8.0
bcrypt==4.1.2
python-dotenv==1.0.0

# Payments
stripe==7.10.0

# Utilities
python-multipart==0.0.6
requests==2.31.0
gunicorn==21.2.0
python-dateutil==2.8.2

# Testing
pytest==7.4.3
pytest-cov==4.1.0
pytest-flask==1.3.0

# Development
black==23.12.1
flake8==7.0.0
```

### 3.2 Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

**Note:** This may take 10-15 minutes due to ML libraries.

**If you encounter issues with torch:**
```bash
# For CPU-only version (smaller, faster install)
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

---

## Step 4: Get API Keys

### 4.1 OpenAI API Key

1. Go to https://platform.openai.com/
2. Sign up / Log in
3. Navigate to API Keys
4. Create new secret key
5. **Copy and save it immediately** (you won't see it again)

**Free tier:** $5 credit for testing
**Recommended:** Add $10-20 for development

### 4.2 Stripe API Keys

1. Go to https://stripe.com/
2. Sign up for account
3. Navigate to Developers > API Keys
4. Get your **Publishable key** and **Secret key**
5. Use **Test mode** for development

### 4.3 Create .env File

Create `backend/.env`:

```bash
# Flask Configuration
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=your-secret-key-change-this-in-production

# OpenAI
OPENAI_API_KEY=sk-your-openai-key-here

# Stripe
STRIPE_SECRET_KEY=sk_test_your-stripe-secret-key
STRIPE_PUBLISHABLE_KEY=pk_test_your-stripe-publishable-key
STRIPE_WEBHOOK_SECRET=whsec_your-webhook-secret

# Database
DATABASE_URL=sqlite:///./chatbot.db

# ChromaDB
CHROMA_PERSIST_DIRECTORY=../data/chroma_db

# JWT
JWT_SECRET_KEY=your-jwt-secret-key-change-this

# Application
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:5000
```

**Security Note:** Never commit `.env` to git!

Create `backend/.env.example` (for git):
```bash
# Copy .env.example to .env and fill in your values
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=
OPENAI_API_KEY=
STRIPE_SECRET_KEY=
# ... etc
```

---

## Step 5: Create .gitignore

Create `.gitignore` in root:

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/

# IDEs
.vscode/
.idea/
*.swp
*.swo

# Environment
.env
.env.local

# Database
*.db
*.sqlite
*.sqlite3

# Logs
logs/
*.log

# ChromaDB
data/chroma_db/

# OS
.DS_Store
Thumbs.db

# Build
dist/
build/
*.egg-info/

# Testing
.coverage
htmlcov/
.pytest_cache/

# Stripe
stripe-cli/
```

---

## Step 6: Verify Installation

### 6.1 Test Python Environment

Create `backend/test_setup.py`:

```python
"""Test script to verify all dependencies are installed correctly."""

def test_imports():
    print("Testing imports...")
    
    try:
        import flask
        print("✓ Flask installed")
    except ImportError as e:
        print(f"✗ Flask error: {e}")
    
    try:
        import langchain
        print("✓ LangChain installed")
    except ImportError as e:
        print(f"✗ LangChain error: {e}")
    
    try:
        import openai
        print("✓ OpenAI installed")
    except ImportError as e:
        print(f"✗ OpenAI error: {e}")
    
    try:
        import chromadb
        print("✓ ChromaDB installed")
    except ImportError as e:
        print(f"✗ ChromaDB error: {e}")
    
    try:
        import transformers
        print("✓ Transformers installed")
    except ImportError as e:
        print(f"✗ Transformers error: {e}")
    
    try:
        import stripe
        print("✓ Stripe installed")
    except ImportError as e:
        print(f"✗ Stripe error: {e}")
    
    try:
        import sqlalchemy
        print("✓ SQLAlchemy installed")
    except ImportError as e:
        print(f"✗ SQLAlchemy error: {e}")
    
    print("\nAll core dependencies verified!")

def test_env():
    print("\nTesting environment variables...")
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    required_vars = [
        'OPENAI_API_KEY',
        'STRIPE_SECRET_KEY',
        'SECRET_KEY'
    ]
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✓ {var} is set")
        else:
            print(f"✗ {var} is missing!")

if __name__ == "__main__":
    test_imports()
    test_env()
    print("\n🎉 Setup verification complete!")
```

Run the test:
```bash
cd backend
python test_setup.py
```

You should see all checkmarks (✓). If any show (✗), review the installation steps.

---

## Step 7: Create Basic Flask App

Create `backend/run.py`:

```python
"""Main application entry point."""
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# Enable CORS
CORS(app)

@app.route('/')
def home():
    return jsonify({
        'message': 'AI Support SaaS API',
        'version': '1.0.0',
        'status': 'running'
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

### Test the Flask App

```bash
cd backend
python run.py
```

Open browser to `http://localhost:5000` - you should see JSON response!

Press `Ctrl+C` to stop the server.

---

## Step 8: Setup Frontend

### 8.1 Create Basic HTML

Create `frontend/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Support SaaS</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <h1>AI Customer Support SaaS</h1>
    <p>Setup Complete! 🎉</p>
    
    <div id="api-status">Checking API...</div>
    
    <script src="js/main.js"></script>
</body>
</html>
```

### 8.2 Create Basic CSS

Create `frontend/css/style.css`:

```css
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    padding: 40px;
    background: #f5f5f5;
}

h1 {
    color: #333;
    margin-bottom: 20px;
}

#api-status {
    padding: 10px 20px;
    background: #fff;
    border-radius: 5px;
    margin-top: 20px;
}
```

### 8.3 Create Basic JavaScript

Create `frontend/js/main.js`:

```javascript
// Test API connection
async function checkAPI() {
    const statusDiv = document.getElementById('api-status');
    
    try {
        const response = await fetch('http://localhost:5000/health');
        const data = await response.json();
        
        if (data.status === 'healthy') {
            statusDiv.textContent = '✓ API is running and healthy!';
            statusDiv.style.background = '#d4edda';
            statusDiv.style.color = '#155724';
        }
    } catch (error) {
        statusDiv.textContent = '✗ API connection failed. Is the Flask server running?';
        statusDiv.style.background = '#f8d7da';
        statusDiv.style.color = '#721c24';
    }
}

// Check API on page load
checkAPI();
```

### 8.4 Test Frontend

Open `frontend/index.html` in your browser directly.

---

## Step 9: Development Workflow

### Daily Workflow:

1. **Activate virtual environment**
   ```bash
   source venv/bin/activate  # Mac/Linux
   # or
   venv\Scripts\activate  # Windows
   ```

2. **Start Flask backend**
   ```bash
   cd backend
   python run.py
   ```

3. **Open frontend**
   - Option A: Open `frontend/index.html` in browser
   - Option B: Use Python's HTTP server:
     ```bash
     cd frontend
     python -m http.server 3000
     ```
     Then visit `http://localhost:3000`

4. **Make changes and test**

5. **Deactivate venv when done**
   ```bash
   deactivate
   ```

---

## Step 10: Useful Commands

### Python/Flask:
```bash
# Install new package
pip install package-name

# Update requirements.txt
pip freeze > requirements.txt

# Run tests
pytest

# Code formatting
black .

# Code linting
flake8 .
```

### Git:
```bash
# Save your work
git add .
git commit -m "Your message"

# Create new branch
git checkout -b feature-name

# Push to remote
git push origin branch-name
```

---

## Common Issues & Solutions

### Issue 1: "Module not found"
**Solution:** 
```bash
# Make sure venv is activated
source venv/bin/activate
# Reinstall requirements
pip install -r requirements.txt
```

### Issue 2: CORS errors in browser
**Solution:** Already handled by Flask-CORS, but ensure backend is running.

### Issue 3: Port already in use
**Solution:**
```bash
# Kill process on port 5000 (Mac/Linux)
lsof -ti:5000 | xargs kill -9

# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

### Issue 4: OpenAI API errors
**Solution:** 
- Verify API key in `.env`
- Check credit balance at platform.openai.com
- Ensure no spaces in API key

---

## 🎉 Setup Complete!

You now have:
- ✓ Python environment with all dependencies
- ✓ Flask backend running
- ✓ Basic frontend setup
- ✓ API keys configured
- ✓ Development workflow established

## Next Steps:

Proceed to `docs/PHASE_2_GUIDE.md` to start building the AI chatbot core!

---

## Quick Reference Card

```bash
# Activate environment
source venv/bin/activate

# Start backend
cd backend && python run.py

# Start frontend (optional HTTP server)
cd frontend && python -m http.server 3000

# Run tests
pytest

# View logs
tail -f logs/app.log
```

Save this guide - you'll reference it often! 📚
