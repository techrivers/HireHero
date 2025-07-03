# Makefile for CV Matcher Agent

.PHONY: help setup build up down logs clean test init-db

help:  ## Show this help message
	@echo "CV Matcher Agent - Available Commands"
	@echo "====================================="
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ { printf "  %-15s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

setup:  ## Setup the project (create .env if needed)
	@echo "🚀 Setting up CV Matcher Agent..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "📝 Created .env file from template"; \
		echo "⚠️  Please edit .env with your credentials before continuing"; \
	else \
		echo "✅ .env file already exists"; \
	fi
	@chmod +x setup.sh
	@chmod +x init_db.py
	@chmod +x test_api.py

build:  ## Build Docker containers
	@echo "🔨 Building containers..."
	docker-compose build

up:  ## Start all services
	@echo "🚀 Starting services..."
	docker-compose up -d

up-build:  ## Build and start all services
	@echo "🔨🚀 Building and starting services..."
	docker-compose up -d --build

down:  ## Stop all services
	@echo "🛑 Stopping services..."
	docker-compose down

logs:  ## View logs
	@echo "📋 Viewing logs..."
	docker-compose logs -f

logs-web:  ## View web service logs
	@echo "📋 Viewing web service logs..."
	docker-compose logs -f web

logs-db:  ## View database logs
	@echo "📋 Viewing database logs..."
	docker-compose logs -f db

clean:  ## Clean up containers and volumes
	@echo "🧹 Cleaning up..."
	docker-compose down -v
	docker system prune -f

clean-all:  ## Clean up everything including images
	@echo "🧹 Deep cleaning..."
	docker-compose down -v --rmi all
	docker system prune -af

test:  ## Run API tests
	@echo "🧪 Running API tests..."
	python test_api.py --wait 5

init-db:  ## Initialize database with demo users
	@echo "🗄️  Initializing database..."
	python init_db.py

restart:  ## Restart all services
	@echo "🔄 Restarting services..."
	docker-compose restart

status:  ## Show service status
	@echo "📊 Service status:"
	docker-compose ps

shell-web:  ## Access web container shell
	@echo "🐚 Accessing web container..."
	docker-compose exec web bash

shell-db:  ## Access database shell
	@echo "🐚 Accessing database..."
	docker-compose exec db psql -U cvmatcher -d cvmatcher_db

backup-db:  ## Backup database
	@echo "💾 Backing up database..."
	@mkdir -p backups
	docker-compose exec db pg_dump -U cvmatcher cvmatcher_db > backups/backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "✅ Database backed up to backups/"

dev:  ## Run in development mode with hot reload
	@echo "🔧 Starting in development mode..."
	docker-compose -f docker-compose.yml -f docker-compose.override.yml up --build

prod:  ## Run in production mode
	@echo "🚀 Starting in production mode..."
	docker-compose -f docker-compose.yml up -d --build

install:  ## Install dependencies locally (for development)
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt

format:  ## Format code with black
	@echo "🎨 Formatting code..."
	black app/

lint:  ## Lint code with flake8
	@echo "🔍 Linting code..."
	flake8 app/

type-check:  ## Type check with mypy
	@echo "🔍 Type checking..."
	mypy app/

docs:  ## Open API documentation
	@echo "📖 Opening API documentation..."
	@echo "API Docs: http://localhost:8000/docs"
	@echo "ReDoc: http://localhost:8000/redoc"
	@echo "Database Admin: http://localhost:8080"

quick-start:  ## Quick start for new users
	@echo "🚀 Quick Start Guide"
	@echo "==================="
	@echo "1. make setup     - Setup environment"
	@echo "2. Edit .env file with your credentials"
	@echo "3. make up-build  - Build and start services"
	@echo "4. make init-db   - Initialize with demo users"
	@echo "5. make test      - Test the API"
	@echo "6. make docs      - View documentation"
