# Tiger MCP Makefile
# Convenient commands for Docker management

# Variables
PROJECT_NAME := tiger-mcp
REGISTRY ?= 
COMPOSE_FILE_DEV := docker-compose.dev.yml
COMPOSE_FILE_PROD := docker-compose.prod.yml
ENV_FILE := .env
ENV_FILE_PROD := .env.prod

# Colors
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

# Default target
.DEFAULT_GOAL := help

# Help target
.PHONY: help
help: ## Show this help message
	@echo "$(BLUE)Tiger MCP Docker Management$(NC)"
	@echo "$(BLUE)=============================$(NC)"
	@echo ""
	@echo "$(GREEN)Available targets:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(BLUE)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(GREEN)Examples:$(NC)"
	@echo "  make dev-up                    # Start development environment"
	@echo "  make prod-up REGISTRY=my.reg  # Start production with registry"
	@echo "  make logs SERVICE=mcp-server   # View logs for specific service"

# Environment setup
.PHONY: setup
setup: ## Setup development environment
	@echo "$(BLUE)Setting up Tiger MCP environment...$(NC)"
	@if [ ! -f $(ENV_FILE) ]; then \
		cp .env.template $(ENV_FILE); \
		echo "$(GREEN)Created $(ENV_FILE) from template$(NC)"; \
		echo "$(YELLOW)Please configure your environment variables in $(ENV_FILE)$(NC)"; \
	else \
		echo "$(GREEN)$(ENV_FILE) already exists$(NC)"; \
	fi
	@mkdir -p logs secrets
	@echo "$(GREEN)Environment setup complete$(NC)"

.PHONY: setup-prod
setup-prod: ## Setup production environment
	@echo "$(BLUE)Setting up Tiger MCP production environment...$(NC)"
	@if [ ! -f $(ENV_FILE_PROD) ]; then \
		cp .env.prod.template $(ENV_FILE_PROD); \
		echo "$(GREEN)Created $(ENV_FILE_PROD) from template$(NC)"; \
		echo "$(YELLOW)Please configure your production variables in $(ENV_FILE_PROD)$(NC)"; \
	fi
	@mkdir -p logs secrets docker/ssl
	@echo "$(YELLOW)Don't forget to setup secrets in the secrets/ directory$(NC)"
	@echo "$(GREEN)Production environment setup complete$(NC)"

# Build targets
.PHONY: build build-dev build-prod
build: build-dev ## Build development images

build-dev: setup ## Build development images
	@echo "$(BLUE)Building development images...$(NC)"
	./scripts/build.sh --target production

build-prod: setup-prod ## Build production images
	@echo "$(BLUE)Building production images...$(NC)"
	./scripts/build.sh --target production $(if $(REGISTRY),--registry $(REGISTRY) --push)

# Development environment
.PHONY: dev-up dev-down dev-logs dev-restart dev-build-up
dev-up: setup ## Start development environment
	@echo "$(BLUE)Starting development environment...$(NC)"
	./scripts/start.sh

dev-down: ## Stop development environment
	@echo "$(BLUE)Stopping development environment...$(NC)"
	./scripts/stop.sh

dev-logs: ## View development logs
	@echo "$(BLUE)Viewing development logs...$(NC)"
	./scripts/logs.sh $(if $(SERVICE),$(SERVICE)) --follow

dev-restart: dev-down dev-up ## Restart development environment

dev-build-up: ## Build and start development environment
	@echo "$(BLUE)Building and starting development environment...$(NC)"
	./scripts/start.sh --build

# Production environment
.PHONY: prod-up prod-down prod-logs prod-restart prod-build-up
prod-up: setup-prod ## Start production environment
	@echo "$(BLUE)Starting production environment...$(NC)"
	./scripts/start.sh --prod

prod-down: ## Stop production environment
	@echo "$(BLUE)Stopping production environment...$(NC)"
	./scripts/stop.sh --prod

prod-logs: ## View production logs
	@echo "$(BLUE)Viewing production logs...$(NC)"
	./scripts/logs.sh --prod $(if $(SERVICE),$(SERVICE)) --follow

prod-restart: prod-down prod-up ## Restart production environment

