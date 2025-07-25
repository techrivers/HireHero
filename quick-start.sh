#!/bin/bash

echo "🚀 Quick Start - CV Matcher Agent with Enhanced Chatbot"
echo "======================================================="

# Navigate to project directory
cd /Users/sanaalishah/Desktop/AI-projects/cv-matcher-agent

# Stop any existing containers
echo "📦 Stopping existing containers..."
docker-compose down -v --remove-orphans

# Clean up Docker system
echo "🧹 Cleaning up Docker system..."
docker system prune -f

# Build and start the application
echo "🔨 Building and starting application..."
docker-compose up --build -d

# Wait a moment for services to start
echo "⏳ Waiting for services to start..."
sleep 10

# Check service status
echo "📊 Checking service status..."
docker-compose ps

echo ""
echo "✅ Application should be running!"
echo ""
echo "🌐 Access URLs:"
echo "- Frontend (Enhanced Chat): http://localhost:3002"
echo "- Backend API:              http://localhost:9000"
echo "- API Documentation:        http://localhost:9000/docs"
echo ""
echo "🤖 Enhanced Chatbot Features:"
echo "- Natural conversation flow"
echo "- Intelligent clarifying questions"
echo "- Detailed candidate explanations"
echo "- Context-aware responses"
echo "- Smart search suggestions"
echo ""
echo "📝 Try these conversation starters:"
echo "- 'I need a senior Python developer'"
echo "- 'Find me someone for my marketing team'"  
echo "- 'Looking for data scientists with ML experience'"
echo "- 'Why is this candidate a good match?'"