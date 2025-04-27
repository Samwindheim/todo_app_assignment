# Makefile for Todo App Assignment

# Use bash for compatibility with source command
SHELL := /bin/bash

# Define variables
FRONTEND_DIR = frontend
BACKEND_DIR = backend
BACKEND_VENV = $(BACKEND_DIR)/venv
PYTHON = $(BACKEND_VENV)/bin/python
PIP = $(BACKEND_VENV)/bin/pip
CONCURRENTLY = $(FRONTEND_DIR)/node_modules/.bin/concurrently

# Phony targets (targets that don't represent files)
.PHONY: help setup install run run-backend run-frontend clean

# Default target (executed when running `make`)
help:
	@echo "Available commands:"
	@echo "  make help          Show this help message"
	@echo "  make setup         Create backend venv, install all backend and frontend dependencies"
	@echo "  make install       Install/update backend and frontend dependencies (assumes venv exists)"
	@echo "  make run           Run backend and frontend servers concurrently (one-command start)"
	@echo "  make run-backend   Run only the backend server"
	@echo "  make run-frontend  Run only the frontend server"
	@echo "  make clean         Remove generated files (venv, node_modules, build artifacts, db)"

# Setup: Create venv and install everything
setup: $(BACKEND_VENV)/bin/activate $(FRONTEND_DIR)/node_modules/.bin/concurrently
	@echo "Backend and Frontend dependencies already installed."

$(BACKEND_VENV)/bin/activate:
	@echo "Creating backend virtual environment in $(BACKEND_VENV)..."
	python3 -m venv $(BACKEND_VENV)
	@echo "Installing backend dependencies..."
	source $(BACKEND_VENV)/bin/activate && \
	$(PIP) install -r $(BACKEND_DIR)/requirements.txt
	touch $(BACKEND_VENV)/bin/activate # Mark as created

$(FRONTEND_DIR)/node_modules/.bin/concurrently: $(FRONTEND_DIR)/package.json
	@echo "Installing frontend dependencies..."
	(cd $(FRONTEND_DIR) && npm install)
	# Check if concurrently was installed (it should be if npm install succeeded)
	@[ -f "$(CONCURRENTLY)" ] || (echo "Error: concurrently not found after npm install. Check frontend/package.json" && exit 1)

# Install: Update dependencies
install: $(BACKEND_VENV)/bin/activate # Ensure venv exists
	@echo "Installing/updating backend dependencies..."
	source $(BACKEND_VENV)/bin/activate && \
	$(PIP) install -r $(BACKEND_DIR)/requirements.txt
	@echo "Installing/updating frontend dependencies..."
	(cd $(FRONTEND_DIR) && npm install)

# Run: Start both servers
run: $(CONCURRENTLY) $(BACKEND_VENV)/bin/activate
	@echo "Starting backend and frontend servers..."
	$(CONCURRENTLY) --kill-others-on-fail \
		"make run-backend" \
		"make run-frontend"

# Run Backend
run-backend: $(BACKEND_VENV)/bin/activate
	@echo "Starting backend server (uvicorn)..."
	source $(BACKEND_VENV)/bin/activate && \
	uvicorn main:app --reload --host 127.0.0.1 --port 8000 --app-dir $(BACKEND_DIR)

# Run Frontend
run-frontend:
	@echo "Starting frontend development server (vite)..."
	(cd $(FRONTEND_DIR) && npm run dev)

# Clean: Remove generated files
clean:
	@echo "Cleaning up generated files..."
	rm -rf $(BACKEND_VENV)
	rm -rf $(FRONTEND_DIR)/node_modules
	rm -rf $(FRONTEND_DIR)/dist
	rm -f $(BACKEND_DIR)/todo.db
	rm -f $(BACKEND_DIR)/*.db-journal
	find . -type d -name '__pycache__' -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.pyo' -delete
	@echo "Cleanup complete." 