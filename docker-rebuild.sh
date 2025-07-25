#!/bin/bash

# Navigate to project directory
cd /Users/sanaalishah/Desktop/AI-projects/cv-matcher-agent

echo "🛑 Stopping existing containers..."
docker-compose down --volumes --remove-orphans

echo "🔧 Rebuilding containers..."
docker-compose build --no-cache

echo "🚀 Starting containers..."
docker-compose up -d

echo "✅ Containers are now running!"
echo "Backend: http://localhost:9000"
echo "Frontend: http://localhost:3002"

echo "📊 Container Status:"
docker-compose ps