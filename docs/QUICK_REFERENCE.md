# Quick Reference Cheat Sheet

## Essential Commands

### Environment
```bash
# Activate virtual environment
source venv/bin/activate              # Mac/Linux
venv\Scripts\activate                 # Windows

# Deactivate
deactivate
```

### Development
```bash
# Start backend
cd backend && python run.py

# Run tests
pytest
pytest -v                             # Verbose
pytest --cov=app tests/              # With coverage

# Format code
black .                               # Auto-format
flake8 .                              # Check style

# Install package
pip install package-name
pip freeze > requirements.txt         # Update requirements
```

### Git
```bash
# Save work
git add .
git commit -m "Description"
git push

# New feature
git checkout -b feature-name
git merge feature-name

# Undo changes
git checkout -- filename
git reset --hard HEAD
```

---

## Project Structure Quick Map

```
ai-support-saas/
├── backend/
│   ├── app/
│   │   ├── api/          # API endpoints (routes)
│   │   ├── models/       # Database models
│   │   ├── services/     # Business logic
│   │   └── utils/        # Helper functions
│   ├── config.py         # Configuration
│   ├── run.py            # Start here
│   └── requirements.txt  # Python packages
│
├── frontend/
│   ├── css/              # Stylesheets
│   ├── js/               # JavaScript
│   ├── pages/            # HTML pages
│   └── widget/           # Embeddable widget
│
└── docs/                 # Documentation
```

---

## Key Files & Their Purpose

| File | Purpose |
|------|---------|
| `backend/run.py` | Application entry point |
| `backend/config.py` | All configuration settings |
| `backend/.env` | Secret keys (NEVER commit!) |
| `backend/app/services/embedding_service.py` | Generate embeddings |
| `backend/app/services/vector_store_service.py` | ChromaDB operations |
| `backend/app/services/sentiment_service.py` | Sentiment analysis |
| `backend/app/services/chat_service.py` | Main chat logic |
| `backend/app/models/user.py` | User database model |
| `backend/app/api/chat.py` | Chat API endpoints |
| `frontend/widget/chat-widget.js` | Embeddable widget |

---

## Environment Variables (.env)

```bash
# Required
OPENAI_API_KEY=sk-...
STRIPE_SECRET_KEY=sk_test_...
SECRET_KEY=your-secret

# Optional
FLASK_ENV=development
DATABASE_URL=sqlite:///chatbot.db
CHROMA_PERSIST_DIRECTORY=../data/chroma_db
```

---

## API Endpoints (To Be Built)

### Authentication
```
POST   /api/auth/register       # Create account
POST   /api/auth/login          # Login
POST   /api/auth/logout         # Logout
POST   /api/auth/reset-password # Reset password
```

### Chat
```
WS     /api/chat/ws             # WebSocket connection
POST   /api/chat/message        # Send message
GET    /api/chat/history        # Get history
```

### Admin
```
GET    /api/admin/dashboard     # Dashboard stats
GET    /api/admin/conversations # List conversations
POST   /api/admin/documents     # Upload document
DELETE /api/admin/documents/:id # Delete document
```

### Payments
```
POST   /api/payments/checkout   # Create checkout
POST   /api/payments/webhook    # Stripe webhook
GET    /api/payments/portal     # Billing portal
```

---

## Common Code Patterns

### Flask Route
```python
from flask import Blueprint, jsonify, request

bp = Blueprint('chat', __name__)

@bp.route('/message', methods=['POST'])
def send_message():
    data = request.get_json()
    # Process message
    return jsonify({'response': 'Hello'})
```

### Database Model
```python
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

### Service Class
```python
class ChatService:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStoreService()
    
    def generate_response(self, message: str) -> str:
        # 1. Get embeddings
        # 2. Search vector store
        # 3. Generate with LLM
        # 4. Return response
        pass
```

### Error Handling
```python
try:
    result = risky_operation()
    return jsonify({'success': True, 'data': result})
except ValueError as e:
    return jsonify({'error': str(e)}), 400
except Exception as e:
    print(f"Unexpected error: {e}")
    return jsonify({'error': 'Internal error'}), 500
```

---

## Testing Patterns

### Unit Test
```python
def test_embedding_generation():
    service = EmbeddingService()
    embedding = service.generate_embedding("test")
    assert len(embedding) == 1536
    assert all(isinstance(x, float) for x in embedding)
```

### API Test
```python
def test_chat_endpoint(client):
    response = client.post('/api/chat/message', json={
        'message': 'Hello',
        'conversation_id': '123'
    })
    assert response.status_code == 200
    assert 'response' in response.json
