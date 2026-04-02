.PHONY: help install test lint format clean build deploy

# Default target
help:
	@echo "Available commands:"
	@echo "  install     - Install all dependencies"
	@echo "  test        - Run all tests"
	@echo "  lint        - Run code quality checks"
	@echo "  format      - Format code"
	@echo "  clean       - Clean up development artifacts"
	@echo "  build       - Build Docker images"
	@echo "  deploy      - Deploy to production"
	@echo "  dev         - Start development environment"
	@echo "  stop        - Stop all services"

# Install dependencies
install:
	@echo "Installing backend dependencies..."
	cd backend && pip install -r requirements.txt
	cd backend && pip install -r requirements-dev.txt
	@echo "Installing frontend dependencies..."
	cd feishin && npm install
	@echo "Installing pre-commit hooks..."
	pre-commit install

# Run tests
test:
	@echo "Running backend tests..."
	cd backend && python -m pytest --cov=app --cov-report=html --cov-report=term
	@echo "Running frontend tests..."
	cd feishin && npm test -- --coverage --watchAll=false

# Code quality checks
lint:
	@echo "Running backend linting..."
	cd backend && python -m ruff check .
	cd backend && python -m black --check .
	cd backend && mypy .
	@echo "Running frontend linting..."
	cd feishin && npm run lint
	cd feishin && npm run typecheck

# Format code
format:
	@echo "Formatting backend code..."
	cd backend && python -m black .
	cd backend && python -m ruff check . --fix
	@echo "Formatting frontend code..."
	cd feishin && npm run format

# Clean development artifacts
clean:
	@echo "Cleaning development artifacts..."
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	cd feishin && rm -rf node_modules/.cache dist build
	cd backend && rm -rf .coverage htmlcov

# Build Docker images
build:
	@echo "Building Docker images..."
	docker compose build

# Deploy to production
deploy:
	@echo "Deploying to production..."
	docker compose -f docker-compose.yml down
	docker compose -f docker-compose.yml up -d --build
	@echo "Waiting for services to be ready..."
	sleep 30
	curl -f http://localhost:8000/health || exit 1
	@echo "Deployment successful!"

# Development environment
dev:
	@echo "Starting development environment..."
	docker compose -f docker-compose.yml up -d postgres redis navidrome
	@echo "Starting backend in development mode..."
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
	@echo "Starting frontend in development mode..."
	cd feishin && npm run dev &

# Stop all services
stop:
	@echo "Stopping all services..."
	docker compose -f docker-compose.yml down
	pkill -f uvicorn || true
	pkill -f "npm run dev" || true

# Database operations
db-migrate:
	@echo "Running database migrations..."
	cd backend && alembic upgrade head

db-reset:
	@echo "Resetting database..."
	docker compose -f docker-compose.yml down postgres
	docker volume rm music-platform_postgres-data || true
	docker compose -f docker-compose.yml up -d postgres
	sleep 10
	$(MAKE) db-migrate

# Security checks
security-scan:
	@echo "Running security scan..."
	trivy fs --format table --severity HIGH,CRITICAL .
	cd backend && safety check
	cd feishin && npm audit

# Performance monitoring
monitor:
	@echo "Starting performance monitoring..."
	docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"

# Backup operations
backup:
	@echo "Creating backup..."
	mkdir -p backups
	docker exec music-postgres pg_dump -U musicuser musicdb | gzip > backups/db_backup_$(shell date +%Y%m%d_%H%M%S).sql.gz
	docker run --rm -v music-platform_navidrome-data:/data -v $(pwd)/backups:/backup alpine tar czf /backup/navidrome_backup_$(shell date +%Y%m%d_%H%M%S).tar.gz -C /data .

# Restore operations
restore-db:
	@echo "Restoring database from backup..."
	@if [ -z "$(FILE)" ]; then echo "Usage: make restore-db FILE=backup.sql.gz"; exit 1; fi
	gunzip -c $(FILE) | docker exec -i music-postgres psql -U musicuser musicdb
