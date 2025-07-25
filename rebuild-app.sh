#!/bin/bash

# Script to rebuild and restart the CV Matcher Agent application

PROJECT_DIR="/Users/sanaalishah/Desktop/AI-projects/cv-matcher-agent"
cd "$PROJECT_DIR"

echo "🔍 Current directory: $(pwd)"
echo "📁 Project contents:"
ls -la

echo ""
echo "🛑 Stopping existing containers..."
docker-compose down --volumes --remove-orphans

echo ""
echo "🧹 Cleaning up Docker system..."
docker system prune -f

echo ""
echo "🔧 Rebuilding containers from scratch..."
docker-compose build --no-cache

echo ""
echo "🚀 Starting the application..."
docker-compose up -d

echo ""
echo "⏳ Waiting for containers to fully start..."
sleep 10

echo ""
echo "✅ Application Status:"
docker-compose ps

echo ""
echo "📊 Container Health:"
docker-compose logs --tail=20 web

echo ""
echo "🎉 Application is ready!"
echo "🌐 Frontend: http://localhost:3002"
echo "🔗 Backend API: http://localhost:9000"
echo "📚 API Docs: http://localhost:9000/docs"

echo ""
echo "🔍 Testing connectivity..."
curl -s http://localhost:9000/ | head -n 5

echo ""
echo "✅ Docker rebuild complete!"