prod-build-up: ## Build and start production environment
	@echo "$(BLUE)Building and starting production environment...$(NC)"
	./scripts/start.sh --prod --build

# Service management
.PHONY: logs status health shell
logs: ## View logs (specify SERVICE=name)
	@if [ -z "$(SERVICE)" ]; then \
		echo "$(RED)Please specify SERVICE=service-name$(NC)"; \
		echo "$(YELLOW)Available services: mcp-server, dashboard-api, postgres, redis$(NC)"; \
		exit 1; \
	fi
	./scripts/logs.sh $(SERVICE)

status: ## Show service status
	@echo "$(BLUE)Development services:$(NC)"
	@docker-compose -f $(COMPOSE_FILE_DEV) ps 2>/dev/null || echo "$(YELLOW)Development environment not running$(NC)"
	@echo ""
	@echo "$(BLUE)Production services:$(NC)"
	@docker-compose -f $(COMPOSE_FILE_PROD) ps 2>/dev/null || echo "$(YELLOW)Production environment not running$(NC)"

health: ## Check service health
	@echo "$(BLUE)Checking service health...$(NC)"
	@echo "$(GREEN)MCP Server:$(NC)"
	@curl -f http://localhost:8000/health 2>/dev/null && echo " ✓ Healthy" || echo " ✗ Unhealthy"
	@echo "$(GREEN)Dashboard API:$(NC)"
	@curl -f http://localhost:8001/health 2>/dev/null && echo " ✓ Healthy" || echo " ✗ Unhealthy"

shell: ## Access container shell (specify SERVICE=name)
	@if [ -z "$(SERVICE)" ]; then \
		echo "$(RED)Please specify SERVICE=service-name$(NC)"; \
		exit 1; \
	fi
	@docker exec -it $(PROJECT_NAME)-$(SERVICE)-dev /bin/bash 2>/dev/null || \
	 docker exec -it $(PROJECT_NAME)-$(SERVICE)-prod /bin/bash 2>/dev/null || \
	 echo "$(RED)Container $(SERVICE) not found or not running$(NC)"

# Database operations
.PHONY: db-migrate db-shell db-backup db-restore
db-migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(NC)"
	@docker exec $(PROJECT_NAME)-db-migrate-dev python manage_db.py upgrade 2>/dev/null || \
	 docker exec $(PROJECT_NAME)-db-migrate-prod python manage_db.py upgrade 2>/dev/null || \
	 echo "$(RED)Migration service not found$(NC)"

db-shell: ## Access PostgreSQL shell
	@echo "$(BLUE)Accessing PostgreSQL shell...$(NC)"
	@docker exec -it $(PROJECT_NAME)-postgres-dev psql -U tiger_user -d tiger_mcp_dev 2>/dev/null || \
	 docker exec -it $(PROJECT_NAME)-postgres-prod psql -U tiger_user -d tiger_mcp_prod 2>/dev/null || \
	 echo "$(RED)PostgreSQL container not found$(NC)"

db-backup: ## Backup database
	@echo "$(BLUE)Creating database backup...$(NC)"
	@mkdir -p backups
	@docker exec $(PROJECT_NAME)-postgres-dev pg_dump -U tiger_user tiger_mcp_dev > backups/backup-$$(date +%Y%m%d_%H%M%S).sql 2>/dev/null || \
	 docker exec $(PROJECT_NAME)-postgres-prod pg_dump -U tiger_user tiger_mcp_prod > backups/backup-$$(date +%Y%m%d_%H%M%S).sql 2>/dev/null || \
	 echo "$(RED)PostgreSQL container not found$(NC)"
	@echo "$(GREEN)Backup completed$(NC)"

db-restore: ## Restore database (specify BACKUP=filename)
	@if [ -z "$(BACKUP)" ]; then \
		echo "$(RED)Please specify BACKUP=filename$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Restoring database from $(BACKUP)...$(NC)"
	@docker exec -i $(PROJECT_NAME)-postgres-dev psql -U tiger_user -d tiger_mcp_dev < $(BACKUP) 2>/dev/null || \
	 docker exec -i $(PROJECT_NAME)-postgres-prod psql -U tiger_user -d tiger_mcp_prod < $(BACKUP) 2>/dev/null || \
	 echo "$(RED)PostgreSQL container not found$(NC)"

