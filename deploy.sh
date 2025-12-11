#!/bin/bash

# AI Chatbot - Quick Deployment Script
# This script helps you deploy your chatbot quickly

set -e

echo "AI Chatbot Deployment Helper"
echo "================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo " Docker not found. Please install Docker first:"
    echo "   https://docs.docker.com/get-docker/"
    exit 1
fi

echo "Docker found"

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose not found. Please install it:"
    echo "   https://docs.docker.com/compose/install/"
    exit 1
fi

echo "Docker Compose found"
echo ""

# Check for .env file
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp backend/.env.example .env
    echo ""
    echo "Please edit .env file with your API keys:"
    echo "   - OPENAI_API_KEY"
    echo "   - STRIPE_SECRET_KEY"
    echo "   - SECRET_KEY (generate with: openssl rand -hex 32)"
    echo "   - JWT_SECRET_KEY (generate with: openssl rand -hex 32)"
    echo ""
    read -p "Press Enter after editing .env file..."
fi

echo "Environment file found"
echo ""

# Deployment options
echo "Choose deployment method:"
echo "1) Docker Compose (Local)"
echo "2) Render.com (Cloud - Recommended)"
echo "3) Railway (Cloud)"
echo "4) Manual Docker Build"
echo ""
read -p "Enter choice [1-4]: " choice

case $choice in
    1)
        echo ""
        echo "Starting with Docker Compose..."
        docker-compose up -d
        echo ""
        echo "Deployment complete!"
        echo ""
        echo "📍 Access your app:"
        echo "   Frontend: http://localhost:8080"
        echo "   Backend:  http://localhost:5000"
        echo "   API Docs: http://localhost:5000/health"
        echo ""
        echo "View logs:"
        echo "   docker-compose logs -f"
        echo ""
        echo "Stop services:"
        echo "   docker-compose down"
        ;;
    2)
        echo ""
        echo "Deploying to Render.com..."
        echo ""
        echo "Follow these steps:"
        echo "1. Push your code to GitHub:"
        echo "   git add ."
        echo "   git commit -m 'feat: add deployment config'"
        echo "   git push origin main"
        echo ""
        echo "2. Go to https://render.com and sign up"
        echo "3. Click 'New +' → 'Web Service'"
        echo "4. Connect your GitHub repo"
        echo "5. Configure backend:"
        echo "   - Name: ai-chatbot-backend"
        echo "   - Root Directory: backend"
        echo "   - Build Command: pip install -r requirements.txt"
        echo "   - Start Command: gunicorn --bind 0.0.0.0:\$PORT --workers 2 --threads 4 --timeout 120 run:app"
        echo "6. Add environment variables from your .env file"
        echo "7. Deploy!"
        echo ""
        echo "Full guide: See DEPLOYMENT_GUIDE.md"
        ;;
    3)
        echo ""
        echo "🚂 Deploying to Railway..."
        echo ""
        if ! command -v railway &> /dev/null; then
            echo "Installing Railway CLI..."
            npm install -g @railway/cli || curl -fsSL https://railway.app/install.sh | sh
        fi
        echo ""
        echo "Follow these steps:"
        echo "1. Login: railway login"
        echo "2. Initialize: railway init"
        echo "3. Set variables:"
        echo "   railway variables set OPENAI_API_KEY=your-key"
        echo "   railway variables set STRIPE_SECRET_KEY=your-key"
        echo "   railway variables set SECRET_KEY=\$(openssl rand -hex 32)"
        echo "   railway variables set JWT_SECRET_KEY=\$(openssl rand -hex 32)"
        echo "   railway variables set FLASK_ENV=production"
        echo "4. Deploy: railway up"
        echo "5. Get URL: railway domain"
        echo ""
        echo "Full guide: See DEPLOYMENT_GUIDE.md"
        ;;
    4)
        echo ""
        echo "🔨 Building Docker image..."
        cd backend
        docker build -t ai-chatbot-backend .
        echo ""
        echo "Build complete!"
        echo ""
        echo "To run:"
        echo "docker run -p 5000:5000 \\"
        echo "  -e OPENAI_API_KEY=your-key \\"
        echo "  -e STRIPE_SECRET_KEY=your-key \\"
        echo "  -e SECRET_KEY=random-secret \\"
        echo "  -e JWT_SECRET_KEY=random-jwt-secret \\"
        echo "  ai-chatbot-backend"
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "Setup complete!"
echo ""
echo "For detailed instructions, see:"
echo "   - DEPLOYMENT_GUIDE.md (comprehensive guide)"
echo "   - README.md (project overview)"
echo ""