#!/bin/bash

# Resume Matcher Agent - Setup Script

echo "🤖 Resume Matcher Agent Setup"
echo "========================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created. Please edit it with your credentials."
    echo ""
    echo "Required configurations:"
    echo "- GOOGLE_CLIENT_ID"
    echo "- GOOGLE_CLIENT_SECRET"
    echo "- SECRET_KEY (generate a secure random string)"
    echo ""
    echo "Please edit .env file and run this script again."
    exit 1
fi

# Check if required environment variables are set
source .env

if [ -z "$GOOGLE_CLIENT_ID" ] || [ "$GOOGLE_CLIENT_ID" = "your-google-client-id" ]; then
    echo "❌ Please set GOOGLE_CLIENT_ID in .env file"
    exit 1
fi

if [ -z "$GOOGLE_CLIENT_SECRET" ] || [ "$GOOGLE_CLIENT_SECRET" = "your-google-client-secret" ]; then
    echo "❌ Please set GOOGLE_CLIENT_SECRET in .env file"
    exit 1
fi

if [ -z "$SECRET_KEY" ] || [ "$SECRET_KEY" = "your-super-secret-jwt-key-change-this-in-production" ]; then
    echo "❌ Please set a secure SECRET_KEY in .env file"
    exit 1
fi

echo "🔧 Environment configuration looks good!"
echo ""

# Build and start containers
echo "🐳 Building and starting Docker containers..."
docker-compose down
docker-compose up --build -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo "✅ Services are running!"
    echo ""
    echo "🚀 Resume Matcher Agent is ready!"
    echo "============================="
    echo ""
    echo "📖 Access points:"
    echo "- API Documentation: http://localhost:8000/docs"
    echo "- API Alternative Docs: http://localhost:8000/redoc"
    echo "- Database Admin: http://localhost:8080"
    echo "- Main API: http://localhost:8000"
    echo ""
    echo "🔧 Management commands:"
    echo "- View logs: docker-compose logs -f"
    echo "- Stop services: docker-compose down"
    echo "- Restart services: docker-compose restart"
    echo ""
    echo "📝 Next steps:"
    echo "1. Register a user account"
    echo "2. Setup Google Drive authentication"
    echo "3. Configure OpenAI API key"
    echo "4. Start matching Resume!"
else
    echo "❌ Some services failed to start. Check logs with:"
    echo "docker-compose logs"
fi
