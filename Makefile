# YouTube Caption API - Makefile
# Docker orchestration for build, run, deploy operations

# Configuration variables
IMAGE_NAME := youtube-caption-api
PROJECT_ID := youtube-caption-api
REGION := us-central1
SERVICE_NAME := youtube-caption-api
GCR_IMAGE := gcr.io/$(PROJECT_ID)/$(SERVICE_NAME)
LOCAL_PORT := 8000
CONTAINER_PORT := 8000

# Default environment variables
CHUNK_SIZE := 5000
MAX_CHUNKS := 5

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

.PHONY: help build run up down logs shell test test-local clean deploy build-push up-compose down-compose

# Default target
help: ## Show this help message
	@echo "YouTube Caption API - Docker Orchestration"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Docker Operations
build: ## Build the Docker image
	@echo "$(GREEN)Building Docker image: $(IMAGE_NAME)$(NC)"
	docker build -t $(IMAGE_NAME) .
	@echo "$(GREEN)Build complete!$(NC)"

run: ## Run container locally (interactive)
	@echo "$(GREEN)Running container locally on port $(LOCAL_PORT)$(NC)"
	docker run --rm -it \
		--env-file .env \
		-p $(LOCAL_PORT):$(CONTAINER_PORT) \
		-e PORT=$(CONTAINER_PORT) \
		--name $(IMAGE_NAME)-dev \
		$(IMAGE_NAME)

up: ## Start container in detached mode
	@echo "$(GREEN)Starting container in background$(NC)"
	docker run -d \
		--env-file .env \
		-p $(LOCAL_PORT):$(CONTAINER_PORT) \
		-e PORT=$(CONTAINER_PORT) \
		--name $(IMAGE_NAME)-dev \
		$(IMAGE_NAME)
	@echo "$(GREEN)Container started! Access at http://localhost:$(LOCAL_PORT)$(NC)"

down: ## Stop and remove containers
	@echo "$(YELLOW)Stopping and removing containers$(NC)"
	-docker stop $(IMAGE_NAME)-dev
	-docker rm $(IMAGE_NAME)-dev
	@echo "$(GREEN)Containers stopped and removed$(NC)"

logs: ## View container logs
	@echo "$(GREEN)Viewing container logs:$(NC)"
	docker logs -f $(IMAGE_NAME)-dev

shell: ## Get interactive shell in running container
	@echo "$(GREEN)Opening shell in container$(NC)"
	docker exec -it $(IMAGE_NAME)-dev /bin/bash

# Testing
test: ## Run tests in Docker container
	@echo "$(GREEN)Running tests in Docker container$(NC)"
	docker run --rm \
		-v $(PWD):/app \
		-w /app \
		python:3.11-slim \
		/bin/bash -c "pip install -r requirements.txt && python -m pytest test_function_app.py -v"

test-local: ## Run tests in local Python environment
	@echo "$(GREEN)Running tests locally$(NC)"
	python3 -m pytest test_function_app.py -v

# Health check
health: ## Check if the service is healthy
	@echo "$(GREEN)Checking service health$(NC)"
	@curl -f http://localhost:$(LOCAL_PORT)/health && echo "\n$(GREEN)Service is healthy!$(NC)" || echo "$(RED)Service is not responding$(NC)"

# Development
dev: build up ## Build and start development environment
	@echo "$(GREEN)Development environment ready!$(NC)"
	@echo "API available at: http://localhost:$(LOCAL_PORT)"
	@echo "API docs at: http://localhost:$(LOCAL_PORT)/docs"

# Cleanup
clean: down ## Clean up Docker images and containers
	@echo "$(YELLOW)Cleaning up Docker resources$(NC)"
	-docker rmi $(IMAGE_NAME)
	-docker system prune -f
	@echo "$(GREEN)Cleanup complete$(NC)"

# Cloud Run Deployment
build-push: ## Build and push image to Google Container Registry
	@echo "$(GREEN)Building and pushing to GCR$(NC)"
	gcloud builds submit --tag $(GCR_IMAGE)
	@echo "$(GREEN)Image pushed to $(GCR_IMAGE)$(NC)"

deploy: build-push ## Deploy to Google Cloud Run
	@echo "$(GREEN)Deploying to Cloud Run$(NC)"
	gcloud run deploy $(SERVICE_NAME) \
		--image $(GCR_IMAGE) \
		--platform managed \
		--region $(REGION) \
		--allow-unauthenticated \
		--memory 512Mi \
		--cpu 1 \
		--timeout 300 \
		--max-instances 100 \
		--set-env-vars "CHUNK_SIZE=$(CHUNK_SIZE),MAX_CHUNKS=$(MAX_CHUNKS)"
	@echo "$(GREEN)Deployment complete!$(NC)"
	@gcloud run services describe $(SERVICE_NAME) --platform managed --region $(REGION) --format 'value(status.url)'

# Docker Compose Operations (if docker-compose.yml exists)
up-compose: ## Start services with docker-compose
	@if [ -f docker-compose.yml ]; then \
		echo "$(GREEN)Starting services with docker-compose$(NC)"; \
		docker-compose --env-file .env up -d; \
	else \
		echo "$(RED)docker-compose.yml not found$(NC)"; \
	fi

down-compose: ## Stop services with docker-compose
	@if [ -f docker-compose.yml ]; then \
		echo "$(YELLOW)Stopping services with docker-compose$(NC)"; \
		docker-compose down; \
	else \
		echo "$(RED)docker-compose.yml not found$(NC)"; \
	fi

# Environment setup
env-example: ## Create example environment file
	@echo "# Example environment variables" > .env.example
	@echo "PROJECT_ID=youtube-caption-api" >> .env.example
	@echo "REGION=us-central1" >> .env.example
	@echo "CHUNK_SIZE=5000" >> .env.example
	@echo "MAX_CHUNKS=5" >> .env.example
	@echo "USE_PROXY=0" >> .env.example
	@echo "WEBSHARE_PROXY_USERNAME=" >> .env.example
	@echo "WEBSHARE_PROXY_PASSWORD=" >> .env.example
	@echo "$(GREEN).env.example created$(NC)"

# Quick development workflow
quick: clean build up ## Clean, build, and start (quick development cycle)
	@echo "$(GREEN)Quick development setup complete!$(NC)"