```

---

## Frontend Patterns

### Fetch API
```javascript
async function sendMessage(message) {
    try {
        const response = await fetch('http://localhost:5000/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ message })
        });
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error:', error);
        throw error;
    }
}
```

### WebSocket Connection
```javascript
const ws = new WebSocket('ws://localhost:5000/api/chat/ws');

ws.onopen = () => {
    console.log('Connected');
    ws.send(JSON.stringify({ type: 'join', room: 'chat-123' }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};

ws.onerror = (error) => {
    console.error('WebSocket error:', error);
};
```

---

## Debugging Tips

### Backend
```python
# Print debug info
print(f"Debug: {variable}")

# Use debugger
import pdb; pdb.set_trace()

# Log to file
import logging
logging.basicConfig(filename='app.log', level=logging.DEBUG)
logging.debug('Debug message')
```

### Frontend
```javascript
// Console debugging
console.log('Variable:', variable);
console.table(arrayOfObjects);
console.error('Error:', error);

// Debugger
debugger;  // Pauses execution in browser dev tools
```

---

## Performance Tips

### Backend
- Use database indexes
- Implement caching (Redis)
- Batch API calls
- Use connection pooling
- Profile slow endpoints

### Frontend
- Minimize HTTP requests
- Lazy load images
- Use CDN for static assets
- Debounce user input
- Cache API responses

---

## Security Checklist

- [ ] Use HTTPS in production
- [ ] Validate all user input
- [ ] Use parameterized queries (prevent SQL injection)
- [ ] Implement rate limiting
- [ ] Set secure HTTP headers
- [ ] Hash passwords (bcrypt)
- [ ] Use CSRF tokens
- [ ] Sanitize HTML output
- [ ] Keep dependencies updated
- [ ] Never commit .env file

---

## Deployment Checklist

### Pre-Deploy
- [ ] All tests passing
- [ ] Environment variables set
- [ ] Database migrations ready
- [ ] Static files built
- [ ] Error tracking configured
- [ ] Backup strategy in place

### Deploy
- [ ] Push to repository
- [ ] Run migrations
- [ ] Deploy backend
- [ ] Deploy frontend
- [ ] Test production endpoints
- [ ] Monitor logs

### Post-Deploy
- [ ] Check error rates
- [ ] Monitor performance
- [ ] Test critical paths
- [ ] Update documentation
- [ ] Announce to users

---

## Useful Links

| Resource | URL |
|----------|-----|
| Flask Docs | https://flask.palletsprojects.com/ |
| LangChain | https://python.langchain.com/ |
| OpenAI API | https://platform.openai.com/docs |
| ChromaDB | https://docs.trychroma.com/ |
| Stripe Docs | https://stripe.com/docs |
| Render | https://render.com/docs |

---

## Emergency Procedures

### Database Issues
```bash
# Backup database
cp chatbot.db chatbot.db.backup

# Reset database
rm chatbot.db
flask db upgrade

# Restore backup
cp chatbot.db.backup chatbot.db
```

### API Key Compromised
1. Immediately revoke key at provider
2. Generate new key
3. Update .env file
4. Redeploy application
5. Check for unauthorized usage

### Server Down
1. Check server logs
2. Verify environment variables
3. Check database connection
4. Restart services
5. Monitor error tracking

---

## Cost Optimization

### OpenAI API
- Use GPT-3.5-turbo for simple queries
- Cache common responses
- Limit response length
- Batch embedding generations

### Database
- Add indexes to frequently queried columns
- Archive old conversations
- Use connection pooling
- Regular VACUUM (PostgreSQL)

### Hosting
- Right-size your instances
- Use CDN for static assets
- Enable compression
- Implement caching

---

## Keyboard Shortcuts (VS Code)

| Action | Shortcut |
|--------|----------|
| Command Palette | Cmd/Ctrl + Shift + P |
| Find in Files | Cmd/Ctrl + Shift + F |
| Terminal | Cmd/Ctrl + ` |
| Format Document | Shift + Alt + F |
| Go to Definition | F12 |
| Rename Symbol | F2 |

---

## Git Workflow

### Feature Development
```bash
git checkout -b feature/new-feature
# Make changes
git add .
git commit -m "Add new feature"
git push origin feature/new-feature
# Create pull request
```

### Bug Fix
```bash
git checkout -b fix/bug-description
# Fix bug
git add .
git commit -m "Fix: description"
git push origin fix/bug-description
```

### Release
```bash
git checkout main
git merge develop
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin main --tags
```

---

## Help & Resources

### Stuck?
1. Read error message carefully
2. Check documentation
3. Search Stack Overflow
4. Ask in Discord/Slack
5. Review similar code examples

### Learning Resources
- Official documentation (always first)
- YouTube tutorials
- Blog posts
- GitHub examples
- Community forums

---

**Print this and keep it handy! 📋**

Last Updated: December 2024
