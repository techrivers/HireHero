#!/bin/bash

echo "🚀 Starting CV Matcher Agent Application"
echo "========================================"

# Stop any existing containers
echo "📦 Stopping existing containers..."
docker-compose down -v

# Build and start the application
echo "🔨 Building and starting application..."
docker-compose up --build

echo "✅ Application should be running!"
echo ""
echo "🌐 Access URLs:"
echo "- Frontend:     http://localhost:3002"
echo "- Backend API:  http://localhost:9000"
echo "- API Docs:     http://localhost:9000/docs"
echo "- Database:     http://localhost:8080 (Adminer)"
echo ""
echo "📝 Demo Accounts (will be created automatically):"
echo "- admin / admin123"
echo "- demo / demo123"
echo "- testuser / test123"