.PHONY: install install-deps install-playwright help docker-build docker-run docker-run-visible k8s-deploy run-visible run-demo run-record docker-run-record k8s-record run-main-record run-main-with-recording run-modified-main run-recording-agent run-direct-recording run-agent-recorder check-recordings run-monkey-patch docker-run-monkey

# Default target
help:
	@echo "Available commands:"
	@echo "  make install         - Install all dependencies and setup Playwright"
	@echo "  make install-deps    - Install Python dependencies"
	@echo "  make install-playwright - Install Playwright browsers"
	@echo "  make docker-build    - Build Docker image"
	@echo "  make docker-run      - Run Docker container locally"
	@echo "  make docker-run-visible - Run Docker with visible browser (X11)"
	@echo "  make k8s-deploy      - Deploy to Kubernetes"
	@echo "  make run-visible     - Run Playwright with visible browser"
	@echo "  make run-demo        - Run the visible browser demo script"
	@echo "  make run-record      - Run the browser recording demo"
	@echo "  make docker-run-record - Run the browser recording demo in Docker"
	@echo "  make k8s-record      - Run the browser recording job in Kubernetes"
	@echo "  make run-main-record - Run main.py with recording wrapper"
	@echo "  make run-main-with-recording - Run the integrated main with recording"
	@echo "  make run-modified-main - Run the modified main.py with recording"
	@echo "  make run-recording-agent - Run main_with_recording.py (recording agent)"
	@echo "  make run-direct-recording - Run main_direct_recording.py (direct recording)"
	@echo "  make run-agent-recorder - Run agent_recorder.py (monkey patching approach)"
	@echo "  make check-recordings - Check for recordings"
	@echo "  make run-monkey-patch - Run with monkey patching for single browser recording"
	@echo "  make docker-run-monkey - Run Docker container with monkey patching recording"

# Install everything
install: install-deps install-playwright

# Install Python dependencies
install-deps:
	@echo "Installing Python dependencies..."
	python3 -m pip install -r requirements.txt

# Install Playwright browsers
install-playwright:
	@echo "Installing Playwright browsers..."
	python3 -m playwright install --with-deps

# Docker build
docker-build:
	@echo "Building Docker image..."
	docker build -t browser-use:latest .

# Alternative Docker build (without browser-use)
docker-build-alt:
	@echo "Building Docker image with alternative Dockerfile..."
	docker build -t browser-use:latest -f Dockerfile.alt .

# Docker run
docker-run:
	@if [ -z "$$OPENAI_API_KEY" ]; then \
		echo "❌ OPENAI_API_KEY environment variable is not set!"; \
		echo "Please set it first:"; \
		echo "export OPENAI_API_KEY=your_api_key"; \
		exit 1; \
	fi
	@echo "Running Docker container with Playwright recording..."
	@mkdir -p ./videos
	docker run -it --rm \
		-e OPENAI_API_KEY="$$OPENAI_API_KEY" \
		-e PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
		-v $$(pwd)/videos:/app/videos \
		browser-use:latest
	@echo "Check the ./videos directory for recordings"

# Docker run with visible browser (X11)
docker-run-visible:
	@if [ -z "$$OPENAI_API_KEY" ]; then \
		echo "❌ OPENAI_API_KEY environment variable is not set!"; \
		echo "Please set it first:"; \
		echo "export OPENAI_API_KEY=your_api_key"; \
		exit 1; \
	fi
	@echo "Running Docker with visible browser (requires X11)..."
	xhost + local:docker || true
	docker run -it --rm \
		-e DISPLAY=$(DISPLAY) \
		-e OPENAI_API_KEY="$$OPENAI_API_KEY" \
		-v /tmp/.X11-unix:/tmp/.X11-unix \
		-v $(PWD):/app \
		--ipc=host \
		browser-use:latest \
		python visible_browser.py

# Docker run with video recording
docker-run-record:
	@if [ -z "$$OPENAI_API_KEY" ]; then \
		echo "❌ OPENAI_API_KEY environment variable is not set!"; \
		echo "Please set it first:"; \
		echo "export OPENAI_API_KEY=your_api_key"; \
		exit 1; \
	fi
	@echo "Running Docker with video recording..."
	docker run -it --rm \
		-e OPENAI_API_KEY="$$OPENAI_API_KEY" \
		-v $(PWD):/app \
		browser-use:latest \
		python record_browser.py
	@echo "Video saved to videos/ directory"

# Docker run with monkey patching
docker-run-monkey:
	@if [ -z "$$OPENAI_API_KEY" ]; then \
		echo "❌ OPENAI_API_KEY environment variable is not set!"; \
		echo "Please set it first:"; \
		echo "export OPENAI_API_KEY=your_api_key"; \
		exit 1; \
	fi
	@echo "Running Docker container with monkey patching recording..."
	@mkdir -p ./videos
	docker run -it --rm \
		-e OPENAI_API_KEY="$$OPENAI_API_KEY" \
		-e PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
		-v $$(pwd)/videos:/app/videos \
		browser-use:latest \
		python monkey_patch_record.py
	@echo "Check the ./videos directory for recordings"

# Kubernetes deploy
k8s-deploy:
	@echo "Deploying to Kubernetes..."
	kubectl apply -f k8s/deployment.yaml

# Kubernetes run recording job
k8s-record:
	@echo "Running browser recording job in Kubernetes..."
	kubectl apply -f k8s/record-job.yaml
	@echo "Job submitted. To check status: kubectl get jobs"
	@echo "To get videos: kubectl cp <pod-name>:/app/videos ./k8s-videos"

# Check recordings
check-recordings:
	@echo "Checking for recordings..."
	python3 check_recordings.py

# Clean up (optional)
clean:
	@echo "Cleaning up..."
	rm -rf node_modules
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} + 