# Cleanup operations
.PHONY: clean clean-all clean-images clean-volumes
clean: ## Clean up containers and networks
	@echo "$(BLUE)Cleaning up containers and networks...$(NC)"
	./scripts/stop.sh
	./scripts/stop.sh --prod
	@docker container prune -f
	@docker network prune -f
	@echo "$(GREEN)Cleanup completed$(NC)"

clean-volumes: ## Clean up containers, networks, and volumes
	@echo "$(BLUE)Cleaning up containers, networks, and volumes...$(NC)"
	@echo "$(RED)WARNING: This will delete all data!$(NC)"
	@read -p "Are you sure? (y/N) " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		./scripts/stop.sh --volumes; \
		./scripts/stop.sh --prod --volumes; \
		docker volume prune -f; \
		echo "$(GREEN)Volume cleanup completed$(NC)"; \
	else \
		echo "$(YELLOW)Volume cleanup cancelled$(NC)"; \
	fi

clean-images: ## Clean up unused images
	@echo "$(BLUE)Cleaning up unused images...$(NC)"
	@docker image prune -f
	@docker images --filter="reference=$(PROJECT_NAME)-*" -q | xargs -r docker rmi
	@echo "$(GREEN)Image cleanup completed$(NC)"

clean-all: clean clean-volumes clean-images ## Clean up everything

# Testing and validation
.PHONY: test validate
test: ## Run tests (placeholder)
	@echo "$(BLUE)Running tests...$(NC)"
	@echo "$(YELLOW)Test implementation needed$(NC)"

validate: ## Validate Docker configuration
	@echo "$(BLUE)Validating Docker configuration...$(NC)"
	@docker-compose -f $(COMPOSE_FILE_DEV) config >/dev/null && echo "$(GREEN)Development config valid$(NC)" || echo "$(RED)Development config invalid$(NC)"
	@docker-compose -f $(COMPOSE_FILE_PROD) config >/dev/null && echo "$(GREEN)Production config valid$(NC)" || echo "$(RED)Production config invalid$(NC)"

# Security operations
.PHONY: security-scan generate-secrets
security-scan: ## Scan images for vulnerabilities (requires trivy)
	@echo "$(BLUE)Scanning images for vulnerabilities...$(NC)"
	@if command -v trivy >/dev/null 2>&1; then \
		for service in mcp-server dashboard-api database; do \
			echo "$(GREEN)Scanning $$service...$(NC)"; \
			trivy image $(PROJECT_NAME)-$$service:latest; \
		done; \
	else \
		echo "$(YELLOW)Trivy not installed. Install with: brew install aquasecurity/trivy/trivy$(NC)"; \
	fi

generate-secrets: ## Generate production secrets
	@echo "$(BLUE)Generating production secrets...$(NC)"
	@cd secrets && \
	openssl rand -base64 32 > postgres_password.txt && \
	openssl rand -base64 32 > redis_password.txt && \
	openssl rand -base64 64 > secret_key.txt && \
	chmod 600 *.txt
	@echo "$(GREEN)Secrets generated in secrets/ directory$(NC)"
	@echo "$(YELLOW)Don't forget to add your Tiger private key as tiger_private_key.pem$(NC)"

# Monitoring
.PHONY: stats monitor
stats: ## Show container resource usage
	@echo "$(BLUE)Container resource usage:$(NC)"
	@docker stats --no-stream 2>/dev/null | grep $(PROJECT_NAME) || echo "$(YELLOW)No containers running$(NC)"

monitor: ## Monitor logs in real-time
	@echo "$(BLUE)Monitoring all services...$(NC)"
	@echo "$(YELLOW)Press Ctrl+C to stop$(NC)"
	./scripts/logs.sh --follow --timestamps

# Documentation
.PHONY: docs
docs: ## Open documentation
	@echo "$(BLUE)Opening documentation...$(NC)"
	@if command -v open >/dev/null 2>&1; then \
		open docs/DOCKER.md; \
	elif command -v xdg-open >/dev/null 2>&1; then \
		xdg-open docs/DOCKER.md; \
	else \
		echo "$(GREEN)See docs/DOCKER.md for detailed documentation$(NC)"; \
	fi